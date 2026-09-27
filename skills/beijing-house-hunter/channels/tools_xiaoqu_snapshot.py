# -*- coding: utf-8 -*-
"""换房智能体·小区挂牌快照工具（房天下房源页，绕开搜索限额）
用法: python xiaoqu_snapshot.py
流程: 区板块页 → 提取目标小区 loupan 链接 → 房源列表页解析(5元组) → 输出 JSON
数据口径: 房天下在售挂牌(非成交), 快照时点即时
"""
import urllib.request, ssl, re, gzip, io, time, json, os

ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
UA = {'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0.0.0 Safari/537.36',
      'Accept-Language':'zh-CN,zh;q=0.9','Accept-Encoding':'gzip'}
def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    r = urllib.request.urlopen(req, timeout=18, context=ctx)
    raw = r.read()
    if r.headers.get('Content-Encoding') == 'gzip':
        raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
    return raw.decode('utf-8','ignore')

# 板块页(区_板块) → 目标小区名
TARGETS = {
    'https://esf.fang.com/housing/6_17404_0_3_0_0_1_0_0_0/':   ['御槐园','南庭新苑','阳光星苑','森与天成'],       # 丰台新宫
    'https://esf.fang.com/housing/6_2681_0_3_0_0_1_0_0_0/':    ['和义东里'],                                      # 丰台和义
    'https://esf.fang.com/housing/6_2683_0_3_0_0_1_0_0_0/':    ['益丰园'],                                        # 丰台东高地
    'https://esf.fang.com/housing/585_0_3_0_0_1_0_0_0/':       ['兴悦居','广安康璟家园','南街福苑','德贤华府','城建兴悦居'],  # 大兴(全区分发)
}

def get_loupan_link(board_url, names):
    """从板块页提取目标小区的 loupan 链接(小区名→/loupan/ID.htm)"""
    html = fetch(board_url)
    pairs = re.findall(r'href="(/loupan/\d+\.htm)"[^>]*>([^<]{2,25})</a>', html)
    found = {}
    for u, t in pairs:
        t = t.strip()
        for n in names:
            if (n in t or t in n) and n not in found:
                found[n] = 'https://esf.fang.com' + u
    return found

def parse_house_list(html, xqname):
    """房源页解析: 5元组 {小区名前缀}|{户型}|{面积}㎡|{总价}|万|{标题}"""
    m = re.search(r'class="houseList(.*?)class="page', html, re.S)
    seg = m.group(1) if m else html
    t = re.sub(r'<script[^>]*>.*?</script>',' ',seg,flags=re.S)
    t = re.sub(r'<[^>]+>','|',t); t = re.sub(r'\|+','|',t)
    items = [x.strip() for x in t.split('|') if x.strip()]
    out = []
    for i, x in enumerate(items):
        if re.match(r'^\d室\d厅$', x) and i+2 < len(items) and re.match(r'^[\d.]+㎡$', items[i+1]) \
           and i+3 < len(items) and re.match(r'^\d{2,4}$', items[i+2]) and '万' in items[i+3]:
            try:
                out.append({'title': items[i-1], 'layout': x,
                            'area': float(items[i+1].replace('㎡','')),
                            'price_wan': int(items[i+2])})
            except: pass
    return out

def main():
    result = {}
    for board_url, names in TARGETS.items():
        try:
            found = get_loupan_link(board_url, names)
        except Exception as e:
            print('board ERR', board_url, e); continue
        for n in names:
            if n not in found:
                result[n] = {'status': 'not_in_board'}
                continue
            try:
                time.sleep(1.5)
                houses = parse_house_list(fetch(found[n]), n)
                if not houses:
                    result[n] = {'status': 'no_listings', 'loupan': found[n]}
                    continue
                prices = [h['price_wan'] for h in houses]
                two = [h for h in houses if h['layout'].startswith('2室')]
                three = [h for h in houses if h['layout'].startswith('3室')]
                result[n] = {
                    'status': 'ok', 'loupan': found[n],
                    'onsale_sample': len(houses), 'min_price': min(prices), 'max_price': max(prices),
                    'two_min': min((h['price_wan'] for h in two), default=None),
                    'two_areas': sorted({h['area'] for h in two}),
                    'three_min': min((h['price_wan'] for h in three), default=None),
                    'samples': [{'t': h['title'][:30], 'l': h['layout'], 'a': h['area'], 'p': h['price_wan']} for h in houses[:8]],
                }
                print(f"{n}: {len(houses)}套样本 最低{min(prices)}万 两居低锚{result[n]['two_min']}")
            except Exception as e:
                result[n] = {'status': 'err', 'err': str(e)}
            time.sleep(1.5)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'xiaoqu_snapshot_latest.json')
    json.dump({'time': time.strftime('%Y-%m-%d %H:%M'), 'data': result},
              open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('saved:', out)
    return result

if __name__ == '__main__':
    main()
