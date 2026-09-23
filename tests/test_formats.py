from tokyo_ckan_stac.formats import format_label, media_type


def test_the_label_is_normalised_but_not_second_guessed():
    assert format_label("CSV", "https://x/a.csv") == "CSV"
    assert format_label("las", "https://x/a.las") == "LAS"
    assert format_label("GeoTIFF", "https://x/a") == "GEOTIFF"
    assert format_label("cityGML", "https://x/a") == "CITYGML"
    assert format_label("xisx", "https://x/a.xlsx") == "XLSX"
    # A KML inside a zip is still KML to someone looking for KML.
    assert format_label("KML", "https://x/a.zip") == "KML"


def test_an_empty_label_falls_back_to_the_extension():
    assert format_label("", "https://x/a.xlsx") == "XLSX"
    assert format_label("", "https://x/download") is None


def test_the_media_type_follows_the_file_not_the_label():
    # Labelled XLS, served as .xlsx: the browser gets an xlsx.
    assert media_type("XLS", "https://x/a.xlsx") == \
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert media_type("KML", "https://x/a.zip") == "application/zip"
    assert media_type("CSV", "https://x/a.csv?x=1") == "text/csv"


def test_without_a_known_extension_the_label_decides():
    assert media_type("PDF", "https://x/download") == "application/pdf"
    assert media_type("JPEG", "https://x/image.php?id=3") == "image/jpeg"
    assert media_type("GeoJSON", "https://x/a.json") == "application/geo+json"


def test_nothing_known_means_no_type_rather_than_a_guess():
    assert media_type("", "https://x/download") is None
    assert media_type("DXF", "https://x/a") is None
