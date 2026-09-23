# AGENTS.md

## What this repository produces

A static STAC catalog under `catalog/`, built offline from `data/`:

- `collections/<org>/`: one Collection per CKAN organisation, Items inside.
- `categories/<group>/<org>/` and `formats/<label>/<org>/`: views that link
  to the Items. They never copy them.
- `items.parquet`, `assets.parquet`: the same, as tables.

`docs/design.md` has the decisions and why.

## Rules that are not negotiable

- Never publish a derived value without its basis beside it. Time carries
  `tokyo:datetime_basis`, place carries `tokyo:footprint_basis`.
- Never write `file:size` from CKAN's `size`. It is a rounded label.
- Never write a number into a document by hand. `docs.py` counts at build
  time; a hand-written fact in the sibling KSJ catalog was wrong.
- The API is a public service. Keep the DataStore sweep at two workers with a
  pause, and send the project's User-Agent (`src/tokyo_ckan_stac/http.py`).

## Upstream irregularities, verified against the live API

- `portal.data.metro.tokyo.lg.jp` is a front end. The CKAN API is at
  `catalog.data.metro.tokyo.lg.jp/api/3/action/` (CKAN 2.11.4).
- CKAN timestamps are naive UTC. Dates entered in Tokyo arrive as
  `T15:00:00` on the previous day.
- `metadata_modified` was rewritten for nearly every dataset in the 2025
  move. It is not when the data changed.
- A resource's `created` is what the publisher typed: 港区's photographs are
  dated 1953 to 1981, by the year they were taken.
- `size` is floored to a KiB (10,462 resources say exactly 1024) and is
  sometimes 1.
- The format label and the file disagree: 313 resources labelled XLS are
  .xlsx, 264 labelled KML are zips.
- 更新頻度 is free text in 170 spellings.
- Organisation names are `t` plus the 全国地方公共団体コード with its check
  digit for municipalities (`t131032` is 港区), and `t000xxx` for bureaus.
  `t313360` 東京都生活文化スポーツ局 has a valid check digit but 31 is 鳥取県.
- 神津島村 has no organisation in the catalog.

## Tests

`make test`. Fixtures in `tests/fixtures/` are real records from the API,
trimmed. Date parsing cases were taken from the resource names that occur.
