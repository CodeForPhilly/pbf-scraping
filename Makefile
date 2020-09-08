#YESTERDAY:=$(shell date +%Y-%m-%d -d "1 day ago")
YESTERDAY=shit

all: output/$(YESTERDAY).csv

output/%_anonymized.csv: 1b_anonymize.py output/%.csv
	python $^ $@

output/%.csv: 0_scrape.py
	python $< --record-date $* --out $@

