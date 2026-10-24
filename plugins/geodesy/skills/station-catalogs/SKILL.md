---
name: station-catalogs
title: Station Catalogs
description: Read any station catalog (ids and coordinates of GNSS or other monitoring stations) without guessing columns - identify latitude, longitude and height by value range and documentation, handle unit-label rows and duplicate column names, and write a normalized copy for spatial filtering. Bundles station_catalog.py.
keywords:
- level:L1
- geodesy
- stations
---

# Station catalogs

A station catalog is a table of station ids and positions. Its column names
are not evidence of what the columns hold: headers may carry unit labels on a
second row, two columns may share a name, a column named for one coordinate
may hold another (height, or a longitude in [0, 360)), and a plain CSV reader
may keep only the last of two same-named columns.

1. **Profile it.** `station_catalog.py profile` reports each column by name
   and `#index`: how many values are numeric, their range, duplicate names,
   header-like rows, and which columns *could* be latitude or longitude.
2. **Decide the columns** from the profile and the catalog's documentation:
   latitude within [-90, 90]; longitude within [-180, 180] or [0, 360); height
   in metres, often hundreds to thousands; the id unique per station. When the
   evidence leaves two candidates, compare a few known stations with their
   published positions or ask the user.
3. **Write a normalized copy** with `station_catalog.py write` (columns
   `id,latitude,longitude[,height]`), to the workspace. It keeps only rows
   with coordinates in range and reports every dropped row by reason, wrapped
   longitudes and duplicate ids. Record which source columns you chose and why.
4. Use the normalized copy for every spatial filter, and the raw file only as
   the cited source.

```text
uv run --no-project "SKILL_ROOT/scripts/station_catalog.py" profile CATALOG.csv --out PROFILE.json
uv run --no-project "SKILL_ROOT/scripts/station_catalog.py" write CATALOG.csv --id COL --lat COL --lon COL [--height COL] [--wrap-longitude] -o NORMALIZED.csv --out REPORT.json
```

A filter result is trustworthy only if the input rows were nonzero and few
rows were skipped as invalid; a zero count from a catalog that failed to parse
is not "no stations".
