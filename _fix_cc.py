import json

P = "/Users/gc/WorkBuddy/2026-09-05-14-37-32/coding-plan-compare/data/pricing.json"
d = json.load(open(P, encoding="utf-8"))
models = {m["id"]: m for m in d["models"]}
plans = {p["id"]: p for p in d["plans"]}

# 官方 base rate（每百万 token，off-peak 谷时为文档主显示值；DeepSeek 含 peak 峰时）。
# 来源 commandcode.ai/docs/plans/go 与 /goat（2026-09-05 抓取，Go/GOAT/Pro 共用同一套单价）
CC_RATE = {
    "kimi-k3": (3.0, 0.3, 15.0),
    "deepseek-v4-flash": (0.22, 0.007, 0.66, 0.44, 0.014, 1.32),
    "deepseek-v4-pro": (0.66, 0.022, 1.98, 1.32, 0.044, 3.96),
    "glm-5.3-flash": (0.15, 0.03, 0.5),
    "glm-5.3": (1.4, 0.26, 4.4),
    "qwen3.7-flash": (0.03, 0.006, 0.13),
    "qwen3.8-flash": (0.16, 0.016, 0.47),
    "qwen3.7-max": (2.5, 0.5, 7.5),
    "qwen3.8-max": (2.0, 0.25, 6.0),
    "minimax-m3": (0.30, 0.06, 1.20),
    "hy3": (0.14, 0.035, 0.58),
    "hy4": (0.834, 0.042, 2.501),
    "gpt-5.6-luna": (0.20, 0.02, 1.20),
    "gpt-5.6-sol": (5.0, 0.5, 30.0),
}

def rate_obj(mid):
    r = CC_RATE[mid]
    if len(r) == 6:
        return {"input": r[0], "cachedInput": r[1], "output": r[2],
                "inputPeak": r[3], "cachedInputPeak": r[4], "outputPeak": r[5]}
    return {"input": r[0], "cachedInput": r[1], "output": r[2]}

# Go 支持的模型（官方文档列出且 data 有定义）
GO_MODELS = ["kimi-k3", "deepseek-v4-flash", "deepseek-v4-pro", "glm-5.3-flash",
             "glm-5.3", "qwen3.7-flash", "qwen3.8-flash", "qwen3.7-max",
             "qwen3.8-max", "minimax-m3", "hy3", "hy4", "gpt-5.6-luna"]
GOAT_MODELS = {"kimi-k3": 20, "deepseek-v4-flash": 60, "deepseek-v4-pro": 20,
               "glm-5.3-flash": 40, "glm-5.3": 20, "qwen3.7-flash": 20,
               "qwen3.8-flash": 20, "qwen3.7-max": 33, "qwen3.8-max": 20,
               "minimax-m3": 47, "hy3": 70, "hy4": 20, "gpt-5.6-luna": 20,
               "gpt-5.6-sol": 70}
PRO_MODELS = {"kimi-k3": 30, "deepseek-v4-flash": 70, "deepseek-v4-pro": 30,
              "glm-5.3-flash": 50, "glm-5.3": 30, "hy3": 80, "hy4": 30,
              "gpt-5.6-luna": 30, "qwen3.8-flash": 30}
PRO_NOPUB = {"claude-sonnet-5": 20, "gpt-5.6-terra": 20}  # Pro 含但 Command Code 未公开单价

go = plans["commandcode-go"]
go["models"] = {mid: {"rate": rate_obj(mid), "source": "official",
                      "note": "Command Code 官方公布每百万 token 真实单价（docs/plans/go，与 GOAT/Pro 同表）；Go 总信用池 $10 按 rate 扣，无每模型上限"}
                for mid in GO_MODELS}
go["poolUSD"] = 10
go["monthlyUSD"] = 1

goat = plans["commandcode-goat"]
goat["models"] = {mid: {"rate": rate_obj(mid), "allowanceUSD": al, "source": "official",
                        "note": f"官方 base rate；GOAT 每月上限 ${al}"}
                  for mid, al in GOAT_MODELS.items()}
goat["monthlyUSD"] = 10

pro = plans["commandcode-pro"]
pro["models"] = {}
for mid, al in PRO_MODELS.items():
    pro["models"][mid] = {"rate": rate_obj(mid), "allowanceUSD": al, "source": "official",
                          "note": f"官方 base rate；Pro 每月上限 ${al}"}
for mid, al in PRO_NOPUB.items():
    pro["models"][mid] = {"noPublicRate": True, "allowanceUSD": al, "source": "official",
                          "note": f"Pro 含此模型但 Command Code 未公开其单价；每月上限 ${al}"}
pro["monthlyUSD"] = 20

# OpenCode Go：按官方价扣 credits，单价=官方价（rate），月度 credits 上限估算保留
op = plans["opencode-go"]
for mid, e in op["models"].items():
    api = models[mid]["api"]
    e["rate"] = {"input": api["input"], "cachedInput": api["cachedInput"], "output": api["output"]}
    e["source"] = "official"
    e["note"] = (e.get("note", "") + "；OpenCode 按官方价扣 credits，月度上限估算").strip("；")

# 订阅/速率/Credits 制计划：不再编造每 token 额度，如实标注"订阅包含"
SUB = ["claude-code-pro", "cursor-pro", "kiro", "copilot-pro", "codex", "windsurf-pro",
       "openai-plus", "openai-pro", "claude-pro", "claude-max5", "claude-max20",
       "gemini-ai-pro", "gemini-ai-ultra", "grok-super", "jetbrains-ai", "zed-pro",
       "amazon-q-pro", "qoder-pro", "qoder-pro-plus", "qoder-ultra"]
for pid in SUB:
    p = plans[pid]
    p["billing"] = "subscription"
    for mid, e in p["models"].items():
        e.clear()
        e["supported"] = True
        e["source"] = "subscription"
        e["note"] = f"{p['vendor']} {p['plan']} 订阅包含此模型（按请求/速率/Credits 计费，无公开每 token 单价）"

# 国内官方 coding plan → 官方直供（0 加价，按官方价），最准确
for pid in ["kimi-coding", "glm-coding", "minimax-coding"]:
    p = plans[pid]
    p["type"] = "agent_platform"
    p["byok"] = True
    p["markup"] = 1.0
    p["monthlyUSD"] = 0
    for mid, e in p["models"].items():
        e.clear()
        e["priceMultiplier"] = 1
        e["source"] = "official"
        e["note"] = f"{p['vendor']} 官方直供（0 加价），按官方价"

json.dump(d, open(P, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("data rewritten")
