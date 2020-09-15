import pandas as pd
df_orig = pd.read_csv("data_adam_deidentified.csv")

# ### Extract city, state, zipcode

# Regex over address like: Philadelphia, PA 19141
# However, sometimes the zipcode is missing: Philadelphia, PA
# Also note, zipcode may have form 191120004 (no hyphens)
address = df_orig.address.str.extract("(.*?), ([A-Z]+) ?([0-9]+)?")
df_orig[["city", "state", "zip_code"]] = address

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
         # drop a few early days overlapping with pbf-analysis
         .loc[lambda d: d.filing_date >= "2020-06-17"]
         # drop a fwe late days overlapping with current scraped data
         .loc[lambda d: d.filing_date < "2020-07-01"]
         .assign(
             filing_date = filing_dt.dt.strftime("%m/%d/%Y"),
             filing_time = filing_dt.dt.time,
             **{k: pd.NA for k in missing}
         )
        )


# -

final.loc[:, out_col_order].to_csv("output/data_adam.csv", index = False)
