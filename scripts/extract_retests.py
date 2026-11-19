"""Turn the 19 November re-tests of the open-ended work into one CSV of per-run numbers.

Usage: python scripts/extract_retests.py [--trial <path to the re-test folder>]

Three trials, each run more than once per model with the marking rules fixed before any run
(marking-rules.md in the trial folder): R research (two briefs), A audit, S second opinion. The
checkers were Sonnet 5.5, blind to which model wrote each report. This script reads the run records,
the blind verdicts and, last, the keys that map blind letters back to runs.

Only numbers are written: time, cost, tokens, tool counts and verdict counts. Report text, claims and
checker notes are never copied. A run whose time overlaps a pause by the machine's freeze watchdog
keeps its cost and verdicts but its wall time is flagged (data/pause_windows.csv, made by extract.py).
"""
import argparse
import csv
import datetime
import json
import re
import sys
from pathlib import Path

PAPER_DIR = Path(__file__).resolve().parent.parent
DEFAULT_TRIAL = (PAPER_DIR.parents[2] / "Software-Ideas" / "model-bench" / "trials"
                 / "2026-11-19-paper1-retests")
NAMES = {"claude-fable-5-2": "Fable 5.2", "claude-opus-5-5": "Opus 5.5"}
BRIEFS = {"R1": "research: packaging", "R2": "research: accounting software", "A": "audit", "S": "second opinion"}
R_VERDICTS = ["right", "wrong", "unsupported", "out of date", "dead link"]
A_VERDICTS = ["real", "real, wrong cause", "not real", "could not check"]
S_VERDICTS = ["true", "partly true", "false", "not checkable from the files"]
CHECKLIST = ["C1", "C2", "C3", "C4", "C5"]
REPORT_SECTIONS = 8
FIELDS = ["trial", "brief", "run", "model", "effort", "started", "wall_s", "timing_excluded", "cost_usd",
          "output_tokens", "web_searches", "page_reads", "file_reads", "report_words", "sections_present",
          "distinct_sources", "claims_found", "checked",
          "right", "wrong", "unsupported", "out_of_date", "dead_link", "hard_error_rate", "problem_rate",
          "real", "real_wrong_cause", "not_real", "could_not_check", "share_real", "client_path_calls",
          "true", "partly_true", "false", "not_checkable", "share_true", "checklist_caught",
          "C1", "C2", "C3", "C4", "C5", "checker_cost_usd"]
URL = re.compile(r"https?://[^\s)\]>\"'`]+")


def log(message):
    stamp = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    print(f"{stamp} {message}", flush=True)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def pause_windows():
    path = PAPER_DIR / "data" / "pause_windows.csv"
    if not path.exists():
        raise FileNotFoundError(f"{path} missing: run scripts/extract.py --watchdog-log <log> first")
    with path.open(encoding="ascii") as handle:
        return [(datetime.datetime.fromisoformat(w["paused"]), datetime.datetime.fromisoformat(w["ended"]))
                for w in csv.DictReader(handle)]


def overlaps(started, ended, windows):
    start, end = datetime.datetime.fromisoformat(started), datetime.datetime.fromisoformat(ended)
    return any(start <= stop and pause <= end for pause, stop in windows)


def points_at_clients(name, tool_input):
    """True when a file tool call aims at the Clients folder. A glob that starts with "!" excludes
    folders, so a search that leaves Clients out does not count."""
    targets = [tool_input.get("file_path"), tool_input.get("path")]
    if name == "Glob":
        targets.append(tool_input.get("pattern"))
    glob = tool_input.get("glob") or ""
    if not glob.startswith("!"):
        targets.append(glob)
    return any("clients" in str(t).lower() for t in targets if t)


def client_path_calls(events_file):
    """Every tool call in the run's event log that aims at the Clients folder, allowed or denied."""
    count = 0
    for line in events_file.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        message = event.get("message") if isinstance(event, dict) else None
        if not isinstance(message, dict):
            continue
        for block in message.get("content") or []:
            if (isinstance(block, dict) and block.get("type") == "tool_use"
                    and points_at_clients(block.get("name"), block.get("input") or {})):
                count += 1
    return count


def report_numbers(output_file):
    text = output_file.read_text(encoding="utf-8")
    sections = sum(1 for n in range(1, REPORT_SECTIONS + 1) if re.search(rf"^##\s+{n}\.", text, re.M))
    return {"report_words": len(text.split()), "sections_present": sections,
            "distinct_sources": len({u.rstrip(".,;:") for u in URL.findall(text)})}


