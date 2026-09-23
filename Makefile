PY := PYTHONPATH=src python3

.PHONY: help packages footprints datastore build validate test serve start install-catalog clean

help:
	@echo "make packages    every dataset record from the CKAN API (under a minute)"
	@echo "make footprints  municipality rectangles from N03 (one 13 MB download)"
	@echo "make datastore   column names of every DataStore resource (hours; resumable)"
	@echo "make build       data/ -> catalog/, plus items.parquet and assets.parquet (offline)"
	@echo "                 BASE_URL=... sets the absolute self links"
	@echo "make validate    check catalog/"
	@echo "make serve       serve catalog/ on :8765 with CORS, for other clients"
	@echo "make start       browse catalog/ in STAC Browser on :8080"
	@echo "make test        unit tests"
	@echo "make install-catalog   rsync catalog/ to \$$(CATALOG_ROOT)"

packages:
	$(PY) scripts/01_fetch_packages.py

footprints:
	$(PY) scripts/02_footprints.py

datastore:
	$(PY) scripts/03_datastore_fields.py

BASE_URL ?= https://stac.yuiseki.net/tokyo-ckan

build:
	$(PY) scripts/04_build_stac.py --base-url "$(BASE_URL)"
	$(PY) scripts/05_geoparquet.py --base-url "$(BASE_URL)"

validate:
	$(PY) scripts/06_validate.py

serve:
	$(PY) scripts/07_serve.py

start:
	bash scripts/08_browser.sh

test:
	$(PY) -m pytest tests -q

# stac.yuiseki.net serves /data/www/html/stac; this catalog is one directory
# in it, next to mlit-nlftp.
CATALOG_ROOT ?= /data/www/html/stac/tokyo-ckan

install-catalog:
	@test -f catalog/catalog.json || { echo "catalog/ is empty; run make build" >&2; exit 1; }
	mkdir -p $(CATALOG_ROOT)
	rsync -a --delete catalog/ $(CATALOG_ROOT)/
	@echo "$(CATALOG_ROOT) updated"

clean:
	rm -rf catalog
