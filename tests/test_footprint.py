from tokyo_ckan_stac.footprint import (
    geometry_of, merge_boxes, outer_bbox, polygon_boxes)


def test_boxes_closer_than_the_gap_merge():
    boxes = [(139.0, 35.0, 139.1, 35.1), (139.12, 35.0, 139.2, 35.1)]
    assert merge_boxes(boxes, gap=0.05) == [(139.0, 35.0, 139.2, 35.1)]


def test_boxes_further_apart_stay_apart():
    # 小笠原村 is 父島 and 母島 near 142E and 沖ノ鳥島 at 136E: one box
    # around all three would cover 1,500 km of open sea.
    boxes = [(142.1, 27.0, 142.3, 27.2), (136.07, 20.42, 136.09, 20.43)]
    assert sorted(merge_boxes(boxes, gap=0.1)) == sorted(boxes)


def test_merging_is_transitive():
    boxes = [(0.0, 0.0, 1.0, 1.0), (2.0, 0.0, 3.0, 1.0), (1.04, 0.0, 1.96, 1.0)]
    assert merge_boxes(boxes, gap=0.05) == [(0.0, 0.0, 3.0, 1.0)]


def test_polygon_boxes_reads_every_polygon_of_a_multipolygon():
    geom = {"type": "MultiPolygon", "coordinates": [
        [[[0, 0], [1, 0], [1, 1], [0, 0]]],
        [[[5, 5], [6, 5], [6, 7], [5, 5]]],
    ]}
    assert polygon_boxes(geom) == [(0, 0, 1, 1), (5, 5, 6, 7)]
    assert polygon_boxes({"type": "Polygon", "coordinates": [[[0, 0], [2, 0], [2, 3], [0, 0]]]}) \
        == [(0, 0, 2, 3)]


def test_geometry_is_a_multipolygon_of_rectangles():
    g = geometry_of([(0.0, 0.0, 1.0, 1.0), (5.0, 5.0, 6.0, 7.0)])
    assert g["type"] == "MultiPolygon"
    assert g["coordinates"][0] == [[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0], [0.0, 0.0]]]
    assert outer_bbox([(0.0, 0.0, 1.0, 1.0), (5.0, 5.0, 6.0, 7.0)]) == [0.0, 0.0, 6.0, 7.0]
