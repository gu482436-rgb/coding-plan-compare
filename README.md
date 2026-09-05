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

## 数据来源与诚实声明
- 价格单位：USD / 每百万 token（`input`=缓存未命中输入，`cachedInput`=缓存命中输入，`output`=输出）。
- **模型基准价（`models[].api`）全部来自各厂家官方定价页（2026-09-05 核对）**：DeepSeek 官方 docs、OpenAI / Anthropic / xAI 官方、阿里云百炼、智谱 bigmodel.ai、月之暗面 kimi.com、腾讯云 TokenHub、MiniMax 官方。每条 `note` 标注来源与原始币种。
- **有效单价 = 官方 API 基准价 ×（月费 ÷ 额度 allowanceUSD）**。有峰谷价的模型（DeepSeek V4 全系）在 `api.offPeak` 存谷时价，用「时段」切换；Agent 平台（byok）有效单价 = 官方价 × markup（默认 1.0，0 加价）。
- 额度 allowanceUSD：订阅制/聚合器 plan 的**额度（信用额）**除 Command Code Go=$10、GOAT=$60 为用户确认外，其余按「月费×倍数」估算并标 `estimated`——这是转售商不公开的数据，请拿官方实时值替换。模型基准价本身均为官方核实价，非估算。

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
脚本 `scripts/update_prices.py` 每日跑，但它**不能凭空编出准确数字**，分两类：

1. **能自动追新的 —— 官方 API 基准价（`models[].api`）**
   数据源是 LiteLLM 社区维护的 `model_prices_and_context_window.json`（业界广泛引用、持续更新）。
   脚本每天尝试拉取并刷新已收录模型的官方价；对极新型号（DeepSeek V4 / GPT-5.6 / Claude Sonnet 5 / Grok 4.7 / Qwen 3.8 等 2026 最新代）若 LiteLLM 尚未收录，则保留人工核到的官方价不动。
   抓取失败（网络/源不可用）会**静默跳过**，不影响校验与提交。
2. **不能自动更新的 —— 订阅档/聚合器的额度（信用额 `allowanceUSD`）**
   厂商从不公开「分模型 token 单价」，任何爬虫都抓不到。这部分**只能人工/社区维护**，标 `source=estimated`。
   当前仅 Command Code Go=$10、GOAT=$60 为用户确认硬值，其余额度均为估算待替换。

> 结论：每日跑 = 每天校验数据不崩 + 尽量追新官方价 + 滚动 lastUpdated；但「额度」一列的准确性需要你（或提 PR 的 contributor）持续维护，脚本不会伪造它。

## 维护数据
编辑 `data/pricing.json`：
- `models[]`：模型目录（id / name / maker / contextWindow / tier），`api` 为官方基准价（可被每日脚本从 LiteLLM 刷新）。
- `plans[]`：每个 coding plan。`byok`（Agent 平台/自带 Key）= 0 加价，按官方价算；非 byok 的订阅档填 `allowanceUSD`（信用额，目前多为估算，待替换真实值）。
- 想新增套餐：直接往 `plans[]` 加对象即可，页面自动渲染。
