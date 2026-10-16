# Rating Calculator

Combines each institution's contest scores into a rating after every credited
contest.

```text
score_calculator/output/score_history.csv + contests (dates)
+ input/credits.json + input/options.json
-> output/latest_ratings.csv + output/ratings_history.csv + output/rating_rank_history.csv
```

`input/credits.json` selects the contests and sets their weight. A credited
contest without a score or a date is an error.

## Files

- `calculators.py`: the `RatingCalculator` interface, implementations, and
  registry
- `service.py`: `run()`
- `input/credits.json`: contest credits
- `input/options.json`: selected calculator and its parameters

## Biscuit

At every point in the history, each contest the institution took part in gets
a weight from its credit and its age:

```text
weight = credit * (1 - time_decay_rate)^(days since contest / time_decay_pulse_days)
```

Scores are then combined with a weighted root mean square:

```text
sqrt(sum(weight * score^2) / sum(weight))
```

Both parts are plain weights. A contest with credit 3 counts three times as
much as one with credit 1. With `time_decay_rate` 0.2 and
`time_decay_pulse_days` 30, a contest loses 20% of its weight every 30 days,
so its weight halves after about 93 days. The exponent is fractional, so the
decay is a smooth curve.
