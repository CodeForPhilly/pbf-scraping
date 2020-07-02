TODAY:=$(shell date +%Y-%m-%d)

all: output/$(TODAY).csv

output/%.csv: scrape.py
	python $< --record-date $* --out $@

