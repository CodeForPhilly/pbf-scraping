#YESTERDAY:=$(shell date +%Y-%m-%d -d "1 day ago")
YESTERDAY=shit

all: output/$(YESTERDAY).csv

output/%_anonymized.csv: 1b_anonymize.py output/%.csv
	python $^ $@

output/%.csv: 0_scrape.py
	python $< --record-date $* --out $@

analyses/ncf_report/2_report.ipynb: analyses/ncf_report/2_report.py
	jupytext --to ipynb $<

analyses/ncf_report/2_report.html: analyses/ncf_report/2_report.ipynb
	jupyter nbconvert --execute \
		--ExecutePreprocessor.timeout=600 \
		--TagRemovePreprocessor.remove_input_tags="{'hide-input'}" \
		$<
