"""README.md and AGENTS.md for every node.

Portolan asks for both beside every catalog.json and collection.json, linked
from it. The root pair says everything; the others say what the node is and
send the reader to the root. Every number in them is counted at build time:
a hand-written fact in the sibling KSJ catalog was wrong, and an agent
repeated it to a planner.
"""

from typing import Dict, Tuple


def _pct(n: int, total: int) -> str:
    return f"{n:,} ({n / total:.0%})" if total else str(n)


def node_docs(doc: Dict, root_rel: str) -> Tuple[str, str]:
    kind = "Collection" if doc["type"] == "Collection" else "Catalog"
    n_items = sum(1 for l in doc["links"] if l["rel"] == "item")
    n_children = sum(1 for l in doc["links"] if l["rel"] == "child")
    what = []
    if n_children:
        what.append(f"{n_children} child links")
    if n_items:
        what.append(f"{n_items} item links")
    readme = (
        f"# {doc['title']}\n\n{doc['description']}\n\n"
        f"This {kind} holds {', '.join(what) or 'no links'}. "
        f"It is one node of an unofficial static STAC mirror of 東京都オープンデータカタログ; "
        f"see [the root README]({root_rel}README.md).\n"
    )
    agents = (
        f"# AGENTS.md: {doc['title']}\n\n"
        f"Read [the root AGENTS.md]({root_rel}AGENTS.md) first. It says what each field means and "
        "which ones are derived rather than stated by the catalog.\n\n"
        f"Do not crawl this tree to answer a question across datasets. "
        f"`{root_rel}items.parquet` (one row per dataset) and `{root_rel}assets.parquet` "
        "(one row per file) answer it in one query.\n"
    )
    return readme, agents


