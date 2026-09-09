# Evaluation set

8 questions against the 4 seeded meetings (`data/seed_meetings/`), covering
retrieval + citation, cross-meeting recall, and the "I don't know" refusal path.

Run it with:

```
python -m src.cli ingest-seed
python -m src.cli eval
```

This auto-scores each question with a simple substring match (see
`expected_contains` in `eval_set.json`), then writes the full model answers to
`eval/eval_results.json`. The substring check is a heuristic, not a real
grader — **read the actual answers yourself and fill in the table below**
before submitting; a "CHECK" row can still be a correct answer the heuristic
happened to miss, and a "PASS" row could in theory cite the wrong meeting.

| # | Question | Expected outcome | Got it right? |
|---|----------|-------------------|----------------|
| q1 | What did we decide about the billing migration? | Mentions Karan owning the historical data migration + rollout plan | |
| q2 | Who owns the historical invoice data migration and when is it due? | Karan, by Wednesday | |
| q3 | What caused the payments outage on Sunday? | Retry logic had no global concurrency cap | |
| q4 | Who owns writing the incident report and by when? | Priya, by Monday | |
| q5 | What was decided about the checkout redesign's mobile payment selector? | Sneha reworking mobile layout, due Tuesday | |
| q6 | What is on the sprint 42 backlog? | Checkout redesign, payments retry logic, notifications cleanup | |
| q7 | Did we discuss quarterly revenue targets in any meeting? | Not present anywhere -> system should say it can't find this in context | |
| q8 | Who is chasing finance sign-off on the PDF template? | Priya | |

**Score: _/8** (fill in after you run it)

If you added your own real recording, add 1-2 questions about it here and
re-run `eval` after adding them to `eval_set.json`.
