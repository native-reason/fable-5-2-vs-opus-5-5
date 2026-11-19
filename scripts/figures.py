"""Draw the paper's three figures from the CSV files in data/.

Usage: python scripts/figures.py
Run scripts/extract.py and scripts/extract_retests.py first. Writes into paper/figures/:
  fig1-every-run   every run of the matched bench pass, cost per run, Fable and Opus side by side
  fig2-ratios      Fable over Opus per bench job in the matched pass, cost and wall time
  fig3-research    the research re-test: cost of each run against the share of its checked claims with a problem
Each is an SVG (used in the PDF) with a PNG copy for previews.
"""
import csv
import datetime
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402

PAPER_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = PAPER_DIR / "paper" / "figures"
# Colours checked with the dataviz palette validator (light mode): both pass CVD and contrast checks.
# One colour pair across the whole series: blue is always Fable, orange is always Opus.
FABLE = "#2a78d6"
OPUS = "#eb6834"
INK = "#2b2b2b"
MUTED = "#8a8a86"
GRID = "#e6e6e3"
PRICE_RATIO = 2.0  # Fable 5.2 list price is exactly twice Opus 5.5's, input and output
FABLE_ID, OPUS_ID = "claude-fable-5-2", "claude-opus-5-5"


def log(message):
    stamp = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    print(f"{stamp} {message}", flush=True)


def read(name):
    with (PAPER_DIR / "data" / name).open(encoding="ascii") as handle:
        return list(csv.DictReader(handle))


def pick_font():
    """Palatino to sit beside the paper's body text; fall back quietly if the machine lacks it."""
    for family in ("Palatino Linotype", "Book Antiqua", "DejaVu Serif"):
        try:
            font_manager.findfont(family, fallback_to_default=False)
            return family
        except ValueError:
            continue
    return "serif"


