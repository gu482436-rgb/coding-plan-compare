#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
混合爬虫 / 每日价目刷新器（模型中心结构）。

诚实说明（重要）：
- 本脚本能可靠自动刷新的，只有「官方 API 基准价」(models[].api)。
  数据源 = LiteLLM 社区维护的 model_prices_and_context_window.json（持续更新、被业界广泛引用）。
  它已覆盖绝大多数在售模型；但对极新的型号（如本数据集里的 DeepSeek V4 / GPT-5.6 / Claude Sonnet 5
  等 2026 最新代），LiteLLM 可能尚未收录，此时保留我们人工核到的官方价不动。
- 本脚本「无法」自动刷新的：各订阅制 coding plan 的「额度/信用额」(allowanceUSD)。
  厂商从不公开「分模型 token 单价」，这类数据只能靠人工/社区维护（标 source=estimated）。
  Command Code Go/GOAT 的额度为用户确认硬值，其余均为估算待替换。

因此：每日自动运行 = ①重新校验数据完整性 ②尽量追新官方价 ③lastUpdated 滚动；
但「额度」一列仍需人维护，脚本不会伪造它。

全程标准库，GitHub Actions 免装依赖。
"""

import json
import os
import re
import sys
import urllib.request
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON_PATH = os.path.join(ROOT, "data", "pricing.json")

UA = {"User-Agent": "Mozilla/5.0 (compatible; coding-plan-compare-bot/2.0)"}

# LiteLLM 社区价目表（权威、持续更新）。抓取失败时静默跳过，不影响校验。
LITELLM_URL = "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json"

# 本数据集模型 id -> LiteLLM 候选键（按顺序尝试，命中即用）。
# 极新型号可能暂未收录，命中为空时保留人工价。
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
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def fetch_litellm():
    """下载 LiteLLM 价目表，失败返回 None（绝不抛异常中断 workflow）。"""
    try:
        txt = http_get(LITELLM_URL)
        return json.loads(txt)
    except Exception as e:
        print(f"[litellm] 抓取失败，跳过官方价自动刷新：{e}")
        return None


def per_million(v):
    """token 单价 -> 每百万单价。"""
    return round(v * 1_000_000, 6) if v is not None else None


def refresh_official_prices(data, litellm):
    """用 LiteLLM 数据刷新 models[].api（仅刷新命中的；offPeak 原样保留）。"""
    if not litellm:
        return 0
    updated = 0
    today = date.today().isoformat()
    for m in data["models"]:
        cand = LITELLM_MAP.get(m["id"], [])
        entry = None
        for key in cand:
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
        old = m["api"]
        m["api"]["input"] = inp
        m["api"]["output"] = out
        if cin is not None:
            m["api"]["cachedInput"] = cin
        # 保留已有的峰谷价（LiteLLM 一般不含）
        if "offPeak" in old:
            m["api"]["offPeak"] = old["offPeak"]
        tag = f"（每日自动从 LiteLLM 刷新 {today}）"
        base = old.get("note", "").split("（每日")[0].strip()
        m["api"]["note"] = base + tag
        updated += 1
        print(f"[litellm] 刷新 {m['id']}: in=${inp} out=${out} cache=${cin}")
    return updated


def main():
    with open(JSON_PATH, encoding="utf-8") as f:
        data = json.load(f)

    # 1) 官方价自动刷新（真实数据源，非伪造）
    litellm = fetch_litellm()
    n_refresh = refresh_official_prices(data, litellm)
    if n_refresh == 0:
        print("[litellm] 本轮无命中的官方价更新（极新型号尚未被收录，保留人工核到价）")

    # 2) 基本校验（模型中心结构）
    assert "models" in data and "plans" in data, "schema missing models/plans"
    mids = {m["id"] for m in data["models"]}
    assert all("api" in m for m in data["models"]), "每个 model 需含 api 基准价"
    for pl in data["plans"]:
        assert "id" in pl and "models" in pl, f"plan {pl.get('id')} malformed"
        for mid, entry in pl["models"].items():
            assert mid in mids, f"plan {pl['id']} 引用了未知模型 {mid}"
            if pl.get("byok"):
                assert "priceMultiplier" in entry, f"plan {pl['id']}/{mid} 缺 priceMultiplier(byok)"
            else:
                assert "allowanceUSD" in entry, f"plan {pl['id']}/{mid} 缺 allowanceUSD"

    # 3) 滚动更新时间
    data["meta"]["lastUpdated"] = date.today().isoformat()

    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    n_est = sum(
        1 for pl in data["plans"] for e in pl["models"].values() if e.get("source") == "estimated"
    )
    print(f"done: {len(data['plans'])} plans, {len(data['models'])} models, "
          f"官方价刷新={n_refresh}, 仍为估算的额度条目={n_est}")


if __name__ == "__main__":
    sys.exit(main())
