# Performance Calculator

Gives every team in every parsed contest a performance and resolves its
institution to the canonical name.

```text
contests + input/options.json + institution_finder
-> output/performances.csv (Contest, Team, Institution, Performance)
```

Rows keep the contest ranking order. Teams without a numeric rank have an empty
performance, and teams whose institution does not resolve have an empty
institution.

## Files

- `calculators.py`: the `PerformanceCalculator` interface, implementations, and
  registry
- `service.py`: `run()`
- `input/options.json`: selected calculator and its parameters

## Biscuit

For rank `r`, solved count `s`, and the contest's maximum solved count `m`:

```text
maximum_team_rating * (1 - rank_decay_rate)^(r - 1) * (s / m)^solved_ratio_exponent
```
