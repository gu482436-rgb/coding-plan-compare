#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
混合爬虫 / 每日价目刷新器（模型中心结构，v3 诚实版）。

诚实说明（重要）——本脚本只做三件事，绝不伪造任何价格：
1. 校验数据完整性（新 schema：rate / byok+priceMultiplier / subscription / allowanceUSD 任一即可）。
2. 滚动更新 lastUpdated。
3. 可选地从 LiteLLM 社区价目表「补充」官方 API 基准价——但默认【不覆盖】已人工核实的价。
   只有 models[].api.autoRefresh=true 的模型才会被 LiteLLM 覆盖（用于我们尚未人工核实的型号）。
   当前 23 个模型均为人工官网核实价，autoRefresh 默认关闭 → 每日运行不会悄悄改掉它们。

为什么「额度」一列无法自动抓取：
- 各订阅制 coding plan 从不公开「分模型 token 单价 / 信用额」，任何爬虫/API 都拿不到。
- 这类数据只能靠人工/社区维护（标 source=estimated 或 subscription）。
- Command Code 全系已用官方公布的每模型真实单价（rate 字段，official），属最准确来源。

全程标准库，GitHub Actions 免装依赖。
"""

import json
import os
import sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON_PATH = os.path.join(ROOT, "data", "pricing.json")

UA = {"User-Agent": "Mozilla/5.0 (compatible; coding-plan-compare-bot/3.0)"}

# LiteLLM 社区价目表（权威、持续更新）。仅用于「补充」未核实价。
LITELLM_URL = "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json"

# 本数据集模型 id -> LiteLLM 候选键（按顺序尝试，命中即用）。
LITELLM_MAP = {
    "kimi-k3": ["moonshotai/kimi-k3", "moonshot/kimi-k3", "kimi-k3"],
    "deepseek-v4-flash": ["deepseek/deepseek-v4", "deepseek/deepseek-chat", "deepseek-v4-flash"],
    "deepseek-v4-pro": ["deepseek/deepseek-v4-pro", "deepseek-v4-pro"],
    "glm-5.3-flash": ["zhipu/glm-5.3-flash", "zhipu/glm-5-flash", "glm-5.3-flash"],
    "glm-5.3": ["zhipu/glm-5.3", "zhipu/glm-5", "glm-5.3"],
    "qwen3.7-flash": ["qwen/qwen3.7-flash", "qwen3.7-flash"],
    "qwen3.8-flash": ["qwen/qwen3.8-flash", "qwen3.8-flash"],
    "qwen3.7-max": ["qwen/qwen3.7-max", "qwen3.7-max"],
    "qwen3.8-max": ["qwen/qwen3.8-max", "qwen3.8-max"],
    "ling-3.0-flash": ["qwen/ling-3.0-flash", "ling-3.0-flash"],
    "minimax-m3": ["minimax/minimax-m3", "minimax-m3"],
    "hy3": ["tencent/hunyuan-hy3", "hunyuan-hy3", "tencent/hunyuan-turbo"],
    "hy4": ["tencent/hunyuan-hy4", "hunyuan-hy4"],
    "doubao-pro": ["bytefltr/doubao-pro", "volcengine/doubao-pro", "doubao-pro"],
    "doubao-2.1-turbo": ["volcengine/doubao-2.1-turbo", "doubao-2.1-turbo"],
    "gpt-5.6-luna": ["openai/gpt-5.6-luna", "gpt-5.6-luna"],
    "gpt-5.6-terra": ["openai/gpt-5.6-terra", "gpt-5.6-terra"],
    "gpt-5.6-sol": ["openai/gpt-5.6-sol", "gpt-5.6-sol"],
    "gpt-6-astra": ["openai/gpt-6-astra", "gpt-6-astra"],
    "claude-sonnet-5": ["anthropic/claude-sonnet-5", "claude-sonnet-5"],
    "claude-opus-5": ["anthropic/claude-opus-5", "claude-opus-5"],
    "grok-4.7": ["xai/grok-4.7", "grok-4.7"],
    "gemini-3.7-flash": ["google/gemini-3.7-flash", "gemini-3.7-flash"],
}


def http_get(url, timeout=20):
    import urllib.request
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def fetch_litellm():
    """下载 LiteLLM 价目表，失败返回 None（绝不抛异常中断 workflow）。"""
    try:
        return json.loads(http_get(LITELLM_URL))
    except Exception as e:
        print(f"[litellm] 抓取失败，跳过官方价自动刷新：{e}")
        return None


def per_million(v):
    return round(v * 1_000_000, 6) if v is not None else None


def refresh_official_prices(data, litellm):
    """仅「补充」未核实价：只有 api.autoRefresh=true 的模型才被 LiteLLM 覆盖。
    已人工核实的模型（默认）一律不动，防止被 LiteLLM 旧/错数据悄悄改掉。"""
    if not litellm:
        return 0
    updated = 0
    today = date.today().isoformat()
    for m in data["models"]:
        if not m.get("api", {}).get("autoRefresh"):
            continue  # 保护已核实价
        entry = None
        for key in LITELLM_MAP.get(m["id"], []):
            if key in litellm:
                entry = litellm[key]
                break
        if not entry:
            continue
        inp = per_million(entry.get("input_cost_per_token"))
        out = per_million(entry.get("output_cost_per_token"))
        cin = per_million(entry.get("cache_read_input_token_cost"))
        if inp is None or out is None:
            continue
        m["api"]["input"] = inp
        m["api"]["output"] = out
        if cin is not None:
            m["api"]["cachedInput"] = cin
        if "offPeak" in m["api"]:
            pass  # 保留已有峰谷价
        base = (m["api"].get("note", "") or "").split("（每日")[0].strip()
        m["api"]["note"] = base + f"（每日自动从 LiteLLM 刷新 {today}）"
        updated += 1
        print(f"[litellm] 刷新 {m['id']}: in=${inp} out=${out} cache=${cin}")
    return updated


def entry_valid(plan, entry):
    """新 schema：一个模型条目只要满足以下任一即为合法，绝不要求必须有额度。"""
    if entry.get("rate"):                      # 官方公布每模型真实单价（如 Command Code）
        return True
    if entry.get("subscription"):              # 订阅/速率/积分制：无公开单价，如实标注
        return True
    if plan.get("byok") and "priceMultiplier" in entry:  # Agent 平台自带 Key，0 加价
        return True
    if "allowanceUSD" in entry:                # 含额度（如 OpenCode Go 月度上限）
        return True
    return False


def main():
    with open(JSON_PATH, encoding="utf-8") as f:
        data = json.load(f)

    # 1) 可选官方价补充（默认不覆盖已核实价）
    litellm = fetch_litellm()
    n_refresh = refresh_official_prices(data, litellm)
    if n_refresh == 0:
        print("[litellm] 本轮无补充（所有模型均为人工核实价 / 极新型号尚未被收录）")

    # 2) 基本校验（新 schema）
    assert "models" in data and "plans" in data, "schema missing models/plans"
    mids = {m["id"] for m in data["models"]}
    assert all("api" in m for m in data["models"]), "每个 model 需含 api 基准价"
    for pl in data["plans"]:
        assert "id" in pl and "models" in pl, f"plan {pl.get('id')} malformed"
        for mid, entry in pl["models"].items():
            assert mid in mids, f"plan {pl['id']} 引用了未知模型 {mid}"
            assert entry_valid(pl, entry), (
                f"plan {pl['id']}/{mid} 既无 rate / subscription / allowanceUSD，也非 byok+priceMultiplier，"
                f"计价方式无法确定"
            )

    # 3) 滚动更新时间
    data["meta"]["lastUpdated"] = date.today().isoformat()

    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # 统计各计价来源
    from collections import Counter
    c = Counter()
    for pl in data["plans"]:
        for mid, e in pl["models"].items():
            if e.get("rate"):
                c["官方真实单价(rate)"] += 1
            elif pl.get("byok"):
                c["平台0加价(byok)"] += 1
            elif e.get("subscription"):
                c["订阅包含(无单价)"] += 1
            else:
                c["额度折算"] += 1
    print(f"done: {len(data['plans'])} plans, {len(data['models'])} models, "
          f"官方价补充={n_refresh}")
    print("  计价来源分布:", dict(c))


if __name__ == "__main__":
    sys.exit(main())
