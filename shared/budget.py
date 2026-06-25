#!/usr/bin/env python3
"""
Monthly budget tracker for all Studio API spend.

Tracks actual usage and cost across every service. Alerts before limits are hit.
Pipelines call budget.charge() before making API calls — if over budget, they stop.

Usage:
  python -m shared.budget --status          # current month spend
  python -m shared.budget --history         # last 3 months
  python -m shared.budget --reset           # reset current month (careful!)
  python -m shared.budget --set-limit elevenlabs 22.00
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, date
from pathlib import Path
from typing import Literal

# ---------------------------------------------------------------------------
# Service definitions with pricing
# ---------------------------------------------------------------------------

Service = Literal[
    "elevenlabs",   # TTS
    "openai",       # GPT-4 validation/review
    "anthropic",    # Claude Code API (if used programmatically)
    "suno",         # Music generation (if switched from MusicGen)
    "runpod",       # GPU hours
    "newsapi",      # News API
    "gnews",        # GNews
    "stability",    # Stable Diffusion images
]

# Default monthly budget limits (USD) — edit these to match your actual plan
DEFAULT_LIMITS: dict[str, float] = {
    "elevenlabs": 22.00,    # Creator plan
    "openai": 50.00,        # GPT-4 validation budget
    "anthropic": 30.00,     # Claude API (if used)
    "suno": 0.00,           # Not active (using MusicGen)
    "runpod": 100.00,       # GPU hours budget
    "newsapi": 0.00,        # Free tier
    "gnews": 0.00,          # Free tier
    "stability": 20.00,     # Image generation
}

# Pricing per unit (keep updated as prices change)
UNIT_PRICING: dict[str, dict] = {
    "elevenlabs": {
        "chars": 0.00022,       # ~$22 per 100K chars (Creator plan flat, tracked for usage)
    },
    "openai": {
        "gpt4o_input_1k": 0.0025,    # GPT-4o input per 1K tokens
        "gpt4o_output_1k": 0.010,    # GPT-4o output per 1K tokens
        "gpt4_input_1k": 0.030,      # GPT-4 input per 1K tokens
        "gpt4_output_1k": 0.060,     # GPT-4 output per 1K tokens
        "gpt35_input_1k": 0.0005,    # GPT-3.5 input per 1K tokens
        "gpt35_output_1k": 0.0015,   # GPT-3.5 output per 1K tokens
    },
    "anthropic": {
        "sonnet_input_1k": 0.003,    # Claude Sonnet 4.6 input per 1K tokens
        "sonnet_output_1k": 0.015,   # Claude Sonnet 4.6 output per 1K tokens
        "haiku_input_1k": 0.00025,
        "haiku_output_1k": 0.00125,
    },
    "runpod": {
        "rtx4090_hr": 0.74,    # RTX 4090 per hour
        "a10g_hr": 0.39,       # A10G per hour
        "a100_hr": 1.64,       # A100 per hour
    },
    "stability": {
        "sdxl_image": 0.002,   # per image (approximate)
        "sd3_image": 0.065,    # SD3 per image
    },
}

# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

BUDGET_FILE = Path(__file__).parent.parent / "config" / "budget.json"


def _load() -> dict:
    if BUDGET_FILE.exists():
        return json.loads(BUDGET_FILE.read_text())
    return {"limits": DEFAULT_LIMITS.copy(), "months": {}}


def _save(data: dict) -> None:
    BUDGET_FILE.parent.mkdir(exist_ok=True)
    BUDGET_FILE.write_text(json.dumps(data, indent=2))


def _month_key() -> str:
    return date.today().strftime("%Y-%m")


def _get_month(data: dict, month: str | None = None) -> dict:
    key = month or _month_key()
    if key not in data["months"]:
        data["months"][key] = {}
    return data["months"][key]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def charge(service: str, cost_usd: float, description: str = "") -> bool:
    """
    Record a charge and check if we're still within budget.

    Returns True if OK to proceed, False if over budget.
    Pipelines should check the return value before making API calls.
    """
    data = _load()
    month = _get_month(data)

    if service not in month:
        month[service] = {"total": 0.0, "charges": []}

    month[service]["total"] = round(month[service]["total"] + cost_usd, 6)
    month[service]["charges"].append({
        "ts": datetime.utcnow().isoformat(),
        "cost": cost_usd,
        "note": description,
    })

    _save(data)

    limit = data["limits"].get(service, 0)
    if limit > 0 and month[service]["total"] > limit:
        print(f"  BUDGET ALERT: {service} over limit "
              f"(${month[service]['total']:.2f} / ${limit:.2f})")
        return False
    if limit > 0 and month[service]["total"] > limit * 0.8:
        print(f"  BUDGET WARNING: {service} at "
              f"{month[service]['total']/limit*100:.0f}% of monthly limit")
    return True


def estimate_openai(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate cost before making an OpenAI call."""
    p = UNIT_PRICING["openai"]
    if "gpt-4o" in model:
        return (input_tokens / 1000) * p["gpt4o_input_1k"] + (output_tokens / 1000) * p["gpt4o_output_1k"]
    elif "gpt-4" in model:
        return (input_tokens / 1000) * p["gpt4_input_1k"] + (output_tokens / 1000) * p["gpt4_output_1k"]
    return (input_tokens / 1000) * p["gpt35_input_1k"] + (output_tokens / 1000) * p["gpt35_output_1k"]


