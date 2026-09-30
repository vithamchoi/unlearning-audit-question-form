#!/usr/bin/env python3
"""Figures for paper 05. Every value is read from the raw audit log."""
import collections
import statistics
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import figstyle as F  # noqa: E402
from analysis import (Data, LABEL, STRATEGIES, audit_normalised,  # noqa: E402
                      audit_shipped)

import matplotlib.pyplot as plt  # noqa: E402

RES = Path(sys.argv[1] if len(sys.argv) > 1 else "../results")
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "figures")
OUT.mkdir(parents=True, exist_ok=True)
F.use_style()
D = Data(RES)

SHORT = {"none": "none", "prompt_filter": "prompt\nfilter",
         "output_filter": "output\nfilter", "sentinel": "sentinel"}

# --------------------------------------------------------------- Figure 1
fig, ax = plt.subplots(figsize=(5.4, 2.5))
x = np.arange(len(STRATEGIES))
w = 0.38
ship = [100 * D.k(s) / D.n for s in STRATEGIES]
norm = [100 * D.k(s, audit_normalised) / D.n for s in STRATEGIES]
cis = [D.cluster_ci(s) for s in STRATEGIES]
err = np.array([[v - 100 * lo for v, (lo, _) in zip(ship, cis)],
                [100 * hi - v for v, (_, hi) in zip(ship, cis)]])
ax.bar(x - w / 2, ship, w, label="shipped audit", color=F.C[0])
ax.errorbar(x - w / 2, ship, yerr=err, fmt="none", ecolor=F.INK,
            elinewidth=0.8, capsize=2.5)
ax.bar(x + w / 2, norm, w, label="normalised audit", color=F.C[1])
for xi, v, (_, hi) in zip(x - w / 2, ship, cis):
    ax.text(xi, max(v, 100 * hi) + 2.4, f"{v:.2f}", ha="center", fontsize=6.6)
for xi, v in zip(x + w / 2, norm):
    ax.text(xi, v + 2.2, f"{v:.2f}", ha="center", fontsize=6.6)
ax.set_xticks(x)
ax.set_xticklabels([SHORT[s] for s in STRATEGIES])
ax.set_ylabel("audit pass rate (%)")
ax.set_ylim(0, 122)
ax.set_yticks([0, 25, 50, 75, 100])
F.tidy(ax)
F.place_legend(ax, ncol=1, allowed=["upper left"])
F.save(fig, OUT / "fig_passrate.pdf")

# --------------------------------------------------------------- Figure 2
fig, ax = plt.subplots(figsize=(5.4, 2.4))
vs = D.variants()
labels = [v[0].replace(" ", "␣") for v in vs]
cnt = [v[1] for v in vs]
seen = [v[2] for v in vs]
scrub = [v[3] for v in vs]
y = np.arange(len(vs))[::-1]
cols = [F.C[2] if sc else (F.C[3] if se else F.C[1]) for se, sc in zip(seen, scrub)]
ax.barh(y, cnt, color=cols, height=0.62)
for yi, c in zip(y, cnt):
    ax.text(c + 12, yi, str(c), va="center", fontsize=6.8)
ax.set_yticks(y)
ax.set_yticklabels(labels, fontname="DejaVu Sans Mono", fontsize=6.8)
ax.set_xlabel("occurrences across all \\Nrows{} logged responses".replace("\\Nrows{}", str(D.n_lines)))
ax.set_xlim(0, max(cnt) * 1.14)
F.tidy(ax)
handles = [plt.Rectangle((0, 0), 1, 1, color=F.C[2]),
           plt.Rectangle((0, 0), 1, 1, color=F.C[3]),
           plt.Rectangle((0, 0), 1, 1, color=F.C[1])]
F.place_legend(ax, handles,
               ["removed by the filter, seen by the audit",
                "seen by the audit, not removed",
                "invisible to both"])
F.save(fig, OUT / "fig_variants.pdf")

# --------------------------------------------------------------- Figure 3
from analysis import CATEGORIES, CAT_LABEL  # noqa: E402

fig, ax = plt.subplots(figsize=(5.4, 2.6))
cols = {"blocked": "#9e9e9e", "leak_caught": F.C[1], "leak_missed": F.C[4],
        "scrubbed": F.C[3], "refusal": F.C[5], "clean": F.C[2]}
y = np.arange(len(STRATEGIES))[::-1]
left = np.zeros(len(STRATEGIES))
for cat in CATEGORIES:
    vals = np.array([D.counts(s)[cat] for s in STRATEGIES], dtype=float)
    ax.barh(y, vals, left=left, height=0.6, color=cols[cat], label=CAT_LABEL[cat])
    for yi, v, l in zip(y, vals, left):
        if v >= 40:
            ax.text(l + v / 2, yi, f"{int(v)}", ha="center", va="center",
                    fontsize=6.6, color="white")
    left += vals
ax.set_yticks(y)
ax.set_yticklabels(list(STRATEGIES), fontsize=7.5)
ax.set_xlabel("responses (out of %d per strategy)" % D.n)
ax.set_xlim(0, D.n)
ax.grid(axis="y", visible=False)
F.tidy(ax)
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.34), ncol=2, fontsize=6.8)
F.save(fig, OUT / "fig_outcomes.pdf")

# --------------------------------------------------------------- Figure 4
fig, ax = plt.subplots(figsize=(5.4, 2.3))
for i, s in enumerate(["none", "output_filter", "sentinel"]):
    outs = D.passes(s)
    frac = sorted(sum(outs[j] for j in idx) / len(idx)
                  for idx in D.clusters.values())
    ax.plot(np.arange(1, len(frac) + 1), [100 * v for v in frac],
            label=s.replace("_", " "), color=F.C[i], lw=1.3)
ax.set_xlabel("distinct prompt, ordered by replicate pass fraction "
              f"($k={len(D.distinct)}$)")
ax.set_ylabel("% of replicates passing")
ax.set_ylim(-4, 104)
ax.set_xlim(1, len(D.distinct))
F.tidy(ax)
F.place_legend(ax)
F.save(fig, OUT / "fig_clusters.pdf")
print("figures done")
