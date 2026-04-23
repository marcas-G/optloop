#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path
from statistics import mean, median, pstdev
from typing import Any


def load_samples(path: Path) -> list[float]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        return [float(x) for x in raw]
    if isinstance(raw, dict) and isinstance(raw.get("samples"), list):
        return [float(x) for x in raw["samples"]]
    raise ValueError(f"{path} must contain a list or an object with a 'samples' list")


def bootstrap_means(samples: list[float], iterations: int, seed: int) -> list[float]:
    rnd = random.Random(seed)
    n = len(samples)
    out = []
    for _ in range(iterations):
        draw = [samples[rnd.randrange(n)] for _ in range(n)]
        out.append(mean(draw))
    out.sort()
    return out


def quantile(sorted_values: list[float], q: float) -> float:
    if not sorted_values:
        raise ValueError("no values")
    if q <= 0:
        return sorted_values[0]
    if q >= 1:
        return sorted_values[-1]
    idx = q * (len(sorted_values) - 1)
    lo = math.floor(idx)
    hi = math.ceil(idx)
    if lo == hi:
        return sorted_values[lo]
    frac = idx - lo
    return sorted_values[lo] * (1 - frac) + sorted_values[hi] * frac


def relative_improvement(baseline_mean: float, candidate_mean: float, direction: str) -> float:
    if baseline_mean == 0:
        return 0.0
    if direction == "lower":
        return (baseline_mean - candidate_mean) / baseline_mean
    if direction == "higher":
        return (candidate_mean - baseline_mean) / baseline_mean
    raise ValueError("direction must be 'lower' or 'higher'")


def decide(baseline: list[float], candidate: list[float], direction: str, min_relative_improvement: float, confidence: float, iterations: int, seed: int) -> dict[str, Any]:
    if len(baseline) < 2 or len(candidate) < 2:
        return {
            "decision": "RERUN",
            "reason": "too-few-samples",
            "baseline_samples": len(baseline),
            "candidate_samples": len(candidate)
        }

    baseline_mean = mean(baseline)
    candidate_mean = mean(candidate)
    baseline_boot = bootstrap_means(baseline, iterations, seed)
    candidate_boot = bootstrap_means(candidate, iterations, seed + 1)

    diff_boot = []
    rel_boot = []
    for b, c in zip(baseline_boot, candidate_boot):
        diff_boot.append((b - c) if direction == "lower" else (c - b))
        rel_boot.append(relative_improvement(b, c, direction))

    diff_boot.sort()
    rel_boot.sort()

    alpha = 1.0 - confidence
    lower_q = alpha / 2.0
    upper_q = 1.0 - lower_q
    diff_ci = [quantile(diff_boot, lower_q), quantile(diff_boot, upper_q)]
    rel_ci = [quantile(rel_boot, lower_q), quantile(rel_boot, upper_q)]
    rel_point = relative_improvement(baseline_mean, candidate_mean, direction)

    favorable = diff_ci[0] > 0 and rel_ci[0] >= min_relative_improvement
    unfavorable = diff_ci[1] < 0 or rel_ci[1] < 0

    if favorable:
        decision = "ACCEPT"
        reason = "confidence-interval-supports-improvement"
    elif unfavorable:
        decision = "REJECT"
        reason = "confidence-interval-does-not-support-improvement"
    else:
        decision = "RERUN"
        reason = "uncertain-result"

    return {
        "decision": decision,
        "reason": reason,
        "direction": direction,
        "baseline": {
            "count": len(baseline),
            "mean": baseline_mean,
            "median": median(baseline),
            "stdev": pstdev(baseline)
        },
        "candidate": {
            "count": len(candidate),
            "mean": candidate_mean,
            "median": median(candidate),
            "stdev": pstdev(candidate)
        },
        "relative_improvement_point_estimate": rel_point,
        "relative_improvement_ci": rel_ci,
        "absolute_favorable_difference_ci": diff_ci,
        "min_relative_improvement": min_relative_improvement,
        "confidence": confidence
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap-based metric acceptance gate for repository optimization.")
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--direction", choices=["lower", "higher"], required=True)
    parser.add_argument("--min-relative-improvement", type=float, default=0.03)
    parser.add_argument("--confidence", type=float, default=0.95)
    parser.add_argument("--iterations", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=1337)
    args = parser.parse_args()

    result = decide(
        baseline=load_samples(args.baseline),
        candidate=load_samples(args.candidate),
        direction=args.direction,
        min_relative_improvement=args.min_relative_improvement,
        confidence=args.confidence,
        iterations=args.iterations,
        seed=args.seed,
    )
    print(json.dumps(result, indent=2))
    return 0 if result["decision"] == "ACCEPT" else 1


if __name__ == "__main__":
    raise SystemExit(main())
