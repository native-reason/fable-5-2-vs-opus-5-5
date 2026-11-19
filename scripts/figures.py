"""Draw the paper's figure from data/pairs_study1.csv and data/pairs_study2.csv.

Usage: python scripts/figures.py
Writes the five figures into paper/figures/, each file numbered as in the paper: fig1-method, fig2-same-or-different,
fig3-ratios, fig4-every-run and fig5-totals.
Each is an SVG (used in the PDF) with a PNG copy for previews.
"""
import csv
import datetime
import random
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402

PAPER_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = PAPER_DIR / "paper" / "figures"
# Colours checked with the dataviz palette validator (light mode): both pass CVD and contrast checks.
# One colour pair across the whole series: blue is always Fable, orange is always Opus. The two studies are told
# apart by filled dark dots (Study 2) and open grey circles (Study 1), never by the model colours.
FABLE = "#2a78d6"
OPUS = "#eb6834"
STUDY2 = "#2b2b2b"
STUDY1 = "#6b6b66"
INK = "#2b2b2b"
MUTED = "#8a8a86"
# Rules fixed before Study 1 (paper Section 2.6): scores within 0.02 are the same; time or cost must differ
# by at least 15 percent to count as different.
SCORE_TOLERANCE = 0.02
RATIO_TOLERANCE = 1.15
BOOTSTRAP_RESAMPLES = 10000
BOOTSTRAP_SEED = 20261119
GREY = "#b3b3ae"
PRICE_RATIO = 2.0  # Fable 5.2 list price is exactly twice Opus 5.5's, input and output


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


def draw_method(font):
    """Figure 1: how one bench run works, as five boxes in a row and a loop arrow for the repeats."""
    from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
    steps = [("1. The job", "A prompt and\nmade-up files,\ncopied from a\nreal job"),
             ("2. The set-up", "One laptop, one\nClaude Code\nversion, no\npersonal settings"),
             ("3. The model", "Named by full\nidentifier, at one\neffort setting"),
             ("4. The run", "Time, cost and\noutput tokens\nlogged by\nClaude Code"),
             ("5. The marking", "Code checks the\nresult against a\nkey or hidden\ntests: score 0-1")]
    plt.rcParams.update({"font.family": font, "font.size": 8.5, "svg.fonttype": "none"})
    fig, ax = plt.subplots(figsize=(6.6, 2.35))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 36)
    ax.axis("off")
    width, gap, top, height = 17.2, 3.5, 11, 22
    centres = []
    for index, (title, body) in enumerate(steps):
        left = index * (width + gap)
        accent = INK if index in (2, 4) else MUTED
        ax.add_patch(FancyBboxPatch((left, top), width, height, boxstyle="round,pad=0,rounding_size=1.2",
                                    facecolor="white", edgecolor=accent, linewidth=1.2))
        ax.text(left + width / 2, top + height - 3.2, title, ha="center", va="center", fontsize=7.8,
                fontweight="bold", color=INK)
        ax.text(left + width / 2, top + height / 2 - 2.5, body, ha="center", va="center", fontsize=7.4,
                color=INK, linespacing=1.3)
        centres.append(left + width / 2)
        if index:
            ax.add_patch(FancyArrowPatch((left - gap + 0.3, top + height / 2), (left - 0.3, top + height / 2),
                                         arrowstyle="-|>", mutation_scale=9, color=MUTED, linewidth=1.0))
    ax.add_patch(FancyArrowPatch((centres[4], top - 0.5), (centres[2], top - 0.5), connectionstyle="arc3,rad=-0.35",
                                 arrowstyle="-|>", mutation_scale=9, color=INK, linewidth=1.1))
    ax.text((centres[2] + centres[4]) / 2, 1.2, "repeated two or three times; in Study 2 both models on the same night",
            ha="center", va="center", fontsize=7.6, color=INK)
    for suffix in ("svg", "png"):
        path = OUT_DIR / f"fig1-method.{suffix}"
        fig.savefig(path, dpi=200, bbox_inches="tight")
        log(f"wrote {path.relative_to(PAPER_DIR)}")
    plt.close(fig)


def save(fig, stem):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for suffix in ("svg", "png"):
        path = OUT_DIR / f"{stem}.{suffix}"
        fig.savefig(path, dpi=200, bbox_inches="tight")
        log(f"wrote {path.relative_to(PAPER_DIR)}")
    plt.close(fig)


