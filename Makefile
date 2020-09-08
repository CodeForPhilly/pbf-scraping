#YESTERDAY:=$(shell date +%Y-%m-%d -d "1 day ago")
YESTERDAY=shit

all: output/$(YESTERDAY).csv

output/%_anonymized.csv: 1b_anonymize.py output/%.csv
	python $^ $@

output/%.csv: 0_scrape.py
	python $< --record-date $* --out $@

2_report.ipynb: 2_report.py
	jupytext --to ipynb $<

2_report.html: 2_report.ipynb
	jupyter nbconvert --execute \
		--ExecutePreprocessor.timeout=600 \
		--TagRemovePreprocessor.remove_input_tags="{'hide-input'}" \
		$<
