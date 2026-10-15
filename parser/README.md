# Parser

Turns saved standings HTML into contests and saves them with the `contests`
module, which owns the contest format.

```text
input/contests.json + input/options.json + input/contest_files/*.html
-> output/contests/<contest-id>.json + output/manifest.json
```

## Files

- `parsers.py`: the `Parser` interface, the `BAPS` and `TOPH` parsers, and the
  parser registry
- `service.py`: `run()` parses the contests whose sources changed
- `input/contests.json`: each contest's name, date, standings files, and parser
- `input/options.json`: `fail_on_warnings` stops on any unparseable row
- `input/contest_files/`: saved standings HTML
- `output/contests/`: parsed contests
- `output/manifest.json`: source hashes, parser versions, and parse statistics

## Parsers

- `BAPS`: BAPS standings (pages link to `bapsoj.org`)
- `TOPH`: Toph standings, detecting the older and current layouts per row

Every parseable row is kept. Unofficial ranks such as `*` are stored as `null`.
A contest is reparsed only when its files, parser, parser `version`, or date
change. Bump a parser's `version` after changing its output.

To add a parser, subclass `Parser`, implement `parse_row()`, and register it
in `PARSERS`.
