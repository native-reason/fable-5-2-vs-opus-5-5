"""Turn the model bench's raw result files into the CSV tables the paper reads.

Usage: python scripts/extract.py [--bench <path to model-bench folder>] [--watchdog-log <path>]

Only per-run numbers are written (task, model, effort, score, time, cost, tokens). Prompts and model
replies are never copied, so nothing from the jobs themselves leaves the bench folder.

The matched pass (2026-11-19) is the main bench result: all 25 jobs, both models at high effort,
three runs each, on one machine on one day. The machine's freeze watchdog paused batch jobs when the
processor was flat out; a run that overlaps a pause has its wall time left out of the timing (its
score and cost still count). The pause windows are read from the watchdog log when --watchdog-log is
given and saved to data/pause_windows.csv, so the published data can be rebuilt without the log.

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
import random
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
BOOTSTRAP_RESAMPLES = 10000
BOOTSTRAP_SEED = 20261119
MATCHED_RUN = "paper1-matched-20261119"
MATCHED_CONFIGS = {"fable52-high": FABLE, "opus55-high": OPUS}
MATCHED_TASK_COUNT = 25
MATCHED_REPS = 3
PAUSE_FIELDS = ["paused", "ended", "how_it_ended"]
WATCHDOG_STAMP = re.compile(r"^\[([^\]]+)\] freeze_watchdog: (.*)$")
RUN_FIELDS = ["study", "source_run", "task", "model", "effort", "rep", "score", "wall_s", "cost_usd",
              "output_tokens", "input_tokens", "cache_read_tokens", "cache_write_tokens", "num_turns",
              "started", "excluded", "timing_excluded"]


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
            "num_turns": row.get("num_turns"), "started": row.get("started") or "", "excluded": excluded,
            "timing_excluded": ""}


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


def read_pause_windows(watchdog_log):
    """Each 'paused N batch jobs' line opens a window; the next 'resumed' or 'killing' line closes it.

    A killed run leaves no result row (the bench simply runs it again), so only paused-then-resumed
    runs can carry a stretched wall time. Both kinds of window are kept to be safe.
    """
    windows, opened = [], None
    for line in watchdog_log.read_text(encoding="utf-8", errors="replace").splitlines():
        match = WATCHDOG_STAMP.match(line)
        if not match:
            continue
        stamp, message = match.groups()
        if "paused" in message and "batch jobs" in message and opened is None:
            opened = stamp
        elif opened is not None and ("resumed" in message or "killing" in message):
            windows.append({"paused": opened, "ended": stamp,
                            "how_it_ended": "resumed" if "resumed" in message else "killed"})
            opened = None
    if opened is not None:
        windows.append({"paused": opened, "ended": opened, "how_it_ended": "log ends while paused"})
    return windows


def parse_time(stamp):
    return datetime.datetime.fromisoformat(stamp)


def overlaps_a_pause(row, windows):
    start = parse_time(row["started"])
    end = start + datetime.timedelta(seconds=float(row["wall_s"]))
    for window in windows:
        if start <= parse_time(window["ended"]) and parse_time(window["paused"]) <= end:
            return True
    return False


def matched_rows(bench, windows):
    """The last good row for each job, model and repeat; earlier attempts the watchdog stopped are not rows."""
    results_file = bench / "results" / MATCHED_RUN / "results.jsonl"
    latest = {}
    for row in load_rows(results_file):
        if row.get("is_error") or row.get("score") is None or row["config"] not in MATCHED_CONFIGS:
            continue
        if row["model"] != MATCHED_CONFIGS[row["config"]]:
            raise ValueError(f"{row['task']} {row['config']} rep {row['rep']} ran on {row['model']}")
        latest[(row["task"], row["config"], row["rep"])] = row
    expected = MATCHED_TASK_COUNT * len(MATCHED_CONFIGS) * MATCHED_REPS
    if len(latest) != expected:
        log(f"warning: matched pass has {len(latest)} of {expected} good runs; the tables will be partial")
    rows = []
    for key in sorted(latest):
        row = latest[key]
        slimmed = slim(row, "matched", MATCHED_RUN)
        if overlaps_a_pause(row, windows):
            slimmed["timing_excluded"] = "overlaps a watchdog pause"
        rows.append(slimmed)
    return rows


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
        # Wall time only from runs the watchdog did not pause; score and cost from every run.
        timed = [r for r in group if not r["timing_excluded"]]
        walls = [r["wall_s"] for r in timed]
        table.append({"study": study, "task": task, "model": NAMES.get(model, model), "effort": effort,
                      "n": len(group), "n_timed": len(timed),
                      "mean_score": round(mean(r["score"] for r in group), 4),
                      "worst_score": min(r["score"] for r in group),
                      "best_score": max(r["score"] for r in group),
                      "mean_wall_s": round(mean(walls), 1) if walls else None,
                      "min_wall_s": round(min(walls), 1) if walls else None,
                      "max_wall_s": round(max(walls), 1) if walls else None,
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
                              "fable_n_timed": fable["n_timed"], "opus_n_timed": opus["n_timed"],
                              "cost_ratio": round(fable["mean_cost_usd"] / opus["mean_cost_usd"], 3),
                              "time_ratio": (round(fable["mean_wall_s"] / opus["mean_wall_s"], 3)
                                             if fable["mean_wall_s"] and opus["mean_wall_s"] else None),
                              "fable_output_tokens": fable["mean_output_tokens"],
                              "opus_output_tokens": opus["mean_output_tokens"]})
    return pairs


def bootstrap_ratio(pairs, fable_key, opus_key):
    """Ratio of totals, Fable over Opus, with a 95 percent range from resampling the jobs (not the runs)."""
    pairs = [p for p in pairs if p[fable_key] is not None and p[opus_key] is not None]
    fable = [float(p[fable_key]) for p in pairs]
    opus = [float(p[opus_key]) for p in pairs]
    rng = random.Random(BOOTSTRAP_SEED)
    ratios = []
    for _ in range(BOOTSTRAP_RESAMPLES):
        picks = [rng.randrange(len(pairs)) for _ in range(len(pairs))]
        ratios.append(sum(fable[i] for i in picks) / sum(opus[i] for i in picks))
    ratios.sort()
    return {"jobs": len(pairs), "fable_total": round(sum(fable), 4), "opus_total": round(sum(opus), 4),
            "ratio": round(sum(fable) / sum(opus), 3),
            "low_95": round(ratios[int(0.025 * BOOTSTRAP_RESAMPLES)], 3),
            "high_95": round(ratios[int(0.975 * BOOTSTRAP_RESAMPLES) - 1], 3)}


def totals(named_pairs):
    rows = []
    for study, pairs in named_pairs:
        for measure, fable_key, opus_key in (("cost", "fable_cost_usd", "opus_cost_usd"),
                                             ("time", "fable_wall_s", "opus_wall_s")):
            rows.append({"study": study, "measure": measure, **bootstrap_ratio(pairs, fable_key, opus_key)})
    return rows


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
    parser.add_argument("--watchdog-log", type=Path, default=None,
                        help="the freeze watchdog's log; rewrites data/pause_windows.csv from it")
    args = parser.parse_args()
    if not (args.bench / "results").is_dir():
        log(f"no results folder under {args.bench}; pass --bench <model-bench folder>")
        return 1
    pause_file = PAPER_DIR / "data" / "pause_windows.csv"
    if args.watchdog_log:
        write_csv(pause_file, read_pause_windows(args.watchdog_log), PAUSE_FIELDS)
    if not pause_file.exists():
        log(f"no {pause_file.name}; pass --watchdog-log once to make it")
        return 1
    with pause_file.open(encoding="ascii") as handle:
        windows = list(csv.DictReader(handle))
    runs = matched_rows(args.bench, windows) + study1_rows(args.bench) + study2_rows(args.bench)
    write_csv(PAPER_DIR / "data" / "runs.csv", runs, RUN_FIELDS)
    table = by_task(runs)
    write_csv(PAPER_DIR / "data" / "by_task.csv", table)
    pairs_matched = paired(table, "matched", matched_effort=True)
    pairs1 = paired(table, "study1", matched_effort=False)
    pairs2 = paired(table, "study2", matched_effort=True)
    write_csv(PAPER_DIR / "data" / "pairs_matched.csv", pairs_matched)
    write_csv(PAPER_DIR / "data" / "pairs_study1.csv", pairs1)
    write_csv(PAPER_DIR / "data" / "pairs_study2.csv", pairs2)
    write_csv(PAPER_DIR / "data" / "totals.csv",
              totals((("matched", pairs_matched), ("study1", pairs1), ("study2", pairs2))))
    left_out =sum(1 for r in runs if r["study"] == "matched" and r["timing_excluded"])
    log(f"matched pass: {left_out} runs overlap a watchdog pause and are left out of the timing")

    # Totals, printed so they can be checked against the bench's own summary.md by eye. Time totals
    # use only the jobs where both models have at least one timed run.
    for name, pairs in (("matched", pairs_matched), ("study1", pairs1), ("study2", pairs2)):
        fable_cost = sum(p["fable_cost_usd"] for p in pairs)
        opus_cost = sum(p["opus_cost_usd"] for p in pairs)
        timed = [p for p in pairs if p["time_ratio"] is not None]
        fable_wall = sum(p["fable_wall_s"] for p in timed)
        opus_wall = sum(p["opus_wall_s"] for p in timed)
        log(f"{name}: {len(pairs)} pairs; cost Fable {fable_cost:.2f} Opus {opus_cost:.2f} "
            f"(x{fable_cost / opus_cost:.2f}); time over {len(timed)} jobs Fable {fable_wall:.0f}s "
            f"Opus {opus_wall:.0f}s (x{fable_wall / opus_wall:.2f}); mean score Fable "
            f"{mean(p['fable_score'] for p in pairs):.3f} Opus {mean(p['opus_score'] for p in pairs):.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
