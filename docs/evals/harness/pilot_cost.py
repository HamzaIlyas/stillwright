#!/usr/bin/env python3
"""Cost per verified pass per arm, and the with/plain ratio with a cluster bootstrap over tasks.

    pilot_cost.py <with-results.csv> <plain-results.csv> [--seed 20261105] [--boot 10000]

Cost per verified pass = sum of cost_usd over every scored row of the arm (void and error rows cost too)
divided by the number of rows with verdict `pass`. The unit of resampling is the task: the same resampled
task list is applied to both arms, the two sums and the ratio are recomputed, and the 2.5 and 97.5
percentiles of the ratio are the interval. An interval that includes 1 means unresolved at this number of
tasks, not no difference.
"""
from __future__ import annotations

import argparse
import csv
import random
from collections import defaultdict


def _cost(r: dict) -> float:
    v = r.get("cost_usd", "")
    if v in ("", "None"):
        raise SystemExit(f"row {r.get('task')}/{r.get('epoch')} has no cost_usd; every scored run must carry its receipt cost")
    return float(v)


def cost_per_pass(rows: list[dict]) -> float:
    total = sum(_cost(r) for r in rows)
    passes = sum(1 for r in rows if r["verdict"] == "pass")
    return total / passes if passes else float("inf")


def _by_task(rows: list[dict]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        out[r["task"]].append(r)
    return out


def ratio_ci(with_rows: list[dict], plain_rows: list[dict], seed: int = 20261105, b: int = 10000) -> tuple[float, float, float]:
    w, p = _by_task(with_rows), _by_task(plain_rows)
    tasks = sorted(set(w) | set(p))
    rng = random.Random(seed)
    ratios = []
    for _ in range(b):
        sample = rng.choices(tasks, k=len(tasks))
        wr = [r for t in sample for r in w.get(t, [])]
        pr = [r for t in sample for r in p.get(t, [])]
        ratios.append(_ratio(cost_per_pass(wr), cost_per_pass(pr)))
    ratios.sort()
    point = _ratio(cost_per_pass(with_rows), cost_per_pass(plain_rows))
    lo_i, hi_i = round(0.025 * (b - 1)), round(0.975 * (b - 1))
    return ratios[lo_i], ratios[hi_i], point


def _ratio(cw: float, cp: float) -> float:
    """with/plain; no passes on either side is infinity (undefined), reported as such rather than hidden."""
    if cw == float("inf") or cp == float("inf") or cp == 0.0:
        return float("inf")
    return cw / cp


def load(path: str) -> list[dict]:
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    bad = [r for r in rows if r["verdict"] == "unscored"]
    if bad:
        raise SystemExit(f"{len(bad)} unscored rows in {path}")
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("with_csv")
    ap.add_argument("plain_csv")
    ap.add_argument("--seed", type=int, default=20261105)
    ap.add_argument("--boot", type=int, default=10000)
    a = ap.parse_args()
    w, p = load(a.with_csv), load(a.plain_csv)
    lo, hi, point = ratio_ci(w, p, a.seed, a.boot)
    for name, rows in (("with", w), ("plain", p)):
        passes = sum(1 for r in rows if r["verdict"] == "pass")
        total = sum(_cost(r) for r in rows)
        print(f"{name}: {len(rows)} runs, {passes} verified passes, {total:.3f} USD, {cost_per_pass(rows):.4f} USD per verified pass")
    print(f"ratio with/plain: {point:.2f} (95% task-bootstrap interval {lo:.2f}–{hi:.2f}, B={a.boot}, seed {a.seed}, {len(_by_task(w))} tasks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
