# beijing-house-hunter 🏠

> 北京二手房/定向安置房**系统化找房与逐套验证**工具——事件驱动找房，而非库存浏览。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 30 秒安装

**方式一（推荐）**：把仓库 clone 下来，运行一键安装器（自动检测 ZCode / Claude Code / Codex）：

```bash
git clone https://github.com/radishlee/beijing-house-hunter.git
cd beijing-house-hunter
python install.py            # 自动安装到检测到的 Agent skills 目录
python install.py --list     # 仅查看检测结果
python install.py --dir ~/.claude/skills   # 指定目录
```

**方式二**：Codex 系 skill-installer 直装：

```
install-skill-from-github.py --repo radishlee/beijing-house-hunter --path skills/beijing-house-hunter
```

**方式二点五**：本仓库自带 Codex plugin manifest（`.codex-plugin/plugin.json`），支持 marketplace 形态安装。

**方式三**：手动 clone 到任意 Agent 的 skills 目录：

```bash
git clone https://github.com/radishlee/beijing-house-hunter.git ~/.zcode/skills/beijing-house-hunter
```

装好后对 Agent 说：

```
用 beijing-house-hunter 帮我找房：预算200万、安置房/商品房次新、房龄10年以内、两居、丰台/大兴
```

## 最终产出长什么样

Agent 会返回一张**全部经房源级验证**的分级表（示例节选自真实运行）：

```
## 主清单（含税≤200万，按含税价排序）
| # | 小区 | 验证房源 | 挂牌 | 含税≈ | 产权/税费 | 证据 | 状态 |
| 1 | 兴悦居 78.15㎡两居 | 大兴瀛海·8号线 | 208万(满五) | ≈210万 | 三定三限满5年,仅1%契税 | 链家房源页 | ✅ |
| 2 | 长馨园一期 69㎡两居 | 丰台长辛店 | 128-169万 | 130-172万 | 满五唯一,6套实盘 | 链家+贝壳 | ✅ |
...
## 证伪/高风险区（含原因）
- "长阳天地77㎡三居158万" → 9号院疑商办产权,出局
## 未覆盖项（如实交代）
- 逐套契税票年份只能线下核
```

每一行都有来源 URL，可点击回溯；每一处判断都标注 ✅验证 / ⚠️存疑 / ❌证伪。

## 这是什么

一套给 AI Agent（Claude/ZCode 等）使用的 **SKILL（技能包）**：按可配置条件（预算/含税口径/户型面积/区域/楼龄/产权类型）穷尽式搜索全渠道房源，并输出**带证据链的验证表**。

它解决三个真实痛点：

1. **渠道盲区**——好房子不在商品房源池里：安置房"下本解禁盘"、法拍、工抵房、共有产权……挂在"产权状态变化"的事件节点上（规自委公示/法院公告），本项目把它们做成可插拔渠道；
2. **价格口径混乱**——挂牌≠成交、裸价≠含税。内置**含税系数表**（安置房不满二 8.3% / 满五解禁 1% …）与预算反推公式，全部候选统一按"含税总支出"排序；
3. **数据污染**——跨城同名小区、平台均值 bug、中介引流话术。内置**7 种污染模式 + 证伪黑名单**，每个候选必须过验证闸门才能进最终表。

## 核心设计

```
条件解析 → 渠道装载 → 并行搜索 → 验证层 → 统一输出
```

- **对扩展开放，对修改关闭**：新增搜索渠道 = 在 `channels/` 放一个新编号 `.md` 文件，核心工作流零改动；
- **验证层五道闸**：房源级证据 → 黑名单过滤 → 含税口径统一 → 产权判定 → 纠错五步法（逐字读冲突→重搜→读原文→验口径→反转假设）；
- **输出纪律**：禁止宣称"穷尽/搞定"，必须附"未覆盖项"清单。

## 目录结构

```
├── SKILL.md                # 核心五步工作流（封闭）
├── channels/               # 搜索渠道（开放扩展）
│   ├── 01-lianjia-beike.md       # 链家/贝壳快照法（绕验证码）
│   ├── 02-anjuke-fangtianxia.md  # 安居客/房天下交叉验证
│   ├── 03-gov-gongshi.md         # 规自委分局公示直抓（安置房下本）
│   ├── 04-banzheng-news.md       # 颁证新闻/办证动态
│   ├── 05-xinfang-weifang.md     # 新房/现房/尾房/工抵
│   ├── 06-fapai.md               # 法拍（默认禁用）
│   ├── 07-fangzu-crawler.md      # 房天下租房直爬（租金/租售比）
│   └── tools_xiaoqu_snapshot.py  # 小区挂牌快照爬虫（Python）
└── references/
    ├── policy.md           # 产权类型判定表（二类经适/三定三限/自住房…）
    ├── tax-calculator.md   # 含税系数表 + 预算反推公式
    └── blacklist.md        # 数据污染模式 + 已证伪案例库
```

## 精华速览

**产权判定表**（`references/policy.md`）——北京定向安置房三种产权路径一张表讲清：

| 类型 | 上市条件 | 上市补缴 |
|---|---|---|
| 二类经适（多数安置房） | **下本即可卖** | 网签价 3% |
| 三定三限 | **房本满 5 年** | 满 5 年**不补**（比二类经适还省） |
| 一类经适 | 满 5 年 | 差价 70% 口径 |

**选筹规律**（实战反推出的三条）：
- 「下本满 5 年的解禁盘」优于「刚下本的盘」——税费归零 + 急售业主出现；
- 同板块价差的第一因子是「商品房纯度」，不是楼龄；
- 快照必滞后——任何决策以 App 实测 + 中介实时表收口。

## 使用方法

安装后对 Agent 说一句话即可触发（自动按 SKILL.md 工作流执行）：

- 「用 beijing-house-hunter 帮我找房：预算200万、安置房/商品房次新、两居」
- 「核实一下 XX 小区的真实挂牌价和产权性质」
- 「追踪 XX 区安置房下本动态」

条件全部可配置：预算 / 含税口径开关 / 户型 / 面积 / 区域 / 房龄上限 / 付款方式 / 产权排除项。

**建议搭配**：配合确定性脚本做每日盯梢（如本项目衍生的 `tools_xiaoqu_snapshot.py` + 系统计划任务），Agent 只做每周趋势判断——确定性采集零 token，LLM 只花在刀刃上。

## 免责声明（务必阅读）

见 [DISCLAIMER.md](DISCLAIMER.md)。要点：本项目仅提供**方法论与公开信息采集工具**，不构成投资建议；爬虫模块仅供个人学习研究，使用前自行确认目标网站服务条款与当地法律法规；所有价格均为挂牌口径快照，交易决策请以官方登记信息与实地核验为准。

## License

MIT
