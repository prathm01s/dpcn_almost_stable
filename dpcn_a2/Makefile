.PHONY: all setup collect stats dashboard test clean-cache

PYTHON ?= python3

all: collect stats dashboard test

setup:
	$(PYTHON) -m pip install -r requirements.txt

collect:
	$(PYTHON) -m src.collect.main

stats:
	$(PYTHON) -m src.stats.main

dashboard:
	$(PYTHON) -m src.dashboard.build_data

test:
	$(PYTHON) -m pytest tests/

clean-cache:
	rm -rf data/cache/*
