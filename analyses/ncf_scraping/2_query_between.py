# ---
# jupyter:
#   jupytext:
#     formats: py:light,ipynb
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.4.2
# ---

# + tags=["hide-input"]
import os
import pandas as pd
import sys

from sqlalchemy import create_engine

start_date, end_date = sys.argv[1:3]
import dotenv
dotenv.load_dotenv()

config = {
    "AWS_ACCESS_KEY_ID": os.environ["AWS_ACCESS_KEY_ID"],
    "AWS_SECRET_ACCESS_KEY": os.environ["AWS_SECRET_ACCESS_KEY"],
    "REGION_NAME": os.environ["REGION_NAME"],
    "SCHEMA_NAME": os.environ["SCHEMA_NAME"],
    "S3_STAGING_DIR": os.environ["S3_STAGING_DIR"],
         }
conn_str = "awsathena+rest://{AWS_ACCESS_KEY_ID}:{AWS_SECRET_ACCESS_KEY}@athena.{REGION_NAME}.amazonaws.com:443/"\
           "{SCHEMA_NAME}?s3_staging_dir={S3_STAGING_DIR}".format(**config)
engine = create_engine(conn_str)

ncf = pd.read_sql("""
    SELECT *
    FROM new_criminal_filings
    """,
    engine
)

ncf["filing_date"] = pd.to_datetime(ncf.filing_date, format = "%m/%d/%Y")

sub_ncf = ncf[ncf.filing_date.between(start_date, end_date)]
# note that between is inclusive by default
print(sub_ncf.to_csv(index = False))
