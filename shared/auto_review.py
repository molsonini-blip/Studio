#!/usr/bin/env python3
"""
Automated code review loop — Claude writes, GPT validates, Claude applies fixes.

Workflow (no human input):
  1. Claude Code generates or modifies a Python file
  2. This module sends the code to GPT-4o for review
  3. GPT returns structured findings: bugs, improvements, test suggestions
  4. Findings are saved and optionally auto-applied via a second Claude API call
  5. Loop repeats until GPT gives a clean bill of health (or max iterations hit)

Usage:
  # Review a single file and print findings:
  python -m shared.auto_review --file music/pipeline.py

  # Review + auto-apply fixes (uses Claude API):
  python -m shared.auto_review --file music/pipeline.py --fix

  # Review all Python files changed since last commit:
  python -m shared.auto_review --changed

  # Run full review loop (review → fix → re-review) up to N times:
  python -m shared.auto_review --file music/pipeline.py --loop 3
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Literal

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shared import budget

ReviewSeverity = Literal["bug", "warning", "suggestion", "test"]

@dataclass
class ReviewFinding:
    severity: ReviewSeverity
    line: int | None
    description: str
    suggested_fix: str

@dataclass
class ReviewResult:
    file: str
    model: str
    timestamp: str
    passed: bool        # True if no bugs found
    findings: list[ReviewFinding]
    test_suggestions: list[str]
    summary: str

REVIEWS_DIR = Path(__file__).parent.parent / "config" / "reviews"

# ---------------------------------------------------------------------------
# GPT-4o review prompt
# ---------------------------------------------------------------------------

_REVIEW_SYSTEM = """You are a senior Python engineer reviewing code for a production AI content pipeline.
Be direct, specific, and actionable. Focus on:

1. BUGS: Logic errors, off-by-one, race conditions, unhandled exceptions, wrong assumptions
2. WARNINGS: Code that will work but is fragile, inefficient, or will cause problems at scale
3. SUGGESTIONS: Simplifications, better stdlib usage, missing edge case handling
4. TESTS: Specific test cases the code needs (input → expected output)

Do NOT flag:
- Style issues (PEP8, formatting) unless they cause bugs
- Missing docstrings or comments
- Abstractions the code doesn't need yet

Return ONLY valid JSON:
{
  "passed": true|false,
  "summary": "one sentence — what is this code, is it correct?",
  "findings": [
    {
      "severity": "bug|warning|suggestion|test",
      "line": null or line number,
      "description": "specific problem",
      "suggested_fix": "exact fix — code snippet if applicable"
    }
  ],
  "test_suggestions": [
    "describe a specific test case: input X → expected output Y"
  ]
}

If no bugs found and code looks correct: set passed=true and findings may be empty or suggestions only."""

_FIX_SYSTEM = """You are a senior Python engineer. You receive code and a list of review findings.
Apply ALL fixes marked as 'bug'. Apply 'warning' and 'suggestion' fixes if they are clearly correct.
Skip 'test' findings (those are test suggestions, not code changes).

