# When is the more expensive model worth paying for?

**Claude Fable 5.2 and Claude Opus 5.5 on a small business's own work.**
Joseph Riggs, Native Reason Ltd, London. November 2026.

[Read the paper (PDF)](paper/paper.pdf)

Fable 5.2 costs twice as much per token as Opus 5.5. For a week after Fable came out I ran both on the real work of my one-person AI consultancy and checked what came back: 24 jobs marked by code, eight of them run again on the same night with both models at the same effort, and six pieces of open-ended work (a plan, an audit, a research question, a fault diagnosis, a second opinion and writing in my voice). No client documents or client personal data were used: the code-marked jobs run on made-up data, and the open-ended work on the business's own notes and code.

In short: on jobs with a right answer a computer can check, the two were level and Fable cost about twice as much, which is its price. On open-ended work where one wrong fact changes the decision, Fable was as good or better, and in research clearly more accurate for about 1.6 times the cost. Opus wrote better in my voice. Both made factual mistakes that only checking found.

## What is in this repository

| Path | What it is |
|---|---|
| `paper/paper.pdf` | The paper |
| `paper/paper.src.html` | Its source; `scripts/build.py` fills in the data tables and prints the PDF |
| `paper/figures/` | All five figures as SVG and PNG, drawn by `scripts/figures.py`: method (Figure 1), same or different (2), cost and time ratio per job (3), every Study 2 run (4), total ratios with a range (5) |
| `data/runs.csv` | One row per bench run: study, job, model, effort, repeat, score, wall time, cost, output tokens, turns, start time |
| `data/by_task.csv` | Means per study, job, model and effort, with the lowest and highest of the repeats for score, time and cost |
| `data/pairs_study1.csv` | Fable against Opus job by job, 10 November, Opus from earlier runs |
| `data/pairs_study2.csv` | Fable against Opus job by job, 11 November, same night and same effort |
| `scripts/` | `extract.py` (raw bench files to CSV), `figures.py`, `build.py` |

## What is not here

The prompts, the model replies and the reports from the open-ended work are not published, because they contain private details of how my business runs. Every number the paper uses from that work is given in its tables.

## How the numbers were produced

- Every run went through Claude Code 2.1.322 (2.1.328 for the labelling job, run again on 19 November) on one Windows laptop, headless, with no personal settings, hooks or memory loaded.
- Models were named by their full identifiers, `claude-fable-5-2` and `claude-opus-5-5`, and the model each run actually used was checked in its transcript.
- Scores come from code: answer keys, hidden tests, or scripts that check what an agent left behind. No model marks the bench.
- Cost is the list-price figure Claude Code reports for each call. The runs used a Claude Max subscription, so for me it was allowance used, not money; for a business paying per token it is the bill.
- Study 1 (10 November) compares Fable with Opus and Sonnet runs the bench already held, some from other days and at a lower effort. Study 2 (11 November) runs both models on the same night at the same effort. The paper explains why both are reported.

## How each job is scored

- Each job is one prompt or small agent task copied from real work, run on made-up emails, notes and code.
- A script marks it from 0 to 1: an answer key, hidden tests, or a check of what the agent left behind. No model marks the bench.
- Every hidden test was checked against a correct reference solution first, so a failure is the model's and not the test's.
- Two or three runs per job. For each I record score, wall time, cost and output tokens, and average them.
- "Same" has fixed rules, set before Study 1: scores within 0.02 are the same, and time or cost must differ by at least 15% to count as different.
- Total ratios in Figure 5 have a 95% range from resampling the jobs 10,000 times with a fixed seed (20261119).

## What it is compared against

- **Study 1 (10 November):** Fable 5.2 at high effort on 24 jobs, against the Opus 5.5 and Sonnet 5.5 runs the bench already held. Those ran on other days, and for ten jobs Opus had run at medium effort.
- **Study 2 (11 November):** Opus 5.5 and Fable 5.2 on the same night, the same machine and the same effort, eight pairings of job and effort, two runs each. This is the clean comparison.
- **Sonnet 5.5 and Haiku 5.5** appear as cheaper-model references where the bench held runs of the same job.
- **Open-ended work:** six pieces of work judged by checking claims against sources, re-running findings, or a blind judge. Those reports are not published; their numbers are in the paper's tables.

## Rebuilding

Run these in this order. `scripts/extract.py` reads the bench's raw result files, which stay private, and writes the CSVs in `data/`, so only I can run it. The other two work from the CSVs alone:

```
python scripts/figures.py   # about 2 seconds: draws the five figures into paper/figures/
python scripts/build.py     # about 1 second: fills the tables and prints paper/paper.pdf
```

Run `figures.py` first, because the PDF uses the figure files. If you only want to check that the numbers reproduce, run `figures.py`: it prints the bootstrap ranges and the same-or-different counts. `build.py` needs Chrome, Edge or Brave installed to print the PDF; `python scripts/build.py --no-pdf` builds the HTML only. Both scripts need Python 3 and matplotlib.

## Versions and corrections

Corrections will be made as new versions, with earlier versions kept in the history below.

| Version | Date | Change |
|---|---|---|
| 1 | 18 November 2026 | First release |

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
  address     = {London, United Kingdom}
}
```

## Licence

The paper, figures and data are released under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The scripts are released under the MIT licence. See `LICENSE`.

Contact: hello@nativereason.com
