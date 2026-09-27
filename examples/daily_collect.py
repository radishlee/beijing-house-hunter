# ============================================================
# 最佳实践示例：确定性每日采集引擎（零 LLM 参与）
# ------------------------------------------------------------
# 架构原则：确定性工作(抓取/解析/对比/落盘)归脚本+系统计划任务(零token)，
#           LLM 只做每周一次的趋势判断与知识更新。
# 本文件为运行实例（含个人目标盘配置），使用时替换 TARGETS 与板块代码。
# 注册（Windows）: schtasks /Create /TN "HouseAgentDaily" /TR
#   "python <此文件路径>" /SC DAILY /ST 09:00 /F
# ============================================================
# -*- coding: utf-8 -*-
"""换房智能体·每日采集引擎（零 LLM 参与，供 Windows 计划任务直接调用）
整合已验证逻辑：吉淘房大盘 + 小区挂牌爬虫 + 规自委三区公示 + 对比昨日 + 写日志 + 刷新大屏
产出：logs/盯梢日志_每日.md 追加、data/xiaoqu_snapshot_latest.json、dashboard_data.json、dashboard.html、alerts.json(供周迭代器)
运行：python daily_collect.py   （建议任务计划程序 每日09:00）
"""
import urllib.request, ssl, re, gzip, io, time, json, os, sys, subprocess
from datetime import date

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # house-agent/
sys.path.insert(0, os.path.join(BASE, 'tools'))
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0.0.0 Safari/537.36',
      'Accept-Language': 'zh-CN,zh;q=0.9', 'Accept-Encoding': 'gzip'}

def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    r = urllib.request.urlopen(req, timeout=18, context=ctx)
    raw = r.read()
    if r.headers.get('Content-Encoding') == 'gzip':
        raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
    return raw.decode('utf-8', 'ignore')

def safe(fn, label):
    try:
        return fn(), None
    except Exception as e:
        return None, f'{label} ERR: {e}'

today = date.today().strftime('%Y-%m-%d')
report, alerts = [], []

# ── 1) 大盘（吉淘房） ──
market = {}
def _market():
    t = re.sub(r'<[^>]+>', ' ', re.sub(r'<script[^>]*>.*?</script>', ' ', fetch('https://www.jitaofang.com/'), flags=re.S))
    t = re.sub(r'\s+', ' ', t)
    wq = re.findall(r'网签量[^\d]{0,6}(\d{2,4})', t)
    zs = re.findall(r'在售二手房源数为?\s*(\d{5,6})', t)
    dt = re.findall(r'(09-\d\d)数据', t)
    return {'wq': int(wq[0]) if wq else None, 'wq_date': dt[0] if dt else '?',
            'zaishou': int(zs[0]) if zs else None}
market, err = safe(_market, '大盘')
if err: report.append(err)

# ── 2) 小区挂牌爬虫（复用 tools/xiaoqu_snapshot.py） ──
prev_file = os.path.join(BASE, 'data', 'xiaoqu_snapshot_latest.json')
prev = json.load(open(prev_file, encoding='utf-8')) if os.path.exists(prev_file) else {'data': {}}
try:
    import xiaoqu_snapshot as xs
    xs.main()
except Exception as e:
    report.append(f'爬虫ERR: {e}')
snap = json.load(open(prev_file, encoding='utf-8')).get('data', {})

# 对比昨日：新上低锚/清零/异常
for name, cur in snap.items():
    old = prev.get('data', {}).get(name, {})
    if old.get('status') != 'ok' and cur.get('status') == 'ok':
        alerts.append(f'[新放量] {name} 房源页从无到有（样本{cur.get("onsale_sample")}套，最低{cur.get("min_price")}万）')
    elif old.get('status') == 'ok' and cur.get('status') == 'ok':
        om, nm = old.get('min_price'), cur.get('min_price')
        if om and nm and nm < om * 0.97:
            alerts.append(f'[降价≥3%] {name} 最低挂牌 {om}→{nm} 万')
        if om and om >= 100 and nm < 100:
            alerts.append(f'[异常] {name} 最低价跳变 {om}→{nm}，疑似样本污染，需人工核')

