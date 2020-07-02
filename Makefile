YESTERDAY:=$(shell date +%Y-%m-%d -d "1 day ago")

all: output/$(YESTERDAY).csv

output/%.csv: scrape.py
	python $< --record-date $* --out $@