def big_style(font):
    """Larger type for the three newer figures so they read on a phone."""
    plt.rcParams.update({"font.family": font, "font.size": 11, "axes.edgecolor": MUTED,
                         "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK, "svg.fonttype": "none"})


def classify_score(row):
    gap = float(row["fable_score"]) - float(row["opus_score"])
    return "same" if abs(gap) <= SCORE_TOLERANCE + 1e-9 else ("fable" if gap > 0 else "opus")


def classify_ratio(row, key):
    """Fable / Opus ratio: 'opus' means Opus ahead (Fable dearer or slower), 'fable' means Fable ahead."""
    ratio = float(row[key])
    if ratio >= RATIO_TOLERANCE:
        return "opus"
    if ratio <= 1 / RATIO_TOLERANCE:
        return "fable"
    return "same"


def draw_same_or_different(study1, study2):
    """Figure 2: stacked bars of how many jobs came out level, Fable ahead or Opus ahead."""
    rows = []
    for label, pairs in (("Study 1", study1), ("Study 2", study2)):
        for measure, classify in (("Score", classify_score),
                                  ("Cost", lambda r: classify_ratio(r, "cost_ratio")),
                                  ("Time", lambda r: classify_ratio(r, "time_ratio"))):
            counts = {"opus": 0, "same": 0, "fable": 0}
            for pair in pairs:
                counts[classify(pair)] += 1
            rows.append((measure, label, len(pairs), counts))
            log(f"same-or-different {label} {measure}: {counts}")
    big_style(pick_font())
    fig, ax = plt.subplots(figsize=(6.6, 4.3))
    colours = {"fable": FABLE, "same": GREY, "opus": OPUS}
    positions = [0, 1, 2, 3.9, 4.9, 5.9]
    for position, (measure, label, total, counts) in zip(positions, rows):
        left = 0
        for key in ("fable", "same", "opus"):
            width = counts[key] / total * 100
            ax.barh(position, width, left=left, color=colours[key], edgecolor="white", linewidth=1.5, height=0.72)
            if counts[key]:
                ax.text(left + width / 2, position, str(counts[key]), ha="center", va="center", fontsize=12,
                        color="white" if key != "same" else INK, fontweight="bold")
            left += width
    ax.set_yticks(positions)
    ax.set_yticklabels([r[0] for r in rows])
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xticklabels(["0", "25", "50", "75", "100%"])
    ax.text(101, 1, "Study 1\n24 jobs", va="center", ha="left", fontsize=11, color=INK)
    ax.text(101, 4.9, "Study 2\n8 pairings", va="center", ha="left", fontsize=11, color=INK)
    ax.tick_params(axis="y", length=0)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    handles = [plt.Rectangle((0, 0), 1, 1, color=colours[k]) for k in ("fable", "same", "opus")]
    ax.legend(handles, ["Fable ahead", "About the same", "Opus ahead"], loc="upper center",
              bbox_to_anchor=(0.5, -0.1), ncol=3, frameon=False, fontsize=11)
    fig.tight_layout()
    save(fig, "fig2-same-or-different")


def draw_every_run(runs, study2):
    """Figure 4: every Study 2 run as a dot, cost per run, Fable and Opus side by side, mean as a short line."""
    efforts = {(r["task"], r["fable_effort"]): r for r in study2}
    by_key = {}
    for run in runs:
        if run["study"] != "study2" or run.get("excluded"):
            continue
        by_key.setdefault((run["task"], run["effort"], run["model"]), []).append(float(run["cost_usd"]))
    order = sorted(efforts, key=lambda k: -float(efforts[k]["opus_cost_usd"]))
    big_style(pick_font())
    fig, ax = plt.subplots(figsize=(6.6, 4.6))
    offset = 0.17
    for row_index, key in enumerate(order):
        task, effort = key
        for model, colour, shift in (("claude-fable-5-2", FABLE, -offset), ("claude-opus-5-5", OPUS, offset)):
            values = by_key[(task, effort, model)]
            y = row_index + shift
            ax.scatter(values, [y] * len(values), s=70, color=colour, edgecolors="white", linewidths=0.8, zorder=4)
            mean = sum(values) / len(values)
            ax.plot([mean, mean], [y - 0.2, y + 0.2], color=INK, linewidth=2.4, zorder=6)
        grey = by_key.get((task, effort, "claude-sonnet-5-5"))
        if grey:
            ax.scatter(grey, [row_index] * len(grey), s=45, color="none", edgecolors=MUTED, linewidths=1.2, zorder=3)
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels([f"{task} ({effort})" for task, effort in order])
    ax.set_ylim(len(order) - 0.5, -0.6)
    ax.set_xscale("log")
    ax.set_xticks([0.003, 0.01, 0.03, 0.1, 0.3, 1])
    ax.set_xticklabels(["$0.003", "$0.01", "$0.03", "$0.10", "$0.30", "$1"])
    ax.set_xlim(0.0017, 3.2)
    ax.minorticks_off()
    ax.set_xlabel("Cost of one run (USD, log scale)")
    ax.grid(axis="x", color="#e6e6e3", linewidth=0.6, zorder=0)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.tick_params(axis="y", length=0)
    handles = [plt.Line2D([], [], marker="o", linestyle="", color=FABLE, markersize=8),
               plt.Line2D([], [], marker="o", linestyle="", color=OPUS, markersize=8),
               plt.Line2D([], [], color=INK, linewidth=2.4),
               plt.Line2D([], [], marker="o", linestyle="", markerfacecolor="none", markeredgecolor=MUTED,
                          markeredgewidth=1.2, markersize=7)]
    ax.legend(handles, ["Fable 5.2, one run", "Opus 5.5, one run", "mean of the runs", "Sonnet 5.5 (one job only)"],
              loc="upper center", bbox_to_anchor=(0.4, -0.16), ncol=2, frameon=False, fontsize=10)
    fig.tight_layout()
    save(fig, "fig4-every-run")


def bootstrap_ratio(pairs, fable_key, opus_key):
    """Ratio of totals, with a 95 percent range from resampling the jobs (not the runs)."""
    fable = [float(p[fable_key]) for p in pairs]
    opus = [float(p[opus_key]) for p in pairs]
    rng = random.Random(BOOTSTRAP_SEED)
    count = len(pairs)
    ratios = []
    for _ in range(BOOTSTRAP_RESAMPLES):
        picks = [rng.randrange(count) for _ in range(count)]
        ratios.append(sum(fable[i] for i in picks) / sum(opus[i] for i in picks))
    ratios.sort()
    low = ratios[int(0.025 * BOOTSTRAP_RESAMPLES)]
    high = ratios[int(0.975 * BOOTSTRAP_RESAMPLES) - 1]
    return sum(fable) / sum(opus), low, high


def draw_totals(study1, study2):
    """Figure 5: total cost and time ratio, Fable over Opus, with a bootstrap range, both studies."""
    rows = []
    for measure, fable_key, opus_key in (("Cost", "fable_cost_usd", "opus_cost_usd"),
                                         ("Time", "fable_wall_s", "opus_wall_s")):
        for label, pairs in (("Study 2, same night (8 pairings)", study2), ("Study 1, earlier Opus (24 jobs)", study1)):
            total, low, high = bootstrap_ratio(pairs, fable_key, opus_key)
            rows.append((measure, label, total, low, high))
            log(f"totals {measure} {label}: ratio {total:.3f}, 95% range {low:.3f} to {high:.3f}")
    big_style(pick_font())
    fig, ax = plt.subplots(figsize=(6.6, 3.9))
    positions = [0, 1, 2.6, 3.6]
    for position, (measure, label, total, low, high) in zip(positions, rows):
        study2_row = label.startswith("Study 2")
        colour = STUDY2 if study2_row else STUDY1
        ax.plot([low, high], [position, position], color=colour, linewidth=3, solid_capstyle="round", zorder=3)
        ax.scatter([total], [position], s=110, zorder=4, color=colour if study2_row else "white",
                   edgecolors=colour, linewidths=2)
        ax.text(high * 1.1, position, f"{total:.2f}x", va="center", fontsize=12, color=INK, fontweight="bold")
    ax.axvline(1.0, color=MUTED, linewidth=0.8, zorder=1)
    ax.axvline(PRICE_RATIO, color=MUTED, linewidth=0.8, linestyle=(0, (3, 3)), zorder=1)
    ax.text(PRICE_RATIO * 1.03, -0.62, "price ratio", color=MUTED, fontsize=10, va="bottom")
    ax.text(1.03, -0.62, "equal", color=MUTED, fontsize=10, va="bottom")
    ax.set_yticks(positions)
    ax.set_yticklabels([f"{r[0]}: {r[1]}" for r in rows])
    ax.set_ylim(4.1, -0.9)
    ax.set_xscale("log")
    ax.set_xticks([0.5, 1, 2, 4, 8])
    ax.set_xticklabels(["0.5", "1", "2", "4", "8"])
    ax.minorticks_off()
    ax.set_xlim(0.7, 9)
    ax.set_xlabel("Total for Fable 5.2 divided by total for Opus 5.5")
    ax.grid(axis="x", color="#e6e6e3", linewidth=0.6, zorder=0)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.tick_params(axis="y", length=0)
    fig.tight_layout()
    save(fig, "fig5-totals")


def main():
    study1, study2 = read("pairs_study1.csv"), read("pairs_study2.csv")
    if not study1 or not study2:
        log("a pairs file is empty; run scripts/extract.py first")
        return 1
    order = sorted(study1, key=lambda row: float(row["cost_ratio"]))
    tasks = [row["task"] for row in order]
    rank = {task: index for index, task in enumerate(tasks)}

    plt.rcParams.update({"font.family": pick_font(), "font.size": 8.5, "axes.edgecolor": MUTED,
                         "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK,
                         "svg.fonttype": "none"})
    fig, axes = plt.subplots(1, 2, figsize=(6.6, 4.15), sharey=True)
    panels = (("cost_ratio", "Cost, Fable 5.2 / Opus 5.5", "(a) Cost per job"),
              ("time_ratio", "Wall time, Fable 5.2 / Opus 5.5", "(b) Time per job"))
    for ax, (key, xlabel, title) in zip(axes, panels):
        ax.axvline(1.0, color=MUTED, linewidth=0.8, zorder=1)
        if key == "cost_ratio":
            ax.axvline(PRICE_RATIO, color=MUTED, linewidth=0.8, linestyle=(0, (3, 3)), zorder=1)
            ax.text(PRICE_RATIO * 1.04, len(tasks) - 0.4, "price ratio", color=MUTED, fontsize=7.5, va="bottom")
        ax.text(1.04, len(tasks) - 0.4, "equal", color=MUTED, fontsize=7.5, va="bottom")
        ax.scatter([float(r[key]) for r in order], [rank[r["task"]] for r in order], s=26,
                   facecolors="white", edgecolors=STUDY1, linewidths=1.3, zorder=3,
                   label="10 Nov: Opus from earlier runs")
        same_day = [r for r in study2 if r["task"] in rank]
        ax.scatter([float(r[key]) for r in same_day], [rank[r["task"]] for r in same_day], s=26,
                   color=STUDY2, edgecolors="white", linewidths=0.8, zorder=4,
                   label="11 Nov: same night, same effort")
        ax.set_xscale("log")
        ax.set_xticks([0.25, 0.5, 1, 2, 4, 8])
        ax.set_xticklabels(["0.25", "0.5", "1", "2", "4", "8"])
        ax.minorticks_off()
        ax.set_xlim(0.22, 11)
        ax.set_xlabel(xlabel)
        ax.set_title(title, loc="left", fontsize=9, color=INK)
        ax.grid(axis="x", color="#e6e6e3", linewidth=0.6, zorder=0)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        ax.tick_params(axis="y", length=0)
    axes[0].set_yticks(range(len(tasks)))
    axes[0].set_yticklabels(tasks)
    axes[0].set_ylim(-0.7, len(tasks) + 0.4)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=2, frameon=False, fontsize=8,
               bbox_to_anchor=(0.55, -0.005))
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for suffix in ("svg", "png"):
        path = OUT_DIR / f"fig3-ratios.{suffix}"
        fig.savefig(path, dpi=200, bbox_inches="tight")
        log(f"wrote {path.relative_to(PAPER_DIR)}")
    plt.close(fig)
    draw_method(pick_font())
    draw_same_or_different(study1, study2)
    draw_every_run(read("runs.csv"), study2)
    draw_totals(study1, study2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
