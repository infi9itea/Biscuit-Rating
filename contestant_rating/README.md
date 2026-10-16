# Contestant Rating

Rates every person in `members/data/members.csv` with the Biscuit rating, using
their teams' performances.

```text
members.csv + parsed contests + performance_calculator/output/performances.csv
+ rating_calculator/input (credits, decay) + input/options.json
-> output/ratings.csv + output/history.csv
```

A person's result in a contest is their team's performance. Their rating after
each contest is the Biscuit rating of those results, with the same credits and
time decay as institution ratings, plus one virtual contest rated
`prior_rating` (1000). Its share of the rating is `prior_credit` (1) divided by
`prior_credit` plus the credits of every contest so far: 1/4 after one ICPC,
1/5 after an ICPC and an IUPC. The virtual contest keeps a newcomer with one or
two lucky results from jumping to the top, and only competing wears it down:
it does not fade with time, and a winning result never lowers a rating.

## Files

- `service.py`: `run()`
- `input/options.json`: the virtual contest's rating and credit
- `output/ratings.csv`: latest rating, peak, contest count, last contest, and
  institution per person
- `output/history.csv`: every contest of every person, with team, rank,
  problems solved out of the contest's total, first solves, performance, and
  rating after the contest
