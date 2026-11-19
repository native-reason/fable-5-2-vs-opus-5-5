"""Turn the model bench's raw result files into the CSV tables the paper reads.

Usage: python scripts/extract.py [--bench <path to model-bench folder>]

Only per-run numbers are written (task, model, effort, score, time, cost, tokens). Prompts and model
replies are never copied, so nothing from the jobs themselves leaves the bench folder.

Study 1 (2026-11-10): Fable 5.2 at high effort on 24 jobs, set against the Opus 5.5 and Sonnet 5.5
runs that the bench already held. The baseline run for each job is read from the "Where each
baseline came from" list in that run's summary.md, so these tables match the summary exactly even
though newer runs now exist.

Study 2 (2026-11-11): the model watch's run, where Fable 5.2 and the current settings ran the same
jobs on the same day, on the same machine, at matched effort.
"""
import argparse
import csv
import datetime
import json
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path

PAPER_DIR = Path(__file__).resolve().parent.parent
DEFAULT_BENCH = PAPER_DIR.parents[2] / "Software-Ideas" / "model-bench"
STUDY1_RUN = "2026-11-10-fable"
STUDY2_RUN = "model-watch-claude-fable-5-2-20261111"
# The labelling job was run again on 19 November with the same settings after one invented request
# was reworded, so its rows come from that run and its 11 November rows are left out.
RELABEL_RUN = "router-label-made-up-name-20261119"
RELABEL_TASK = "router-label"
FABLE = "claude-fable-5-2"
OPUS = "claude-opus-5-5"
SONNET = "claude-sonnet-5-5"
NAMES = {FABLE: "Fable 5.2", OPUS: "Opus 5.5", SONNET: "Sonnet 5.5", "claude-haiku-5-5": "Haiku 5.5"}
# Rows the machine broke, not the model (full disk, a port already in use). Same list as summarise.py.
# They are published with the reason in the "excluded" column and left out of every average.
STUDY1_BROKEN = {("results.jsonl", "digest-day", 1): "machine: disk full",
                 ("rerun/results.jsonl", "localhost", 2): "machine: port already in use"}
STUDY1_PARTS = ("results.jsonl", "rerun/results.jsonl", "briefing-day/results.jsonl", "rerun2/results.jsonl")
# The first briefing-day attempt ran from a folder where Claude Code refuses file writes: the set-up's fault.
STUDY1_BLOCKED_PART = "briefing-day-blocked/results.jsonl"
STUDY1_BLOCKED_REASON = "set-up: folder refused file writes"
RUN_FIELDS = ["study", "source_run", "task", "model", "effort", "rep", "score", "wall_s", "cost_usd",
              "output_tokens", "input_tokens", "cache_read_tokens", "cache_write_tokens", "num_turns",
              "started", "excluded"]


def log(message):
    stamp = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    print(f"{stamp} {message}", flush=True)


def load_rows(results_file):
    rows = []
    for number, line in enumerate(results_file.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            log(f"skipped a bad line in {results_file} at line {number}: {exc}")
    return rows


def slim(row, study, source_run, excluded=""):
    """Keep only the numbers. Never the prompt, the reply or the grader's notes.

    Input and cache token counts exist only for runs made after the bench began recording them
    (19 November 2026); older rows leave those columns blank.
    """
    return {"study": study, "source_run": source_run, "task": row["task"], "model": row["model"],
            "effort": row.get("effort") or "", "rep": row["rep"], "score": row.get("score"),
            "wall_s": row.get("wall_s"), "cost_usd": row.get("cost_usd"),
            "output_tokens": row.get("output_tokens"), "input_tokens": row.get("input_tokens"),
            "cache_read_tokens": row.get("cache_read_tokens"), "cache_write_tokens": row.get("cache_write_tokens"),
            "num_turns": row.get("num_turns"), "started": row.get("started") or "", "excluded": excluded}


def study1_baseline_sources(summary_file):
    """Parse '- task / Opus 5.5: `run`, effort high, ...' lines into {(task, model): (run, effort)}."""
    pattern = re.compile(r"^- (\S+) / (Sonnet 5\.5|Opus 5\.5): `([^`]+)`, effort (\w+),")
    model_ids = {"Sonnet 5.5": SONNET, "Opus 5.5": OPUS}
    sources = {}
    for line in summary_file.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line)
        if match:
            task, name, run, effort = match.groups()
            sources[(task, model_ids[name])] = (run, effort)
    if not sources:
        raise ValueError(f"no baseline lines found in {summary_file}; has its format changed?")
    return sources


def study1_rows(bench):
    run_dir = bench / "results" / STUDY1_RUN
    rows = []
    for part in STUDY1_PARTS:
        for row in load_rows(run_dir / part):
            if row["model"] == FABLE:
                reason = STUDY1_BROKEN.get((part, row["task"], row["rep"]), "")
                rows.append(slim(row, "study1", f"{STUDY1_RUN}/{part}", reason))
    for row in load_rows(run_dir / STUDY1_BLOCKED_PART):
        if row["model"] == FABLE:
            rows.append(slim(row, "study1", f"{STUDY1_RUN}/{STUDY1_BLOCKED_PART}", STUDY1_BLOCKED_REASON))
    for (task, model), (run, effort) in sorted(study1_baseline_sources(run_dir / "summary.md").items()):
        results_file = bench / "results" / run / "results.jsonl"
        if not results_file.exists():
            raise FileNotFoundError(f"baseline file missing for {task} / {model}: {results_file}")
        group = [r for r in load_rows(results_file)
                 if r["task"] == task and r["model"] == model and (r.get("effort") or "") == effort]
        if not group:
            raise ValueError(f"no rows for {task} / {model} / {effort} in {results_file}")
        rows += [slim(r, "study1", run) for r in group]
    return rows


