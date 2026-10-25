.PHONY: all setup collect stats dashboard test clean-cache insights insights-fetch

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
	$(PYTHON) -m src.dashboard.build_insights_js

insights-fetch:
	$(PYTHON) -m src.collect.fetch_counts_by_year
	$(PYTHON) -m src.collect.fetch_author_careers

insights:
	$(PYTHON) -m src.stats.insights.run_all
	$(PYTHON) -m src.dashboard.build_insights_js

test:
	$(PYTHON) -m pytest tests/

clean-cache:
	rm -rf data/cache/*

