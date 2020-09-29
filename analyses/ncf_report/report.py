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

ncf = pd.read_sql("""
    SELECT *
    FROM new_criminal_filings
    """,
    engine
)

ncf["filing_date"] = ncf.filing_date.astype("datetime64[ns]")

# + tags=["hide-input"]
status_counts = (ncf
        .groupby(["filing_date", "bail_status"])
        .size()
        .reset_index(name = "ttl")
)

(ggplot(status_counts, aes("filing_date", "ttl", fill = "bail_status"))
  + geom_col()
  + theme(axis_text_x = element_text(angle = 45, hjust = 1))
)


# + tags=["hide-input"]
type_counts = ncf[["filing_date", "bail_type"]].value_counts().reset_index(name = "n")

(
    ggplot(type_counts, aes('filing_date', 'n', fill = 'bail_type')) +
    geom_col() +
    labs(title = "Docket Count by Day",
        subtitle = "Data since 2020-02-29",
        x = "Date",
        y = "Docket Count",
        fill = "Bail Type") +
    theme(axis_text_x = element_text(angle = 45)) +
    theme_light()
)
# -

# ### Missing days

# + tags=["hide-input"]
data_dates = pd.date_range("2020-03-01", "today")

pd.DataFrame(
    {'date': data_dates[~data_dates.isin(status_counts.filing_date)]
    })