# ── 3) 规自委三区公示 ──
for code, dist in [('ft', '丰台'), ('dx', '大兴'), ('cy', '朝阳')]:
    def _gz(c=code, d=dist):
        html = fetch(f'https://ghzrzyw.beijing.gov.cn/zhengwuxinxi/tzgg/{c}/')
        pairs = re.findall(r'<a[^>]*href="([^"]+)"[^>]*>([^<]{8,70})</a>', html)
        hits = [(t.strip(), u) for u, t in pairs
                if any(k in t for k in ['安置', '回迁', '首次', '丰遗', '和义', '旧宫', '久敬', '管庄', '南街', '瀛海', '西红门', '房本'])]
        return hits
    hits, err = safe(_gz, f'规自委{dist}')
    if err:
        report.append(err); continue
    new_hits = [h for h in (hits or []) if '2025丰遗登07号' not in h[0] and '西红门镇开展农房' not in h[0]
                and '临时用地' not in h[0] and '挂牌出让' not in h[0] and '估价服务' not in h[0]
                and '资产清查' not in h[0] and '注销行政许可' not in h[0] and '热力外线' not in h[0]]
    if new_hits:
        for t, u in new_hits:
            alerts.append(f'[官方公示] {dist}: {t} ({u})')

# ── 4) 写日志 ──
daily = os.path.join(BASE, 'logs', '盯梢日志_每日.md')
if not os.path.exists(daily):
    open(daily, 'w', encoding='utf-8').write('# 盯梢日志（每日采集引擎自动追加）\n\n> 基线见 baselines.json。显著事件同步 alerts.json 供周迭代器。\n')
mq = f"{market['wq']}({market['wq_date']})" if market.get('wq') else '?'
zs = str(market.get('zaishou')) if market.get('zaishou') else '?'
entry = f"\n## {today}\n- **大盘**：建委网签 {mq} 套；全市在售 {zs} 套。来源：吉淘房直抓。\n"
entry += '- **规自委**：' + ('无目标盘新公示。' if not any(a.startswith('[官方') for a in alerts) else '⚠️ 见 alerts。') + '\n'
if alerts:
    entry += '- **显著事件**：\n' + '\n'.join(f'  - {a}' for a in alerts) + '\n'
else:
    entry += '- **显著事件**：无。\n'
entry += '- **逐盘样本**：' + '; '.join(f"{n}:{d.get('onsale_sample','—')}套/低锚{d.get('min_price','—')}" for n, d in snap.items()) + '\n'
open(daily, 'a', encoding='utf-8').write(entry)

# ── 5) alerts.json（供周迭代器读取） ──
al_file = os.path.join(BASE, 'data', 'alerts.json')
al = json.load(open(al_file, encoding='utf-8')) if os.path.exists(al_file) else []
al.append({'date': today, 'alerts': alerts})
json.dump(al[-60:], open(al_file, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

# ── 6) 刷新大屏数据 ──
dd_file = os.path.join(BASE, 'dashboard_data.json')
d = json.load(open(dd_file, encoding='utf-8'))
d['updated'] = today + ' 09:00(采集引擎)'
if market.get('wq'): d['market']['wq'] = str(market['wq'])
if market.get('wq_date'): d['market']['wqDate'] = market['wq_date']
if market.get('zaishou'): d['market']['zaishou'] = f"{market['zaishou']:,}"
if alerts:
    d['events'] = [f'{today} ' + a for a in alerts] + d.get('events', [])[:5]
json.dump(d, open(dd_file, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
subprocess.run(['python', os.path.join(BASE, 'update_dashboard.py'), dd_file], capture_output=True)

print(f'[{today}] 采集完成 | 网签{mq} 在售{zs} | 显著事件{len(alerts)}条')
for a in alerts: print('  -', a)
