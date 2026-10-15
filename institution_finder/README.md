# Institution Finder

Owns the institution database: canonical names, their alternate names, and
everything that reads or changes them.

## Files

- `finder.py`: `InstitutionFinder` resolves any known name to its canonical
  name and suggests fuzzy matches
- `database.py`: `add_institution()`, `add_alt_name()`, and `validate()`
- `resolve.py`: `resolve_interactively()` asks a person how to resolve each
  unknown name
- `data/institutions.json`: the database

Every name is uppercase and belongs to exactly one institution.

```python
from pathlib import Path
from institution_finder import InstitutionFinder

finder = InstitutionFinder(Path("institution_finder/data/institutions.json"))
finder.resolve("BANGLADESH UNIVERSITY OF ENGINEERING & TECHNOLOGY")
finder.best_matches("UNIVERSITY OF DHAKAA", 3)
```
