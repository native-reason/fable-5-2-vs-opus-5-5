---
type: trial-rubric
status: done
captured: 2026-11-19
note: written and saved BEFORE any run was launched, so the marking cannot be fitted to the results. No run or checker saw this file.
---

# Marking rules for the paper 1 re-tests (fixed before any run)

Why: the paper's open-ended trials (research R, audit A, second opinion S) were one run per arm,
and R shared one search allowance that Opus used up and Fable did not. These re-runs give each
run its own allowance, repeat each arm, and check the claims without the checker knowing which
model wrote them.

## Set-up common to every run

- One `claude -p` call per run, its own process, so its own web-search allowance. No personal
  settings, hooks, CLAUDE.md or MCP servers (`--setting-sources ""`, `--strict-mcp-config`), no
  saved session. Effort `high` for every run of both models. Time limit 40 minutes (2400 s): a run
  past it is killed and recorded as "timed out", not scored.
- Models by full id: `claude-fable-5-2`, `claude-opus-5-5`. Checkers: `claude-sonnet-5-5` (neither
  compared model). The model that really ran is read from the call's own record (modelUsage and
  each message's model field); a run on a different model is reported, not counted.
- At most 2 calls at once, below-normal priority. Runs are queued so the two models alternate and
  run side by side.
- Cost is the figure the call reports (list price). On Joe's plan it is allowance, not money.
- Every call is recorded as a full event log (stream-json), so tool calls can be listed afterwards.

## R: research (10 runs: packaging brief Fable x3, Opus x3; fresh brief on accounting software x2 each)

1. **Claim.** One distinct fact about the outside world stated in section 1 (Short answer) or
   section 4 (Blockers and gotchas) of the report: a number, price, date, rule, term, limit or named
   behaviour of a named product, law or platform. Recommendations, opinions, advice and statements
   about the report itself are not claims. A bullet with three facts is three claims.
2. **Extraction.** A Sonnet 5.5 call lists every claim in those two sections of the stripped report,
   in document order, each with the source URL(s) the report ties to it (inline, or via its [S#] tag
   to the Sources section). A claim with no source in the report is listed with "none".
3. **Sampling.** Claims are numbered in document order. If a report has more than 12, code draws 12
   with `random.Random(20261119 + run_number)`; if 12 or fewer, all are checked. Same rule for
   every run. The draw is by code, not by anyone's judgement.
4. **Blinding.** Each report is relabelled with a random letter, shuffled; the key is saved in a
   separate file that is not opened until all checks are done. Lines that name the model, "Anthropic
   model", a model id or a run number are removed from the text the checkers see. The checker is told
   only the claim and its cited URL(s), never the model, run or the other runs.
5. **Check.** A Sonnet 5.5 call per report opens each cited source (page fetch), compares the claim
   to the source text, and gives one verdict per claim:
   - **right**: the opened source says it (a close paraphrase counts; a quote in quote marks must
     match word for word apart from punctuation).
   - **wrong**: the opened source, or a current official page, says something different from the
     claim.
   - **unsupported**: the source opens but does not say it, or the report gave no source.
   - **out of date**: the source says it but a newer or official current page shows it no longer
     holds (or the source is dated before a change the checker can show).
   - **dead link**: the cited URL does not open (not found, blocked, or an error) after one retry.
   For wrong or out of date the checker gives the evidence URL.
6. **Reported per model, with every run shown:** claims checked, counts of each verdict, **hard
   error rate = (wrong + out of date) / checked**, **problem rate = (wrong + out of date +
   unsupported + dead link) / checked**; also wall time, cost, output tokens, web searches and
   page reads, report words, distinct sources, and whether all 8 sections are present.
7. **Reading the result.** n is 3 per model on the packaging brief and 2 on the fresh brief. A model
   is called better on a measure only if every one of its runs on that brief beats every run of the
   other (so the ranges do not overlap). Otherwise: "no clear difference". No significance test; n is
   too small and the report says so.

## A: audit (4 runs: Fable x2, Opus x2)

- Same brief (rebuilt from the original, read-only, answer returned as text), same vault state (all
  four launched back to back today), tools Read, Glob, Grep only. Blocked by rule: `Clients/`,
  `Life/`, `Emails/`, `Inbox/`, plus the earlier audit's own report folder and files that describe it,
  so no run can read the earlier answer.
- **Client check:** the full call log of every run is searched for any tool call whose path
  contains `Clients`; any such attempt (allowed or denied) is reported. A read that succeeded would
  void that run.
- **Top ten.** The first ten numbered findings of each report. Labels hidden as in R4 (random
  letters, key saved separately, model self-references removed).
- **Check.** A Sonnet 5.5 call per report, with Read, Glob, Grep and a few read-only commands (ls,
  wc, git log, git status), checks each finding against the actual files and gives:
  - **real**: true as stated (a count within a few of the claim, or off only because the files moved
    since, counts as real and is noted).
  - **real, wrong cause**: the symptom exists but the finding blames the wrong cause.
  - **not real**: the claim is false, or the thing it points to does not exist.
  - **could not check**: only when the claim cannot be tested with those tools; reported, not
    counted either way.
- Reported per model: findings checked, real / wrong cause / not real / could not check, share real,
  time, cost, tokens, files read.

## S: second opinion (6 runs: Fable x3, Opus x3)

- Same brief (rebuilt, the original was not saved), same draft (the Opus 5.5 suggestion as logged),
  same frozen copy of the site and notes as they stood before the title was changed (commit
  `347a2e084^`), tools Read, Glob, Grep only.
- **Claims.** Each distinct problem or factual claim in the review's points 2 and 4 is one claim.
- **Check (blind).** Sonnet 5.5 checks each against the frozen files: **true**, **partly true**,
  **false**, or **not checkable from the files**. Character counts are checked by counting.
- **Known-issues checklist, fixed now.** The earlier Fable review caught these; a run scores each
  one it states clearly: C1 "small businesses" reverses the owner's 2026-10-19 decision (no size on
  the site); C2 the title is too long and would be cut in results (about 60 characters); C3 the
  " | " separator breaks the site's " - Native Reason" title pattern; C4 the draft's "for small
  businesses in West London" claims customers are in West London when the site only says Joe is;
  C5 the owner's 2026-10-20 decision 13 (site is for people he has met, no promotion) is in tension
  with search work. Scored yes/no per run by the blind checker, from the review text alone.
- Reported per model: claims checked, share true, false claims, checklist items caught (out of 5),
  time, cost, tokens.

## W: writing

No runs. A blind ranking sheet for people, with the key kept apart. Not sent to anyone.

## What the summary must do with the result

For each trial, say plainly whether the paper's claim stands, weakens or flips, and give the limits
(n, rebuilt briefs, same-day changes in the vault, checker is one model).
