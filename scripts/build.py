"""Build paper/paper.html from paper/paper.src.html and the data tables, then print it to paper/paper.pdf.

Usage: python scripts/build.py [--status "Draft 2, 19 November 2026"] [--repo-link URL] [--no-pdf]

The data tables (the matched bench pass, the re-tests, and the earlier comparisons in Appendix B) are
filled from data/*.csv so no number is copied by hand.
The PDF is printed by a headless browser with its own throwaway profile, so it never opens a window
or touches the browser the owner is using.
"""
import argparse
import csv
import datetime
import html
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PAPER_DIR = Path(__file__).resolve().parent.parent
SRC = PAPER_DIR / "paper" / "paper.src.html"
OUT_HTML = PAPER_DIR / "paper" / "paper.html"
OUT_PDF = PAPER_DIR / "paper" / "paper.pdf"
# Headless only. Chrome first: Brave hung in headless print mode on this machine (2026-11-18).
BROWSERS = [Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
            Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
            Path(r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe")]
DEFAULT_STATUS = "Draft 1, 18 November 2026. Not yet published."
DEFAULT_REPO = "[repository link to be added on publication]"


def log(message):
    stamp = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    print(f"{stamp} {message}", flush=True)


def read(name):
    with (PAPER_DIR / "data" / name).open(encoding="ascii") as handle:
        return list(csv.DictReader(handle))


def num(value, places):
    return f"{float(value):,.{places}f}"


def cell(text, numeric=True):
    return f'<td class="n">{text}</td>' if numeric else f"<td>{html.escape(text)}</td>"


def spread(index, task, model, effort, kind, places, study="study2"):
    """'mean<br>(min to max)' for one job, model and effort, from by_task.csv's repeat ranges."""
    line = index[(study, task, model, effort)]
    low, high = line[f"min_{kind}"], line[f"max_{kind}"]
    mean_value = line["mean_wall_s" if kind == "wall_s" else "mean_cost_usd"]
    return (f'{num(mean_value, places)}<br><span class="rng">{num(low, places)} to {num(high, places)}</span>')


def table_study2():
    rows = read("pairs_study2.csv")
    index = {(r["study"], r["task"], r["model"], r["effort"]): r for r in read("by_task.csv")}
    head = ("<thead><tr><th>Job</th><th>Effort</th><th class=\"n\">Score (both)</th>"
            "<th class=\"n\">Time Fable</th><th class=\"n\">Time Opus</th><th class=\"n\">Ratio</th>"
            "<th class=\"n\">Cost Fable</th><th class=\"n\">Cost Opus</th><th class=\"n\">Ratio</th></tr></thead>")
    body = []
    for row in sorted(rows, key=lambda r: (r["fable_effort"], r["task"])):
        if row["fable_score"] != row["opus_score"]:
            score = f"{num(row['fable_score'], 2)} / {num(row['opus_score'], 2)}"
        else:
            score = num(row["fable_score"], 2)
        body.append("<tr>" + cell(row["task"], False) + cell(row["fable_effort"], False) + cell(score)
                    + cell(spread(index, row["task"], "Fable 5.2", row["fable_effort"], "wall_s", 1))
                    + cell(spread(index, row["task"], "Opus 5.5", row["opus_effort"], "wall_s", 1))
                    + cell(num(row["time_ratio"], 2))
                    + cell(spread(index, row["task"], "Fable 5.2", row["fable_effort"], "cost_usd", 3))
                    + cell(spread(index, row["task"], "Opus 5.5", row["opus_effort"], "cost_usd", 3))
                    + cell(num(row["cost_ratio"], 2)) + "</tr>")
    fable_wall = sum(float(r["fable_wall_s"]) for r in rows)
    opus_wall = sum(float(r["opus_wall_s"]) for r in rows)
    fable_cost = sum(float(r["fable_cost_usd"]) for r in rows)
    opus_cost = sum(float(r["opus_cost_usd"]) for r in rows)
    body.append('<tr class="total">' + cell("Total", False) + cell("", False) + cell("")
                + cell(num(fable_wall, 0)) + cell(num(opus_wall, 0)) + cell(num(fable_wall / opus_wall, 2))
                + cell(num(fable_cost, 2)) + cell(num(opus_cost, 2)) + cell(num(fable_cost / opus_cost, 2)) + "</tr>")
    return f'<table class="b3">{head}<tbody>{"".join(body)}</tbody></table>'


def score_text(index, task, model):
    """Mean score, with the worst single run after it when the runs differed."""
    line = index[("matched", task, model, "high")]
    text = num(line["mean_score"], 2)
    if float(line["worst_score"]) < float(line["best_score"]):
        text += f'<br><span class="rng">worst {num(line["worst_score"], 2)}</span>'
    return text


def time_text(index, task, model):
    line = index[("matched", task, model, "high")]
    if not line["mean_wall_s"]:
        return "-"
    text = num(line["mean_wall_s"], 0)
    if line["n_timed"] != line["n"]:
        text += f'<br><span class="rng">{line["n_timed"]} of {line["n"]} timed</span>'
    return text


def table_matched():
    """The main bench table: every job in the matched pass, means over three runs, totals with 95% ranges."""
    rows = read("pairs_matched.csv")
    index = {(r["study"], r["task"], r["model"], r["effort"]): r for r in read("by_task.csv")}
    totals = {r["measure"]: r for r in read("totals.csv") if r["study"] == "matched"}
    head = ("<thead><tr><th>Job</th><th class=\"n\">Score Fable</th><th class=\"n\">Score Opus</th>"
            "<th class=\"n\">Time Fable</th><th class=\"n\">Time Opus</th><th class=\"n\">Ratio</th>"
            "<th class=\"n\">Cost Fable</th><th class=\"n\">Cost Opus</th><th class=\"n\">Ratio</th></tr></thead>")
    body = []
    for row in sorted(rows, key=lambda r: r["task"]):
        task = row["task"]
        body.append("<tr>" + cell(task, False)
                    + cell(score_text(index, task, "Fable 5.2")) + cell(score_text(index, task, "Opus 5.5"))
                    + cell(time_text(index, task, "Fable 5.2")) + cell(time_text(index, task, "Opus 5.5"))
                    + cell(num(row["time_ratio"], 2) if row["time_ratio"] else "-")
                    + cell(num(row["fable_cost_usd"], 3)) + cell(num(row["opus_cost_usd"], 3))
                    + cell(num(row["cost_ratio"], 2)) + "</tr>")
    cost, time = totals["cost"], totals["time"]
    fable_score = sum(float(r["fable_score"]) for r in rows) / len(rows)
    opus_score = sum(float(r["opus_score"]) for r in rows) / len(rows)
    body.append('<tr class="total">' + cell("Total (mean for score)", False)
                + cell(num(fable_score, 3)) + cell(num(opus_score, 3))
                + cell(num(time["fable_total"], 0)) + cell(num(time["opus_total"], 0))
                + cell(f'{num(time["ratio"], 2)}<br><span class="rng">{num(time["low_95"], 2)} to {num(time["high_95"], 2)}</span>')
                + cell(num(cost["fable_total"], 2)) + cell(num(cost["opus_total"], 2))
                + cell(f'{num(cost["ratio"], 2)}<br><span class="rng">{num(cost["low_95"], 2)} to {num(cost["high_95"], 2)}</span>')
                + "</tr>")
    return f'<table class="b3">{head}<tbody>{"".join(body)}</tbody></table>'


def minutes(row):
    text = num(float(row["wall_s"]) / 60, 1)
    return text + "*" if row["timing_excluded"] else text


def table_research():
    """Every research re-test run: verdicts on the sampled claims, cost and time."""
    rows = [r for r in read("retests.csv") if r["trial"] == "R"]
    head = ("<thead><tr><th>Run</th><th>Model</th><th class=\"n\">Checked</th><th class=\"n\">Right</th>"
            "<th class=\"n\">Wrong</th><th class=\"n\">Unsup.</th><th class=\"n\">Out of date</th>"
            "<th class=\"n\">Dead link</th><th class=\"n\">Problem rate</th><th class=\"n\">Cost</th>"
            "<th class=\"n\">Minutes</th><th class=\"n\">Searches / pages</th><th class=\"n\">Words</th></tr></thead>")
    body = []
    for row in sorted(rows, key=lambda r: (r["brief"], r["model"], r["run"])):
        body.append("<tr>" + cell(row["run"], False) + cell(row["model"], False) + cell(row["checked"])
                    + cell(row["right"]) + cell(row["wrong"]) + cell(row["unsupported"]) + cell(row["out_of_date"])
                    + cell(row["dead_link"]) + cell(f'{float(row["problem_rate"]) * 100:.0f}%')
                    + cell(num(row["cost_usd"], 2)) + cell(minutes(row))
                    + cell(f'{row["web_searches"]} / {row["page_reads"]}') + cell(num(row["report_words"], 0)) + "</tr>")
    return f'<table class="b3">{head}<tbody>{"".join(body)}</tbody></table>'


def table_audit_second_opinion():
    """Every audit and second-opinion re-test run: how the checked points held, cost and time."""
    rows = [r for r in read("retests.csv") if r["trial"] in ("A", "S")]
    head = ("<thead><tr><th>Run</th><th>Model</th><th class=\"n\">Checked</th><th class=\"n\">Held</th>"
            "<th class=\"n\">Partly / wrong cause</th><th class=\"n\">Did not hold</th><th class=\"n\">Could not check</th>"
            "<th class=\"n\">Known issues caught (of 5)</th><th class=\"n\">Cost</th><th class=\"n\">Minutes</th>"
            "<th class=\"n\">Files read</th></tr></thead>")
    body = []
    for row in sorted(rows, key=lambda r: (r["trial"], r["model"], r["run"])):
        audit = row["trial"] == "A"
        body.append("<tr>" + cell(row["run"], False) + cell(row["model"], False) + cell(row["checked"])
                    + cell(row["real"] if audit else row["true"])
                    + cell(row["real_wrong_cause"] if audit else row["partly_true"])
                    + cell(row["not_real"] if audit else row["false"])
                    + cell(row["could_not_check"] if audit else row["not_checkable"])
                    + cell("-" if audit else row["checklist_caught"])
                    + cell(num(row["cost_usd"], 2)) + cell(minutes(row)) + cell(row["file_reads"]) + "</tr>")
    return f'<table class="b3">{head}<tbody>{"".join(body)}</tbody></table>'


# What the first week's single runs got wrong, from the trial records (their replies are not published).
FIRST_WEEK_FABLE = ("Two times in a plan it could not have known; a wrong date in a post; a real failure given the "
                    "wrong cause; out of date on one connector; one dead link; a wrong figure repeated from an "
                    "unfinished report")
FIRST_WEEK_OPUS = ("A recommendation built on a feature closed to new users; one date not on its cited page; "
                   "the same wrong figure repeated from an unfinished report")


def table_mistakes():
    """Mistake counts per model, summed over every re-test run, plus the first week's list."""
    rows = read("retests.csv")

    def total(model, trial, *fields):
        return sum(int(r[f] or 0) for r in rows if r["model"] == model and r["trial"] == trial for f in fields)

    def missed(model):
        runs = [r for r in rows if r["model"] == model and r["trial"] == "S"]
        return f"{sum(5 - int(r['checklist_caught']) for r in runs)} of {5 * len(runs)}"

    lines = [("Research claims checked", "R", ("checked",)),
             ("Contradicted by a source, or out of date", "R", ("wrong", "out_of_date")),
             ("Cited page does not say it", "R", ("unsupported",)),
             ("Dead link", "R", ("dead_link",)),
             ("Audit findings checked", "A", ("checked",)),
             ("Not real", "A", ("not_real",)),
             ("Real, but the wrong cause", "A", ("real_wrong_cause",)),
             ("Second-opinion claims checked", "S", ("checked",)),
             ("False", "S", ("false",)),
             ("Partly true", "S", ("partly_true",))]
    head = "<thead><tr><th>Mistake</th><th>Fable 5.2</th><th>Opus 5.5</th></tr></thead>"
    body = []
    for label, trial, fields in lines:
        is_count_of_checked = fields == ("checked",)
        name = f"<b>{html.escape(label)}</b>" if is_count_of_checked else html.escape(label)
        body.append(f"<tr><td>{name}</td>" + cell(str(total("Fable 5.2", trial, *fields)))
                    + cell(str(total("Opus 5.5", trial, *fields))) + "</tr>")
    body.append("<tr><td>Known problems with the draft missed</td>" + cell(missed("Fable 5.2"))
                + cell(missed("Opus 5.5")) + "</tr>")
    body.append("<tr><td>First week, single runs</td>" + cell(FIRST_WEEK_FABLE, False)
                + cell(FIRST_WEEK_OPUS, False) + "</tr>")
    return f'<table class="wide">{head}<tbody>{"".join(body)}</tbody></table>'


def table_study1():
    pairs = {r["task"]: r for r in read("pairs_study1.csv")}
    sonnet = {r["task"]: r for r in read("by_task.csv") if r["study"] == "study1" and r["model"] == "Sonnet 5.5"}
    missing = sorted(set(pairs) - set(sonnet))
    if missing:
        raise ValueError(f"no Sonnet baseline for: {', '.join(missing)}")
    head = ("<thead><tr><th>Job</th><th>Effort</th>"
            "<th class=\"n\">Score F</th><th class=\"n\">Score O</th><th class=\"n\">Score S</th>"
            "<th class=\"n\">Cost F</th><th class=\"n\">Cost O</th><th class=\"n\">Cost S</th>"
            "<th class=\"n\">Time F</th><th class=\"n\">Time O</th><th class=\"n\">Time S</th></tr></thead>")
    body = []
    for task in sorted(pairs):
        pair, son = pairs[task], sonnet[task]
        body.append("<tr>" + cell(task, False) + cell(f"{pair['opus_effort']}/{son['effort']}", False)
                    + cell(num(pair["fable_score"], 2)) + cell(num(pair["opus_score"], 2))
                    + cell(num(son["mean_score"], 2)) + cell(num(pair["fable_cost_usd"], 3))
                    + cell(num(pair["opus_cost_usd"], 3)) + cell(num(son["mean_cost_usd"], 3))
                    + cell(num(pair["fable_wall_s"], 0)) + cell(num(pair["opus_wall_s"], 0))
                    + cell(num(son["mean_wall_s"], 0)) + "</tr>")
    return f'<table class="b1">{head}<tbody>{"".join(body)}</tbody></table>'


def find_browser():
    for path in BROWSERS:
        if path.exists():
            return path
    raise FileNotFoundError("no Brave, Chrome or Edge found to print the PDF; pass --no-pdf to build the HTML only")


def print_pdf(html_file, pdf_file):
    browser = find_browser()
    profile = Path(tempfile.mkdtemp(prefix="paper-pdf-"))
    command = [str(browser), "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
               f"--user-data-dir={profile}", "--no-pdf-header-footer", "--virtual-time-budget=4000",
               f"--print-to-pdf={pdf_file}", html_file.as_uri()]
    if pdf_file.exists():
        pdf_file.unlink()
    # Output goes to a file, not a pipe: the browser's helper processes inherit pipe handles and
    # keep them open after the main process exits, which made a piped run wait forever.
    browser_log = profile / "browser.log"
    try:
        with browser_log.open("w", encoding="utf-8", errors="replace") as handle:
            process = subprocess.Popen(command, stdout=handle, stderr=subprocess.STDOUT)
            try:
                returncode = process.wait(timeout=120)
            except subprocess.TimeoutExpired:
                process.kill()
                returncode = "timeout"
        tail = browser_log.read_text(encoding="utf-8", errors="replace")[-800:]
    finally:
        shutil.rmtree(profile, ignore_errors=True)
    if not pdf_file.exists():
        raise RuntimeError(f"printing failed with {browser.name} (exit {returncode}): {tail}")
    log(f"wrote {pdf_file.relative_to(PAPER_DIR)} ({pdf_file.stat().st_size // 1024} KB) with {browser.name}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--status", default=DEFAULT_STATUS)
    parser.add_argument("--repo-link", default=DEFAULT_REPO)
    parser.add_argument("--no-pdf", action="store_true")
    args = parser.parse_args()

    text = SRC.read_text(encoding="utf-8")
    link = args.repo_link
    repo = f'<a href="{html.escape(link)}">{html.escape(link)}</a>' if link.startswith("http") else html.escape(link)
    fills = {"{{TABLE_MATCHED}}": table_matched(), "{{TABLE_RESEARCH}}": table_research(),
             "{{TABLE_AUDIT_SO}}": table_audit_second_opinion(), "{{TABLE_MISTAKES}}": table_mistakes(),
             "{{TABLE_STUDY2}}": table_study2(), "{{TABLE_STUDY1}}": table_study1(),
             "{{STATUS_LINE}}": html.escape(args.status), "{{REPO_LINK}}": repo}
    for marker, value in fills.items():
        if marker not in text:
            raise ValueError(f"marker {marker} not found in {SRC.name}")
        text = text.replace(marker, value)
    bad = [ch for ch in set(text) if ch in "\u2013\u2014\u2015\u2018\u2019\u201c\u201d"]
    if bad:
        raise ValueError(f"long dashes or curly quotes in the paper: {bad}")
    OUT_HTML.write_text(text, encoding="utf-8")
    log(f"wrote {OUT_HTML.relative_to(PAPER_DIR)}")
    if not args.no_pdf:
        print_pdf(OUT_HTML, OUT_PDF)
    return 0


if __name__ == "__main__":
    sys.exit(main())
