# When is the more expensive model worth paying for?

**Claude Fable 5.2 and Claude Opus 5.5 on a small business's own work.**
Joseph Riggs, Native Reason Ltd, London. November 2026.

Claude Fable 5.2 is Anthropic's top AI model, and it is twice the price of the next one down, Claude Opus 5.5. I ran both on my own business's everyday jobs to see when the dearer one is worth it.

## The short answer

1. **Routine jobs with a right answer** (sorting email, pulling dates out of a thread, small code fixes): the top model did no better, and it cost 2.7 times as much. Use the cheapest model that passes your own test.
2. **Research and audits:** in blind checks Opus 5.5 was as accurate as Fable 5.2, for less than half the cost on research.
3. **A second opinion before something goes out:** Fable 5.2 caught every known problem in a draft, three runs out of three. Opus missed one or two each time. This was the one job where the top model earned its price.
4. **Whichever model you use, check the facts a decision rests on.** About one research claim in four, from either model, cited a page that did not back it.

No client documents or client personal data were used: the tests run on made-up data, my own business notes and public web pages.

[Read the paper (PDF)](paper/paper.pdf). Page 1 has the short answer. Everything below is for anyone who wants to check the numbers.

## How it was tested, in one paragraph

All 25 bench jobs were marked by code, and each ran three times on both models at the same settings (150 runs). Three open-ended jobs (research, an audit, and a second opinion on a draft) ran two or three times per model and were checked blind by a third model. On research Fable cost 2.3 times as much as Opus, and on the audit 1.15 times.

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
| `data/marking-rules.md` | The marking rules for the re-tests, as saved before any run started, with a few private references reworded (no rule changed) |
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
| 1 | 18 November 2026 | First draft, not released. Two reviews, one by each model under test, said its open-ended results rested on single runs |
| 2 | 19 November 2026 | The full matched bench pass and blind re-tests of the research, audit and second-opinion jobs. The first draft's research advantage for Fable did not repeat |
| 2.1 | 25 November 2026 | Correction to Section 3.2: it gave USD 16.54 against 6.24 as the cost of three runs of every job. Those figures are the cost of an average run of every job; all three runs of every job cost USD 49.63 against 18.71. The ratio of 2.65 and every result are unchanged. |

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
  note        = {Version 2.1, 25 November 2026}
}
```

## Licence

The paper, figures and data are released under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The scripts are released under the MIT licence. See `LICENSE`.

Contact: hello@nativereason.com, https://nativereason.com
