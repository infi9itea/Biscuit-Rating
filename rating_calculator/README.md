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

## SHONG

At every point in the history, older contests' credits decay:

```text
effective_credit = credit * (1 - time_decay_rate)^(days since contest / time_decay_pulse_days)
```

The exponent is fractional, so the decay is a smooth curve. Scores are then
combined with a credit-weighted root mean square, skipping contests the
institution did not take part in:

```text
sqrt(sum((score * effective_credit)^2) / sum(effective_credit^2))
```
