# Website

Builds the static rating website into `output/` (not committed): a rankings
page, one profile page per person at `u/<handle>.html`, and an about page.

```text
contestant_rating/output + codeforces/data/users.json
+ rating_calculator/input/credits.json
-> output/
```

Pages use relative links, so the same files work locally and on GitHub Pages.
Light and dark mode follow the system setting until the visitor picks one.

## Files

- `builder.py`: `build()` loads the ratings and Codeforces profiles and writes the pages
- `pages.py`: the HTML of each page
- `chart.py`: the rating history chart (inline SVG)
- `theme.py`: rating tiers and Codeforces rank colours
- `static/style.css`, `static/app.js`: styles, theme switch, search, and chart tooltips
