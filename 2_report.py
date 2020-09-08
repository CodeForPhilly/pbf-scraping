# ---
# jupyter:
#   jupytext:
#     formats: py:light,ipynb
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.4.2
#   kernelspec:
#     display_name: venv-pbf-scraping
#     language: python
#     name: venv-pbf-scraping
# ---

# + tags=["hide-input"]
import os
import pandas as pd

from plotnine import *
from sqlalchemy import create_engine

#import dotenv
#dotenv.load_dotenv()

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

df = pd.read_sql("""
SELECT filing_date, bail_status, COUNT(*) as ttl
FROM new_criminal_filings
GROUP BY filing_date, bail_status
""", engine)

# + tags=["hide-input"]
df["filing_date"] = df.filing_date.astype("datetime64[ns]")

(ggplot(df, aes("filing_date", "ttl", color = "bail_status"))
  + geom_point()
  + geom_line()
  + theme(axis_text_x = element_text(angle = 45, hjust = 1))
)