# The checker sometimes shortened a verdict; "not checkable" is the same verdict. Once (second opinion)
# it wrote "mostly true", which is not on the fixed list: it is counted as the stricter "partly true".
ALIASES = {"not checkable": "not checkable from the files", "mostly true": "partly true"}


def counts(verdicts, names, key="verdict"):
    tally = {name: 0 for name in names}
    for item in verdicts:
        verdict = (item.get(key) or "").strip().lower()
        verdict = ALIASES.get(verdict, verdict)
        if verdict not in tally:
            raise ValueError(f"unexpected verdict {verdict!r}")
        tally[verdict] += 1
    return tally


def rate(numerator, denominator):
    return round(numerator / denominator, 3) if denominator else None


def row_for(run_id, letter, kind, trial, windows):
    run_dir = trial / "runs" / run_id
    meta = read_json(run_dir / "meta.json")
    models = list(meta["assistant_messages_by_model"])
    if models != [meta["asked_model"]]:
        raise ValueError(f"{run_id} asked for {meta['asked_model']} but messages came from {models}")
    tools = meta.get("tool_calls", {})
    row = {field: "" for field in FIELDS}
    row.update({"trial": kind, "brief": run_id.split("-")[0], "run": run_id, "model": NAMES[meta["asked_model"]],
                "effort": meta["effort"], "started": meta["started"], "wall_s": meta["wall_s"],
                "timing_excluded": "overlaps a watchdog pause" if overlaps(meta["started"], meta["ended"], windows) else "",
                "cost_usd": round(meta["cost_usd"], 4), "output_tokens": meta["output_tokens"],
                "web_searches": tools.get("WebSearch", 0), "page_reads": tools.get("WebFetch", 0),
                "file_reads": tools.get("Read", 0)})
    row.update(report_numbers(run_dir / "output.md"))
    checks = trial / "checks"
    if kind == "R":
        verdict_file = read_json(checks / f"verdicts-R-{letter}.json")
        tally = counts(verdict_file["verdicts"], R_VERDICTS)
        checked = sum(tally.values())
        row.update({"claims_found": len(read_json(checks / f"claims-all-R-{letter}.json") or []), "checked": checked,
                    "right": tally["right"], "wrong": tally["wrong"], "unsupported": tally["unsupported"],
                    "out_of_date": tally["out of date"], "dead_link": tally["dead link"],
                    "hard_error_rate": rate(tally["wrong"] + tally["out of date"], checked),
                    "problem_rate": rate(checked - tally["right"], checked),
                    "checker_cost_usd": verdict_file.get("cost_usd")})
    elif kind == "A":
        verdict_file = read_json(checks / f"verdicts-A-{letter}.json")
        tally = counts(verdict_file["verdicts"], A_VERDICTS)
        testable = sum(tally.values()) - tally["could not check"]
        row.update({"checked": sum(tally.values()), "real": tally["real"], "real_wrong_cause": tally["real, wrong cause"],
                    "not_real": tally["not real"], "could_not_check": tally["could not check"],
                    "share_real": rate(tally["real"], testable),
                    "client_path_calls": client_path_calls(run_dir / "events.jsonl"),
                    "checker_cost_usd": verdict_file.get("cost_usd")})
    else:
        verdict_file = read_json(checks / f"verdicts-S-{letter}.json")
        result = verdict_file["result"]
        tally = counts(result["claims"], S_VERDICTS)
        checkable = sum(tally.values()) - tally["not checkable from the files"]
        caught = {c: bool(result["checklist"].get(c)) for c in CHECKLIST}
        row.update({"checked": sum(tally.values()), "true": tally["true"], "partly_true": tally["partly true"],
                    "false": tally["false"], "not_checkable": tally["not checkable from the files"],
                    "share_true": rate(tally["true"], checkable), "checklist_caught": sum(caught.values()),
                    "checker_cost_usd": verdict_file.get("cost_usd")})
        row.update({c: "yes" if caught[c] else "no" for c in CHECKLIST})
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--trial", type=Path, default=DEFAULT_TRIAL)
    args = parser.parse_args()
    if not (args.trial / "checks").is_dir():
        log(f"no checks folder under {args.trial}; pass --trial <re-test folder>")
        return 1
    windows = pause_windows()
    rows = []
    for kind in ("R", "A", "S"):
        key = read_json(args.trial / "checks" / f"key-{kind}.json")
        for letter, run_id in sorted(key.items(), key=lambda item: item[1]):
            rows.append(row_for(run_id, letter, kind, args.trial, windows))
    out = PAPER_DIR / "data" / "retests.csv"
    with out.open("w", newline="", encoding="ascii") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    log(f"wrote {out.relative_to(PAPER_DIR)} ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