Return ONLY the corrected Python code. No explanation, no markdown fences."""


# ---------------------------------------------------------------------------
# OpenAI call
# ---------------------------------------------------------------------------

def _call_gpt(prompt: str, system: str, model: str = "gpt-4o") -> str:
    try:
        import openai
    except ImportError:
        print("Install openai: pip install openai")
        sys.exit(1)

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set in environment")

    client = openai.OpenAI(api_key=api_key)

    # Estimate cost before calling
    est_input = len(prompt.split()) + len(system.split())
    est_cost = budget.estimate_openai(model, est_input * 1.3, 800)
    if not budget.charge("openai", est_cost, f"auto_review {model}"):
        raise RuntimeError("OpenAI budget exceeded — review aborted")

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        max_tokens=2000,
    )
    return resp.choices[0].message.content.strip()


# ---------------------------------------------------------------------------
# Claude API apply-fixes call
# ---------------------------------------------------------------------------

def _call_claude(prompt: str, system: str, model: str = "claude-haiku-4-5-20251001") -> str:
    try:
        import anthropic
    except ImportError:
        print("Install anthropic: pip install anthropic")
        sys.exit(1)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set in environment")

    client = anthropic.Anthropic(api_key=api_key)
    est_cost = budget.estimate_openai(model, len(prompt.split()) * 1.3, 2000)
    budget.charge("anthropic", est_cost * 0.1, f"auto_fix {model}")  # Haiku is cheap

    resp = client.messages.create(
        model=model,
        max_tokens=4096,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text.strip()


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def review_file(file_path: Path, model: str = "gpt-4o") -> ReviewResult:
    """Send a file to GPT-4o for code review."""
    code = file_path.read_text(encoding="utf-8")
    prompt = (
        f"File: {file_path.name}\n\n"
        f"```python\n{code}\n```\n\n"
        f"Review this code for bugs, issues, and test gaps."
    )

    raw = _call_gpt(prompt, _REVIEW_SYSTEM, model)
    # Strip fences if present
    import re
    clean = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
    clean = re.sub(r"\s*```$", "", clean, flags=re.MULTILINE).strip()
    data = json.loads(clean)

    findings = [
        ReviewFinding(
            severity=f.get("severity", "suggestion"),
            line=f.get("line"),
            description=f.get("description", ""),
            suggested_fix=f.get("suggested_fix", ""),
        )
        for f in data.get("findings", [])
    ]
    return ReviewResult(
        file=str(file_path),
        model=model,
        timestamp=datetime.utcnow().isoformat(),
        passed=data.get("passed", False),
        findings=findings,
        test_suggestions=data.get("test_suggestions", []),
        summary=data.get("summary", ""),
    )


def apply_fixes(file_path: Path, result: ReviewResult) -> bool:
    """Apply bug fixes via Claude API. Returns True if file was changed."""
    bugs = [f for f in result.findings if f.severity == "bug"]
    if not bugs:
        return False

    code = file_path.read_text(encoding="utf-8")
    findings_text = "\n".join(
        f"[{f.severity.upper()}] Line {f.line}: {f.description}\nFix: {f.suggested_fix}"
        for f in result.findings
        if f.severity in ("bug", "warning", "suggestion")
    )
    prompt = (
        f"Code:\n```python\n{code}\n```\n\n"
        f"Review findings:\n{findings_text}\n\n"
        f"Return the corrected Python code only."
    )

    fixed = _call_claude(prompt, _FIX_SYSTEM)
    # Strip any accidental markdown fences
    import re
    fixed = re.sub(r"^```python\s*", "", fixed, flags=re.MULTILINE)
    fixed = re.sub(r"\s*```$", "", fixed, flags=re.MULTILINE).strip()

    if fixed and fixed != code:
        # Back up original
        backup = file_path.with_suffix(f".{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak")
        backup.write_text(code, encoding="utf-8")
        file_path.write_text(fixed, encoding="utf-8")
        print(f"  Fixes applied. Backup: {backup.name}")
        return True
    return False


def save_review(result: ReviewResult) -> Path:
    REVIEWS_DIR.mkdir(parents=True, exist_ok=True)
    stem = Path(result.file).stem
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = REVIEWS_DIR / f"{stem}_{ts}.json"
    out.write_text(json.dumps(asdict(result), indent=2))
    return out


def print_result(result: ReviewResult) -> None:
    status = "PASS" if result.passed else "FAIL"
    print(f"\n{'='*55}")
    print(f"REVIEW: {Path(result.file).name}  [{status}]  ({result.model})")
    print(f"Summary: {result.summary}")
    if result.findings:
        print(f"\nFindings ({len(result.findings)}):")
        for f in result.findings:
            line_str = f" line {f.line}" if f.line else ""
            print(f"  [{f.severity.upper():10}]{line_str}: {f.description}")
            if f.suggested_fix:
                print(f"    Fix: {f.suggested_fix[:120]}")
    if result.test_suggestions:
        print(f"\nTest suggestions:")
        for t in result.test_suggestions:
            print(f"  • {t}")


def get_changed_files() -> list[Path]:
    """Get Python files changed since last git commit."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            capture_output=True, text=True, cwd=Path(__file__).parent.parent
        )
        files = [Path(f) for f in result.stdout.strip().splitlines() if f.endswith(".py")]
        return [f for f in files if f.exists()]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Automated GPT-4o code review loop")
    parser.add_argument("--file", help="Python file to review")
    parser.add_argument("--changed", action="store_true",
                        help="Review all files changed since last git commit")
    parser.add_argument("--fix", action="store_true",
                        help="Auto-apply bug fixes via Claude API")
    parser.add_argument("--loop", type=int, default=1,
                        help="Number of review→fix iterations (default: 1)")
    parser.add_argument("--model", default="gpt-4o",
                        help="GPT model for review (default: gpt-4o)")
    parser.add_argument("--save", action="store_true",
                        help="Save review results to config/reviews/")
    args = parser.parse_args()

    if args.changed:
        files = get_changed_files()
        if not files:
            print("No changed Python files found.")
            return
    elif args.file:
        files = [Path(args.file)]
    else:
        parser.print_help()
        return

    for fp in files:
        print(f"\nReviewing {fp} ...")
        for iteration in range(args.loop):
            if args.loop > 1:
                print(f"  Iteration {iteration + 1}/{args.loop}")
            result = review_file(fp, model=args.model)
            print_result(result)
            if args.save:
                saved = save_review(result)
                print(f"  Saved to {saved}")
            if result.passed:
                print("  Clean — no further iterations needed.")
                break
            if args.fix and not result.passed:
                changed = apply_fixes(fp, result)
                if not changed:
                    print("  No auto-fixable bugs found.")
                    break


if __name__ == "__main__":
    main()
