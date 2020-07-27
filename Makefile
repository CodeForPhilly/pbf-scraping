YESTERDAY:=$(shell date +%Y-%m-%d -d "1 day ago")

all: $(YESTERDAY).csv

%.csv: scrape.py
	python $< --record-date $* --out $@

scraped_data.csv: scrape.py
	python $< --record-date $* --out $@

