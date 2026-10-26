PYTHON=python
PIP=pip
PACKAGE=pyglobalcache
VERSION=$(shell bin/$(PACKAGE) --version)

all: build

style:
	pycodestyle --config=pycodestyle.cfg $(PACKAGE)/*.py

build: dist/$(PACKAGE)-$(VERSION).tar.gz

dist/$(PACKAGE)-$(VERSION).tar.gz: $(PACKAGE)/__init__.py pyproject.toml
	${PYTHON} -m build

install:
	$(PIP) install .

version:
	@echo ${VERSION}

uninstall:
	$(PIP) uninstall $(PACKAGE)

upload:
	twine upload dist/*

clean:
	rm -rf dist build */__pycache__ $(PACKAGE).egg-info $(PACKAGE)-$(VERSION)

.PHONY: clean pycodestyle build install uninstall
