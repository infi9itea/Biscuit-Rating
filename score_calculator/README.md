# Score Calculator

Combines the performances of each institution's teams into one score per
contest.

```text
performance_calculator/output/performances.csv + contests (dates) + input/options.json
-> output/score_history.csv + output/score_rank_history.csv
```

Columns are contests, newest first. Rows are institutions that have at least
one score, best in the newest contest first.

## Files

- `calculators.py`: the `ScoreCalculator` interface, implementations, and
  registry
- `service.py`: `run()`
- `input/options.json`: selected calculator and its parameters

## Biscuit

Takes the institution's best `institution_team_limit` teams and combines their
performances with a power mean:

```text
(mean(performance^rating_degree))^(1 / rating_degree)
```