def estimate_elevenlabs(char_count: int) -> float:
    return char_count * UNIT_PRICING["elevenlabs"]["chars"]


def estimate_runpod(gpu: str, hours: float) -> float:
    key = f"{gpu}_hr"
    rate = UNIT_PRICING["runpod"].get(key, 0.74)
    return hours * rate


def get_status(month: str | None = None) -> dict:
    data = _load()
    key = month or _month_key()
    month_data = data["months"].get(key, {})
    limits = data["limits"]
    status = {}
    for service, limit in limits.items():
        spent = month_data.get(service, {}).get("total", 0.0)
        pct = (spent / limit * 100) if limit > 0 else 0
        status[service] = {
            "spent": spent,
            "limit": limit,
            "remaining": max(0, limit - spent),
            "pct": pct,
            "over": spent > limit if limit > 0 else False,
        }
    # Add any services with charges but no limit
    for service, info in month_data.items():
        if service not in status:
            status[service] = {
                "spent": info.get("total", 0.0),
                "limit": 0,
                "remaining": 0,
                "pct": 0,
                "over": False,
            }
    return {"month": key, "services": status,
            "total_spent": sum(v["spent"] for v in status.values()),
            "total_limit": sum(v["limit"] for v in status.values())}


def set_limit(service: str, limit_usd: float) -> None:
    data = _load()
    data["limits"][service] = limit_usd
    _save(data)


def print_status(month: str | None = None) -> None:
    s = get_status(month)
    print(f"\n{'='*55}")
    print(f"BUDGET STATUS — {s['month']}")
    print(f"{'='*55}")
    print(f"{'Service':<18} {'Spent':>8} {'Limit':>8} {'Remaining':>10} {'%':>5}")
    print(f"{'-'*55}")
    for svc, info in sorted(s["services"].items()):
        flag = " !!!" if info["over"] else (" !" if info["pct"] > 80 else "")
        limit_str = f"${info['limit']:.2f}" if info["limit"] > 0 else "  --  "
        rem_str = f"${info['remaining']:.2f}" if info["limit"] > 0 else "  --  "
        pct_str = f"{info['pct']:.0f}%" if info["limit"] > 0 else " --"
        print(f"{svc:<18} ${info['spent']:>7.2f} {limit_str:>8} {rem_str:>10} {pct_str:>5}{flag}")
    print(f"{'-'*55}")
    print(f"{'TOTAL':<18} ${s['total_spent']:>7.2f} ${s['total_limit']:>7.2f}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Studio monthly budget tracker")
    parser.add_argument("--status", action="store_true", help="Show current month")
    parser.add_argument("--history", action="store_true", help="Show last 3 months")
    parser.add_argument("--set-limit", nargs=2, metavar=("SERVICE", "USD"),
                        help="Set monthly limit for a service")
    parser.add_argument("--add-charge", nargs=3, metavar=("SERVICE", "COST", "NOTE"),
                        help="Manually record a charge")
    parser.add_argument("--month", default=None, help="YYYY-MM to inspect")
    args = parser.parse_args()

    if args.set_limit:
        svc, usd = args.set_limit
        set_limit(svc, float(usd))
        print(f"Set {svc} limit to ${float(usd):.2f}/month")
        return

    if args.add_charge:
        svc, cost, note = args.add_charge
        ok = charge(svc, float(cost), note)
        print(f"Charged ${float(cost):.4f} to {svc}. Budget OK: {ok}")
        return

    if args.history:
        data = _load()
        months = sorted(data["months"].keys(), reverse=True)[:3]
        for m in months:
            print_status(m)
        return

    print_status(args.month)


if __name__ == "__main__":
    main()
