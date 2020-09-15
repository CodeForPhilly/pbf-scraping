# +
import pandas as pd
import dotenv

dotenv.load_dotenv()
# -

# ## Transforming Original data -> new
#
# * rename represented -> represented_by
# * address split to city, state, zip_code
# * original missing: bail_date, bail_time, filing_time, in_custody
# * new data missing: id column (for anonymizing; fine to exclude)
#
# overlapping data: July 1, July 6, July 7

df_orig = pd.read_csv("https://raw.githubusercontent.com/CodeForPhilly/pbf-analysis/master/Data/0c_distinct_dockets.csv")

# +
from sqlalchemy import create_engine
import os

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
# -

df_new = pd.read_sql("""
SELECT *
FROM new_criminal_filings
""", engine)

set(df_new.columns) - set(df_orig.columns)

set(df_orig.columns) - set(df_new.columns)

# ### Extract city, state, zipcode

# +
# Regex over address like: Philadelphia, PA 19141
# However, sometimes the zipcode is missing: Philadelphia, PA
# Also note, zipcode may have form 191120004 (no hyphens)
address = df_orig.address.str.extract("(.*?), ([A-Z]+) ?([0-9]+)?")
df_orig[["city", "state", "zip_code"]] = address

#df_orig[["address", "city", "state", "zip_code"]].head(100)
# -

# ### Rename represented_by, fill in missing columns as NA

# +
missing = ['bail_date', 'bail_time', 'in_custody']

out_col_order = ['age',
 'city',
 'state',
 'zip_code',
 'docket_number',
 'filing_date',
 'filing_time',
 'charge',
 'represented',
 'in_custody',
 'bail_status',
 'bail_date',
 'bail_time',
 'bail_type',
 'bail_amount',
 'outstanding_bail_amount']

filing_dt = df_orig.filing_date.astype("datetime64[ns]")

final = (df_orig
         .rename(columns = {
             "represented_by": "represented",
             "bail_status": "bail_type",
             "bail_type": "bail_status"
         })
         .drop(columns = ["id"])
         .assign(
             filing_date = filing_dt.dt.strftime("%m/%d/%Y"),
             filing_time = filing_dt.dt.time,
             **{k: pd.NA for k in missing}
         )
        )
# -

final[out_col_order].to_csv("output/pbf_analysis_distinct_dockets.csv", index = False)
