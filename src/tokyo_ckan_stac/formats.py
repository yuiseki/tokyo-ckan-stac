"""Format labels and media types.

The publisher's label and the file disagree often enough to matter: 313
resources labelled XLS are .xlsx files, 264 labelled KML are zips. The two
questions get separate answers. The label, normalised, is what a reader
filters on. The media type is what the server will send, so it follows the
file name when the file name says, and the label only when it does not.
"""

from urllib.parse import urlparse

_TYPES = {
    "CSV": "text/csv",
    "XLSX": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "XLS": "application/vnd.ms-excel",
    "PDF": "application/pdf",
    "JPEG": "image/jpeg",
    "JPG": "image/jpeg",
    "PNG": "image/png",
    "GIF": "image/gif",
    "ZIP": "application/zip",
    "TXT": "text/plain",
    "HTML": "text/html",
    "HTM": "text/html",
    "KML": "application/vnd.google-earth.kml+xml",
    "KMZ": "application/vnd.google-earth.kmz",
    "RDF": "application/rdf+xml",
    "GEOJSON": "application/geo+json",
    "JSON": "application/json",
    "XML": "application/xml",
    "DOC": "application/msword",
    "DOCX": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "PPTX": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "GEOTIFF": "image/tiff; application=geotiff",
    "TIF": "image/tiff",
    "TIFF": "image/tiff",
    "MP4": "video/mp4",
    "ODS": "application/vnd.oasis.opendocument.spreadsheet",
}

_ALIASES = {"XISX": "XLSX", "JPG": "JPEG", "HTM": "HTML", "TIF": "TIFF"}


def _extension(url: str):
    path = urlparse(url or "").path
    name = path.rsplit("/", 1)[-1]
    if "." not in name:
        return None
    ext = name.rsplit(".", 1)[-1].upper()
    return ext if ext in _TYPES else None


def format_label(fmt, url):
    label = (fmt or "").strip().upper()
    if not label:
        ext = _extension(url)
        return _ALIASES.get(ext, ext) if ext else None
    return _ALIASES.get(label, label)


def media_type(fmt, url):
    ext = _extension(url)
    if ext == "JSON" and (fmt or "").upper() == "GEOJSON":
        return _TYPES["GEOJSON"]
    if ext:
        return _TYPES[ext]
    label = format_label(fmt, url)
    return _TYPES.get(label) if label else None