def style(size=10):
    plt.rcParams.update({"font.family": pick_font(), "font.size": size, "axes.edgecolor": MUTED,
                         "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK, "svg.fonttype": "none"})


def tidy(ax):
    ax.grid(axis="x", color=GRID, linewidth=0.6, zorder=0)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.tick_params(axis="y", length=0)


def save(fig, stem):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for suffix in ("svg", "png"):
        path = OUT_DIR / f"{stem}.{suffix}"
        fig.savefig(path, dpi=200, bbox_inches="tight")
        log(f"wrote {path.relative_to(PAPER_DIR)}")
    plt.close(fig)


def draw_every_run(runs, pairs):
    """Figure 1: each run of the matched pass as a dot, cost per run on a log scale, mean as a short line."""
    by_key = {}
    for run in runs:
        if run["study"] == "matched" and not run["excluded"]:
            by_key.setdefault((run["task"], run["model"]), []).append(float(run["cost_usd"]))
    order = [p["task"] for p in sorted(pairs, key=lambda p: -float(p["opus_cost_usd"]))]
    style(9.5)
    fig, ax = plt.subplots(figsize=(6.6, 0.25 * len(order) + 1.4))
    offset = 0.18
    for row_index, task in enumerate(order):
        for model, colour, shift in ((FABLE_ID, FABLE, -offset), (OPUS_ID, OPUS, offset)):
            values = by_key.get((task, model), [])
            if not values:
                continue
            y = row_index + shift
            ax.scatter(values, [y] * len(values), s=26, color=colour, edgecolors="white", linewidths=0.6, zorder=4)
            mean = sum(values) / len(values)
            ax.plot([mean, mean], [y - 0.2, y + 0.2], color=INK, linewidth=1.8, zorder=6)
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels(order)
    ax.set_ylim(len(order) - 0.4, -0.6)
    ax.set_xscale("log")
    ax.set_xticks([0.03, 0.1, 0.3, 1, 3])
    ax.set_xticklabels(["$0.03", "$0.10", "$0.30", "$1", "$3"])
    ax.set_xlim(0.02, 5)
    ax.minorticks_off()
    ax.set_xlabel("Cost of one run (USD, log scale)")
    tidy(ax)
    handles = [plt.Line2D([], [], marker="o", linestyle="", color=FABLE, markersize=6),
               plt.Line2D([], [], marker="o", linestyle="", color=OPUS, markersize=6),
               plt.Line2D([], [], color=INK, linewidth=1.8)]
    fig.legend(handles, ["Fable 5.2, one run", "Opus 5.5, one run", "mean of the three runs"],
               loc="lower center", ncol=3, frameon=False, fontsize=9)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    save(fig, "fig1-every-run")


def draw_ratios(pairs):
    """Figure 2: Fable over Opus for each job in the matched pass, cost (a) and wall time (b), log scale."""
    order = sorted(pairs, key=lambda p: float(p["cost_ratio"]))
    rank = {p["task"]: index for index, p in enumerate(order)}
    style(9)
    fig, axes = plt.subplots(1, 2, figsize=(6.6, 0.22 * len(order) + 1.5), sharey=True)
    panels = (("cost_ratio", "Cost, Fable 5.2 / Opus 5.5", "(a) Cost per job"),
              ("time_ratio", "Wall time, Fable 5.2 / Opus 5.5", "(b) Time per job"))
    for ax, (key, xlabel, title) in zip(axes, panels):
        ax.axvline(1.0, color=MUTED, linewidth=0.8, zorder=1)
        ax.text(1.04, len(order) - 0.3, "equal", color=MUTED, fontsize=7.5, va="bottom")
        if key == "cost_ratio":
            ax.axvline(PRICE_RATIO, color=MUTED, linewidth=0.8, linestyle=(0, (3, 3)), zorder=1)
            ax.text(PRICE_RATIO * 1.04, len(order) - 0.3, "price ratio", color=MUTED, fontsize=7.5, va="bottom")
        shown = [p for p in order if p[key]]
        ax.scatter([float(p[key]) for p in shown], [rank[p["task"]] for p in shown], s=24, color=INK,
                   edgecolors="white", linewidths=0.6, zorder=4)
        ax.set_xscale("log")
        ax.set_xticks([0.25, 0.5, 1, 2, 4, 8])
        ax.set_xticklabels(["0.25", "0.5", "1", "2", "4", "8"])
        ax.minorticks_off()
        ax.set_xlim(0.22, 11)
        ax.set_xlabel(xlabel)
        ax.set_title(title, loc="left", fontsize=9, color=INK)
        tidy(ax)
    axes[0].set_yticks(range(len(order)))
    axes[0].set_yticklabels([p["task"] for p in order])
    axes[0].set_ylim(-0.7, len(order) + 0.5)
    fig.tight_layout()
    save(fig, "fig2-ratios")


def draw_research(retests):
    """Figure 3: research re-test runs, cost against the share of checked claims that had a problem."""
    rows = [r for r in retests if r["trial"] == "R"]
    style(10)
    fig, ax = plt.subplots(figsize=(6.6, 3.6))
    markers = {"R1": ("o", "packaging brief"), "R2": ("s", "accounting software brief")}
    colours = {"Fable 5.2": FABLE, "Opus 5.5": OPUS}
    for row in rows:
        marker, _ = markers[row["brief"]]
        ax.scatter(float(row["cost_usd"]), 100 * float(row["problem_rate"]), s=70, marker=marker,
                   color=colours[row["model"]], edgecolors="white", linewidths=0.8, zorder=4)
    ax.set_xlabel("Cost of the run (USD)")
    ax.set_ylabel("Checked claims with a problem (%)")
    ax.set_ylim(bottom=0)
    ax.set_xlim(left=0)
    ax.grid(color=GRID, linewidth=0.6, zorder=0)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    handles = [plt.Line2D([], [], marker="o", linestyle="", color=FABLE, markersize=8),
               plt.Line2D([], [], marker="o", linestyle="", color=OPUS, markersize=8),
               plt.Line2D([], [], marker="o", linestyle="", color=MUTED, markersize=8),
               plt.Line2D([], [], marker="s", linestyle="", color=MUTED, markersize=8)]
    ax.legend(handles, ["Fable 5.2", "Opus 5.5", markers["R1"][1], markers["R2"][1]],
              loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=4, frameon=False, fontsize=9)
    fig.tight_layout()
    save(fig, "fig3-research")


def main():
    pairs = read("pairs_matched.csv")
    retests = read("retests.csv")
    if not pairs or not retests:
        log("a data file is empty; run scripts/extract.py and scripts/extract_retests.py first")
        return 1
    draw_every_run(read("runs.csv"), pairs)
    draw_ratios(pairs)
    draw_research(retests)
    return 0


if __name__ == "__main__":
    sys.exit(main())
