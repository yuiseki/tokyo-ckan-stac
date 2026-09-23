# Design decisions

## Organisation is the Collection

The alternatives were one Collection per CKAN group (分類) or per dataset.
Groups overlap, so an Item would belong to several Collections, and STAC gives
an Item one. A dataset is too small: the median dataset has one resource. The
organisation is the unit that publishes, answers for the data, and has an area,
which is also where the footprint comes from. Groups and formats became browse
trees instead.

## Item is the dataset, asset is the resource

A dataset here is a record with a title, a description and a licence; its
resources are files. The alternative, an Item per resource, would give
83,821 Items most of which repeat their dataset's description. The cost of the
choice is that one Item can have 596 assets. assets.parquet is there so that a
question about files does not have to open Items.

## Time: the words first, then the dates people typed, then the record

STAC requires a time on every Item and CKAN has none that describes the data.
The order tried is the order of how much the evidence is about the data:

1. Periods in resource names. 和暦 and 年度 are read as Tokyo calendar days.
2. Periods in the dataset title.
3. The resource `created` dates, which publishers set. Sometimes the date of
   the data, sometimes of the upload.
4. The CKAN record's creation.

The first that yields anything is used, and `tokyo:datetime_basis` says which.
A reader who needs the data's own time filters on the first two.

Dates that cannot be dates are dropped rather than clamped: 平成99年 does not
exist, and a 3 in 第3表 is not a year.

## Place: the publisher's area, as rectangles

CKAN has no spatial field and the datasets do not share a coordinate column,
so the footprint is the publishing organisation's area. It comes from 国土数値
情報 N03 行政区域 so that this catalog and the KSJ one agree on where Tokyo is.

The geometry is a MultiPolygon of rectangles rather than the boundary: 9,698
copies of the boundary would make the catalog large for no gain in honesty,
since the footprint is already only where the data can be. Rectangles within
0.1 degrees merge; at that gap the mainland is one box per municipality and
each island group is its own, and Tokyo as a whole is 22 boxes.

## Sizes are not measured yet

CKAN's figure is kept as `ckan:size`. A HEAD sweep of 83,821 files across
100 hosts would give `file:size`; it is left for later because it takes
a day at a polite rate, and a catalog without sizes is more useful today than
one with them tomorrow.

## What is borrowed from Portolan and the KSJ catalog

- README.md and AGENTS.md beside every node, linked `describedby` and `agents`.
- `source` as the asset role, since the files are the publishers', not ours.
- A fabricated value is worse than an absent one: hence `ckan:size` rather
  than `file:size`, and the basis fields.
- A Parquet index next to the tree, because agents testing the KSJ catalog
  named reading every Item as their largest cost.
