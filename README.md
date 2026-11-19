# When is the more expensive model worth paying for?

**Claude Fable 5.2 and Claude Opus 5.5 on a small business's own work.**
Joseph Riggs, Native Reason Ltd, London. November 2026.

[Read the paper (PDF)](paper/paper.pdf)

Fable 5.2 costs twice as much per token as Opus 5.5. I ran both on the work of my one-person AI consultancy and checked what came back: all 25 bench jobs marked by code, three runs each with both models at the same settings (150 runs), and three open-ended jobs (research, an audit, a second opinion on a draft) repeated two or three times per model and checked blind by a third model. No client documents or client personal data were used: the bench jobs run on made-up data, and the open-ended work on the business's own notes and public web pages.

In short: on jobs with a right answer a computer can check, the two were level and Fable cost 2.7 times as much. On research and the audit they were level too, with Fable costing 2.3 and 1.15 times as much. Fable was better at one job, a second opinion on a draft: it caught every known problem in all three runs, and Opus missed one or two. Both models cited pages that did not back their claims, about one research claim in four, so check the facts a decision rests on whichever model you use.

## What is in this repository

| Path | What it is |
|---|---|
| `paper/paper.pdf` | The paper |
| `paper/paper.src.html` | Its source; `scripts/build.py` fills in the data tables and prints the PDF |
| `paper/figures/` | The three figures as SVG and PNG, drawn by `scripts/figures.py`: every run of the matched pass (Figure 1), cost and time ratio per job (2), the research re-test (3) |
| `data/runs.csv` | One row per bench run: study, job, model, effort, repeat, score, wall time, cost, tokens, turns, start time, and whether the run is excluded or its time left out |
| `data/by_task.csv` | Means per study, job, model and effort, with the lowest and highest of the repeats |
| `data/pairs_matched.csv` | Fable against Opus job by job in the matched pass (19 November) |
| `data/pairs_study1.csv`, `data/pairs_study2.csv` | The earlier comparisons (10 and 11 November), kept in Appendix B |
| `data/totals.csv` | Total cost and time ratios with a 95% range from resampling the jobs |
| `data/pause_windows.csv` | When the machine's freeze watchdog paused batch jobs; runs overlapping a pause are left out of the timing |
| `data/retests.csv` | One row per open-ended re-test run: time, cost, tokens, tool use and the blind verdict counts |
| `data/marking-rules.md` | The marking rules for the re-tests, as saved before any run started |
| `scripts/` | `extract.py` and `extract_retests.py` (raw files to CSV), `figures.py`, `build.py` |

## What is not here

The prompts, the model replies and the open-ended reports are not published, because they contain private details of how my business runs. Every number the paper uses from that work is in `data/retests.csv` and the paper's tables.

## How the numbers were produced

- The matched pass and the re-tests ran on 19 November 2026 through Claude Code 2.1.328 on one Windows laptop, headless, with no personal settings, hooks or memory loaded, both models at high effort.
- Models were named by their full identifiers, `claude-fable-5-2` and `claude-opus-5-5`, and the model each run actually used was checked in its own record.
- Bench scores come from code: answer keys, hidden tests, or scripts that check what an agent left behind. No model marks the bench.
- The open-ended reports were relabelled with random letters before checking. Claude Sonnet 5.5, neither of the models compared, checked them: 12 claims per research report drawn by code with a fixed seed and checked against the cited page, the top ten audit findings checked against the files, and each second-opinion claim checked against a frozen copy of the site. The key was opened only after every check had finished.
- Cost is the list-price figure Claude Code reports for each call. The runs used a Claude Max subscription, so for me it was allowance used, not money; for a business paying per token it is the bill.
- The laptop was in use during the runs. A watchdog paused or killed batch jobs when the processor was flat out. Killed runs were started again from scratch, and runs that overlapped a pause keep their score and cost but are left out of the timing.

## How "better" and "same" are decided

- Bench: scores within 0.02 are the same; time or cost must differ by at least 15% to count as different. Total ratios have a 95% range from resampling the jobs 10,000 times with a fixed seed (20261119).
- Open-ended re-tests: a model is better on a measure only if every one of its runs beats every run of the other. Otherwise: no clear difference. No significance tests; two or three runs are too few.

## Rebuilding

`scripts/extract.py` and `scripts/extract_retests.py` read the raw result files, which stay private, so only I can run them. The other two work from the CSVs alone:

```
python scripts/figures.py   # draws the three figures into paper/figures/
python scripts/build.py     # fills the tables and prints paper/paper.pdf
```

Run `figures.py` first, because the PDF uses the figure files. `build.py` needs Chrome, Edge or Brave installed to print the PDF; `python scripts/build.py --no-pdf` builds the HTML only. Both need Python 3 and matplotlib.

## Versions and corrections

Corrections will be made as new versions, with earlier versions kept in the history below.

| Version | Date | Change |
|---|---|---|
| 1 | 18 November 2026 | First draft, not released. Two independent reviews said its open-ended results rested on single runs |
| 2 | 19 November 2026 | The full matched bench pass and blind re-tests of the research, audit and second-opinion jobs. The first draft's research advantage for Fable did not repeat |

## Citation

```bibtex
@techreport{riggs2026fableopus,
  author      = {Riggs, Joseph},
  title       = {When is the more expensive model worth paying for? {Claude Fable 5.2} and {Claude Opus 5.5} on a small business's own work},
  institution = {Native Reason Ltd},
  type        = {Research note},
  number      = {1},
  year        = {2026},
  month       = nov,
  address     = {London, United Kingdom},
  note        = {Version 2, 19 November 2026}
}
```

## Licence

The paper, figures and data are released under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The scripts are released under the MIT licence. See `LICENSE`.

Contact: hello@nativereason.com