def root_docs(stats: Dict, base: str) -> Tuple[str, str]:
    n = stats["datasets"]
    b = stats["basis"]
    f = stats["footprint"]
    lic = ", ".join(f"{k} {v:,}" for k, v in stats["licenses"].most_common())
    readme = f"""# 東京都オープンデータカタログ (static STAC)

[東京都オープンデータカタログ](https://catalog.data.metro.tokyo.lg.jp/) の
{n:,} データセット、{stats['resources']:,} ファイルを、STAC 1.1 の静的カタログにしたものです。
非公式のミラーです。データ本体は持たず、各ファイルは公開元の URL を指します。

## 入口

- [組織別](collections/catalog.json): {stats['organisations']} 組織。1 組織が 1 Collection
- [分類別](categories/catalog.json): CKAN のグループ
- [形式別](formats/catalog.json): CSV, XLSX, PDF, GeoJSON ...
- [共通項目別](families/catalog.json): 同じ名前のデータセットを {stats['min_orgs']} 以上の組織が公開しているもの
  {stats['families']} 種類 ({stats['family_datasets']:,} 件)。うち {stats['national_families']} 種類はデジタル庁の
  自治体標準オープンデータセット。区市町村を比べるならここから
- [items.parquet](items.parquet): 全データセットを 1 行ずつ (GeoParquet)
- [assets.parquet](assets.parquet): 全ファイルを 1 行ずつ

## 対応関係

| CKAN | STAC |
|---|---|
| organization | Collection |
| dataset (package) | Item |
| resource | asset |

## CKAN に無いので導いた値

STAC は Item に場所と時刻を求めますが、CKAN のデータセットはどちらも持っていません。
導いた値には、何から導いたかを必ず併記しています。

- 時刻 (`tokyo:datetime_basis`): ファイル名の「令和4年度」などから {_pct(b.get('resource-name', 0), n)}、
  データセット名から {_pct(b.get('dataset-title', 0), n)}、公開者が付けたファイルの日付から
  {_pct(b.get('resource-created', 0), n)}、カタログへの登録日から {_pct(b.get('catalog-record', 0), n)}
- 場所 (`tokyo:footprint_basis`): 公開した組織の管轄区域。区市町村 {_pct(f.get('municipality', 0), n)}、
  都の組織は東京都全域 {_pct(f.get('prefecture', 0), n)}。区域は国土数値情報 N03 行政区域 (2026) から

ライセンス: {lic}。

作り方は [GitHub の yuiseki/tokyo-ckan-stac](https://github.com/yuiseki/tokyo-ckan-stac) を参照してください。
"""

    agents = f"""# AGENTS.md: how to get an answer out of this catalog

This is an unofficial static STAC mirror of 東京都オープンデータカタログ, a CKAN
site. It holds metadata only. Every asset href points at the publisher's own
server. {n:,} Items (datasets), {stats['resources']:,} assets (files),
{stats['organisations']} Collections (organisations).

## Start with the tables, not the tree

Do not open Items one by one to answer a question across datasets. Query:

- `{base}/items.parquet`: one row per dataset. GeoParquet, with the footprint.
- `{base}/assets.parquet`: one row per file, with its format, media type, the
  period in its name, and its column names when CKAN knows them.

```sql
-- datasets from 港区 with a CSV that has a latitude column
select a.item_id, a.title, a.href
  from '{base}/assets.parquet' a
 where a.collection = 't131032' and a.format = 'CSV'
   and list_contains(a.columns, '緯度');
```

Fetch with curl, requests or DuckDB. Cloudflare in front of this host has
answered `Python-urllib` with 403 before; send a User-Agent of your own.

## Comparing publishers: start from a family

Questions like "which of 文京区, 台東区 and 千代田区 has the most libraries"
need the same kind of list from each publisher. {stats['families']} names are used by
{stats['min_orgs']} or more organisations; these are families, and each Item in one carries
`tokyo:family`. {stats['national_families']} of them are デジタル庁's 自治体標準オープンデータセット
(`tokyo:national_standard` is the number in its definition books, 01 公共施設一覧
and so on; ゴミ集積所一覧 and 観光ポイント are one character off the national names, and
their columns show they are 30 and 31). The others, such as スポーツ施設一覧 and 公立図書館情報, were
registered across Tokyo in batches without a national definition.

A shared name is a claim; the columns are the evidence. The first row of each
member's first CSV was read, and:

- `tokyo:family_layout_match` is true when the header equals the family's
  most common one, false when it differs, null when it could not be read
  (no CSV, a dead link, or a zip named .csv).

The match is exact, so it is strict. National families have more than one
layout in use because the definition books have versions (a later one adds
法人番号 as the second column) and a second, データモデル型 form whose columns
carry a prefix (投票所_全国地方公共団体コード). A false here often means "an
older or newer layout of the same thing", not "a different thing": compare
the headers before discarding a member.

`{base}/families/index.json` has, per family, how many headers were read and
how many match. Read it before comparing: a family where half the members
differ cannot be compared by counting rows.

```sql
select organization_title, title, family_layout_match, ckan_url
  from '{base}/items.parquet'
 where family = '公立図書館情報'
   and collection in ('t131016', 't131059', 't131067');
```

What a family does not settle. The same name can hold different things:
千代田区's 公共施設一覧 is close to a property register (public toilets,
storehouses, staff housing), while other wards list the facilities residents
use. Some members list facilities outside the publisher's area (sports
grounds on the 荒川 and 江戸川 banks, a ward's lodge in 軽井沢). Where a family
member is missing, the publisher may publish the same thing split by kind
under other names: 台東区 publishes one dataset per kind of facility, and no
公共施設一覧. Absence from a family is not absence of data.

## Fields that are derived, and how far to trust them

CKAN has no field for where a dataset is or what period it covers. STAC
requires both, so both are derived, and the derivation is named on every Item.

`tokyo:datetime_basis`, in the order tried:

| basis | Items | what the time is |
|---|---|---|
| resource-name | {b.get('resource-name', 0):,} | periods named in the file names: 令和4年度 is 2022-04-01 to 2023-03-31 in Tokyo |
| dataset-title | {b.get('dataset-title', 0):,} | the same, from the dataset title |
| resource-created | {b.get('resource-created', 0):,} | the `created` date the publisher gave the files. Sometimes the date of the data (港区's photographs are dated by year), sometimes the date of upload |
| catalog-record | {b.get('catalog-record', 0):,} | when the record was created in CKAN. Says nothing about the data |

Only `resource-name` and `dataset-title` are about the data. Filter on the
basis before using the time for anything that matters. Assets carry their own
`start_datetime`/`end_datetime` when their name names a period, so a dataset
with one file per year can be narrowed to the year you want.

`created` and `updated` on an Item are the CKAN record's times, as STAC
defines them. `updated` was rewritten for nearly every dataset when the
catalog moved in 2025; it is not when the data changed.

`tokyo:footprint_basis`:

| basis | Items | geometry |
|---|---|---|
| municipality | {f.get('municipality', 0):,} | rectangles around the publishing ward, city, town or village |
| prefecture | {f.get('prefecture', 0):,} | rectangles around the whole of Tokyo, islands included |

The footprint is where the data can be, not where it is. A 港区 dataset may
list facilities outside 港区; a bureau's dataset may be about one building. The
whole-of-Tokyo geometry is a MultiPolygon of separate rectangles because one
rectangle would run from 沖ノ鳥島 (20N) to 奥多摩: a query on the sea between
the islands does not match, but a `bbox` test does, since `bbox` is one box.
Prefer the geometry.

## Other things that are not what they look like

- `ckan:size` on an asset is the catalog's own figure. It is rounded down to
  a KiB and is sometimes 1. It is not a measured size; `file:size` is left out
  until one is measured.
- `tokyo:format` is the publisher's label, normalised. The asset `type` follows
  the file name when there is one, so the two disagree for files labelled XLS
  that are .xlsx, or labelled KML that are zips. The `type` is what you will get.
- `table:columns` appears only on files CKAN loaded into its DataStore
  ({stats['datastore_schemas']:,} in this build). Most of them are statistical tables. A file
  without it may still have columns; CKAN just does not know them.
- `tokyo:update_frequency` is the publisher's words (170 spellings). The class
  in `tokyo:update_frequency_class` is for filtering, and `other` means the
  words did not fit a class, not that they were unreadable.
- Licences: {lic}. Each Item links its licence. Individual files can still
  carry third-party rights the record does not mention; check the publisher's
  page (`rel: related`) before redistributing.

## When nothing matches

The catalog holds only what is registered in 東京都オープンデータカタログ.
Many wards publish more on their own sites. No match here means not registered
here, not that the data does not exist.
"""
    return readme, agents