def study2_rows(bench):
    run_dir = bench / "results" / STUDY2_RUN
    rows = [slim(r, "study2", STUDY2_RUN) for r in load_rows(run_dir / "results.jsonl")
            if r["task"] != RELABEL_TASK]
    relabel_file = bench / "results" / RELABEL_RUN / "results.jsonl"
    if not relabel_file.exists():
        raise FileNotFoundError(f"re-run of {RELABEL_TASK} missing: {relabel_file}")
    relabel = [slim(r, "study2", RELABEL_RUN) for r in load_rows(relabel_file) if r["task"] == RELABEL_TASK]
    if len(relabel) != 8:
        raise ValueError(f"expected 8 {RELABEL_TASK} rows in {relabel_file}, found {len(relabel)}")
    return rows + relabel


def mean(values):
    values = [v for v in values if v is not None]
    return statistics.fmean(values) if values else None


def by_task(rows):
    """One line per (study, task, model, effort): mean and range of score, time and cost, n.

    The min and max columns show the spread of the repeats. They are plain ranges, not a test: with two
    or three repeats a significance test would say nothing.
    """
    groups = defaultdict(list)
    for row in rows:
        if row["excluded"]:
            continue
        groups[(row["study"], row["task"], row["model"], row["effort"])].append(row)
    table = []
    for (study, task, model, effort), group in sorted(groups.items()):
        table.append({"study": study, "task": task, "model": NAMES.get(model, model), "effort": effort,
                      "n": len(group), "mean_score": round(mean(r["score"] for r in group), 4),
                      "worst_score": min(r["score"] for r in group),
                      "best_score": max(r["score"] for r in group),
                      "mean_wall_s": round(mean(r["wall_s"] for r in group), 1),
                      "min_wall_s": round(min(r["wall_s"] for r in group), 1),
                      "max_wall_s": round(max(r["wall_s"] for r in group), 1),
                      "mean_cost_usd": round(mean(r["cost_usd"] for r in group), 4),
                      "min_cost_usd": round(min(r["cost_usd"] for r in group), 4),
                      "max_cost_usd": round(max(r["cost_usd"] for r in group), 4),
                      "mean_output_tokens": round(mean(r["output_tokens"] for r in group) or 0)})
    return table


def paired(table, study, matched_effort):
    """Fable against Opus on each task both ran in a study; same effort only when matched_effort."""
    index = defaultdict(list)
    for line in table:
        if line["study"] == study:
            index[(line["task"], line["model"])].append(line)
    pairs = []
    for (task, model), fable_lines in sorted(index.items()):
        if model != "Fable 5.2":
            continue
        for fable in fable_lines:
            for opus in index.get((task, "Opus 5.5"), []):
                if matched_effort and opus["effort"] != fable["effort"]:
                    continue
                pairs.append({"study": study, "task": task, "fable_effort": fable["effort"],
                              "opus_effort": opus["effort"], "fable_n": fable["n"], "opus_n": opus["n"],
                              "fable_score": fable["mean_score"], "opus_score": opus["mean_score"],
                              "fable_wall_s": fable["mean_wall_s"], "opus_wall_s": opus["mean_wall_s"],
                              "fable_cost_usd": fable["mean_cost_usd"], "opus_cost_usd": opus["mean_cost_usd"],
                              "cost_ratio": round(fable["mean_cost_usd"] / opus["mean_cost_usd"], 3),
                              "time_ratio": round(fable["mean_wall_s"] / opus["mean_wall_s"], 3),
                              "fable_output_tokens": fable["mean_output_tokens"],
                              "opus_output_tokens": opus["mean_output_tokens"]})
    return pairs


def write_csv(path, rows, fields=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = fields or list(rows[0].keys())
    with path.open("w", newline="", encoding="ascii") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    log(f"wrote {path.relative_to(PAPER_DIR)} ({len(rows)} rows)")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--bench", type=Path, default=DEFAULT_BENCH)
    args = parser.parse_args()
    if not (args.bench / "results").is_dir():
        log(f"no results folder under {args.bench}; pass --bench <model-bench folder>")
        return 1
    runs = study1_rows(args.bench) + study2_rows(args.bench)
    write_csv(PAPER_DIR / "data" / "runs.csv", runs, RUN_FIELDS)
    table = by_task(runs)
    write_csv(PAPER_DIR / "data" / "by_task.csv", table)
    pairs1 = paired(table, "study1", matched_effort=False)
    pairs2 = paired(table, "study2", matched_effort=True)
    write_csv(PAPER_DIR / "data" / "pairs_study1.csv", pairs1)
    write_csv(PAPER_DIR / "data" / "pairs_study2.csv", pairs2)

    # Totals, printed so they can be checked against the bench's own summary.md by eye.
    for name, pairs in (("study1", pairs1), ("study2", pairs2)):
        fable_cost = sum(p["fable_cost_usd"] for p in pairs)
        opus_cost = sum(p["opus_cost_usd"] for p in pairs)
        fable_wall = sum(p["fable_wall_s"] for p in pairs)
        opus_wall = sum(p["opus_wall_s"] for p in pairs)
        log(f"{name}: {len(pairs)} pairs; cost Fable {fable_cost:.2f} Opus {opus_cost:.2f} "
            f"(x{fable_cost / opus_cost:.2f}); time Fable {fable_wall:.0f}s Opus {opus_wall:.0f}s "
            f"(x{fable_wall / opus_wall:.2f}); mean score Fable {mean(p['fable_score'] for p in pairs):.3f} "
            f"Opus {mean(p['opus_score'] for p in pairs):.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
