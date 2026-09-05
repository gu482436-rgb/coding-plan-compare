# AI 编程模型 Token 价格对比

按**模型**维度横向对比各家 **Coding Plan**（官方 coding plan + 第三方聚合器）的 token 单价，找出同一模型在哪个 plan 最便宜。

> 纯 API 厂商（DeepSeek API / OpenRouter 等）只进「API 参考」栏，**不参与排名**（按需求方口径不核算 API 价格）。

## 三个视图
1. **模型总榜** — 所有模型按「综合价（每亿 token）」升序排名，点模型进入横向对比。
2. **单模型对比** — 选一个模型（如 Kimi K3），列出所有提供它的 coding plan 各自单价，标出最便宜。
3. **API 参考** — 纯 API 直供价，只读。

## 综合价口径
```
综合价 = 输入 × 输入占比 × (1 − 缓存命中率)
       + 缓存输入 × 输入占比 × 缓存命中率
       + 输出 × 输出占比
```
- 默认 **缓存命中率 98%**（滑块可调，对应你的使用场景 98~99%）。
- 默认 **输入 : 输出 = 3 : 1**（可选 1:1 ~ 10:1）。
- 单位默认 **每亿 token**，可切每百万。

## 数据来源与诚实声明（原则：只用最准确的数据，绝不编造）
价格单位：USD / 每百万 token（`input`=缓存未命中输入，`cachedInput`=缓存命中输入，`output`=输出）。

**三类计价方式，精度从高到低：**

1. **官方公布每模型真实单价（`rate`，最高精度）** —— Command Code 全系（Go/GOAT/Pro/Max）在官网逐字公布了每个模型的每百万 token 单价（`docs/plans/go|goat|pro|max`），直接采用，标注 `source: official`。这是本项目最准的来源。
2. **Agent 平台自带 Key（byok，0 加价）** —— WorkBuddy / CodeBuddy / Kilo Code / Cline / Roo Code 等，以及国内官方 coding plan（Kimi / 智谱 GLM / MiniMax / 火山方舟），有效单价 = 官方 API 价 × markup（默认 1.0，即 0 加价）。准确。
3. **订阅 / 速率 / Credits 制（不编单价）** —— Cursor、Claude Code、Copilot、Codex、Kiro、Windsurf、各官方订阅档（ChatGPT Plus/Pro、Claude Pro/Max、Google AI Pro/Ultra、SuperGrok）、Qoder 等。这类计划是**按请求数 / 速率档 / 积分**计费，**厂商从不公开"分模型 token 单价"**，任何爬虫都抓不到。本项目**不编造额度**，而是如实标注"订阅包含"，**不参与每 token 单价排名**，仅在单模型对比里显示为「订阅包含」行。

- **模型基准价（`models[].api`）全部来自各厂家官方定价页（2026-09-05 核对）**：DeepSeek 官方 docs、OpenAI / Anthropic / xAI 官方、阿里云百炼、智谱 bigmodel.ai、月之暗面 kimi.com、腾讯云 TokenHub、MiniMax 官方、火山方舟。每条 `note` 标注来源与原始币种。
- 有峰谷价的模型（DeepSeek V4 全系）在 `api.offPeak` 存谷时价，用「时段」切换。

## 本地预览
```bash
cd coding-plan-compare
python3 -m http.server 8200 --directory .
# 浏览器打开 http://127.0.0.1:8200/
```
> 必须用本地服务器访问（fetch 数据），不要直接双击用 file:// 打开。

## 推到 GitHub + 开启自动更新
```bash
cd coding-plan-compare
git init
git add -A
git commit -m "init coding plan token compare"
gh repo create coding-plan-compare --public --source=. --push   # 或自行 git remote add
```
然后在仓库 **Settings → Pages** 选 `main` 分支 `/ (root)`；**Settings → Actions → General → Workflow permissions** 设 `Read and write`。GitHub Actions 会按 `.github/workflows/update.yml` 的**每日 cron（UTC 03:17）**跑脚本并自动 commit。

## 自动更新到底能更新什么？（重要，别误会）
脚本 `scripts/update_prices.py` 每日跑，但它**不能凭空编出准确数字**：

1. **能自动补的 —— 未核实的官方 API 基准价**
   数据源是 LiteLLM 社区维护的 `model_prices_and_context_window.json`（业界广泛引用、持续更新）。
   默认**只补充** `models[].api.autoRefresh=true` 的型号（目前为空，即 23 个模型均为人工官网核实价，**不会被 LiteLLM 覆盖**）。若要放开某型号自动刷新，在 `models[].api` 里加 `"autoRefresh": true` 即可。抓取失败会**静默跳过**，不影响校验与提交。
2. **绝不伪造的 —— 任何额度 / 单价**
   所有计价字段（rate / byok / subscription / allowanceUSD）均由数据源或人工维护，脚本只做校验 + 滚动 `lastUpdated`，**从不生成任何价格数字**。

> 结论：每日跑 = 每天校验数据不崩 + 滚动 lastUpdated；官方价经你开启 autoRefresh 后才自动追新。任何"最便宜"排名都只基于真实公布的单价（rate / byok），订阅制计划不参与单价排名，避免假精度。

## 维护数据
编辑 `data/pricing.json`：
- `models[]`：模型目录（id / name / maker / contextWindow / tier），`api` 为官方基准价（可被每日脚本从 LiteLLM 刷新）。
- `plans[]`：每个 coding plan。`byok`（Agent 平台/自带 Key）= 0 加价，按官方价算；非 byok 的订阅档填 `allowanceUSD`（信用额，目前多为估算，待替换真实值）。
- 想新增套餐：直接往 `plans[]` 加对象即可，页面自动渲染。
