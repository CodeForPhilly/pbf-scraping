# +
import pandas as pd
import argh
import datetime
import os
import glob
import sys

from siuba import _
from siuba.siu import symbolic_dispatch

file_name = sys.argv[1]


# +
def clean_up_money(x):
    no_dollar_sign = x[1:len(x) - 3]
    return no_dollar_sign.replace(',', '')

@symbolic_dispatch
def row_template(df, s, **kwargs):
    """Apply a string template to each row of data. Allows _ to stand in for data."""
    return df.apply(lambda ser: s.format(**ser, **kwargs), axis = 1)


# +
# Will examine two forms of data: raw cases and cash bail cases
df = pd.read_csv(file_name).rename(columns = lambda s: s.lower().replace(" ", "_"))

cash_bail = (df
    .siu_filter(_["bail_type"].str.contains("Monetary"))
)

# +
# Now some stats on the cases where cash bail was set

bail_types = pd.DataFrame({
    "bail_type": ["Monetary", "ROR", "Unsecured", "Denied"],
    "order": range(4)
    })

bail_type_agg = (
  df
  # ensure denied is included in bail type
  .siu_mutate(bail_type = _["bail_status"].where(_["bail_status"] == "Denied", _["bail_type"]))
  .siu_count(_["bail_type"])
  # ensure bail types not in data are still reported
  .merge(bail_types, on = "bail_type", how = "outer")
  .siu_mutate(
      n = _.n.fillna(0).astype(int),
      pct = (_.n / _.n.sum()),
      text = row_template(_, "{bail_type}: {pct:.0%} ({n} cases)")
  )
  .siu_arrange(_.order)
)

text_bail_type = bail_type_agg.text.str.cat(sep = "\n")

# +
# What percent of cash bail cases have bail Posted?

template = """
Of the {ttl:.0f} cases where bail was set:
-{ttl_posted:.0f} were posted
-in {pct_defender:.0%} ({ttl_defender:.0f} cases) a public defender was assigned due to indigence
"""

cash_bail_status = (
  cash_bail
  .siu_summarize(
      ttl = _.shape[0],
      ttl_posted = _["bail_status"].eq("Posted").sum(),
      ttl_defender = _["represented"].str.contains("Defender Assoc").sum()
  )
  .siu_mutate(
      pct_posted = _.ttl_posted / _.ttl,      
      pct_defender =  _.ttl_defender / _.ttl,
      text = row_template(_, template)
  )
)

text_cash_bail = cash_bail_status.text[0]

# +
# Descriptive statistics for bail amount

amount_cleaned = cash_bail["bail_amount"].apply(clean_up_money).astype(int)

amount_agg = amount_cleaned.describe()
needed = (amount_agg / 10).rename(lambda x: x + "_needed")

text_amount = """\
Highest cash bail: {max} ({max_needed} needed to post bail)
Lowest cash bail: {min} ({min_needed} needed to post bail)
Average bail issued: {mean} ({mean_needed} needed to post bail)
Total cash bail issued: ${ttl:,.0f} (${ttl_10:,.0f} needed to post bail for all)\
""".format(
    **amount_agg.apply("${:,.0f}".format),
    **needed.apply("${:,.0f}".format),
    ttl = amount_cleaned.sum(),
    ttl_10 = amount_cleaned.sum() / 10
)

# +
# Display the dates we're summarizing over
min_date, max_date = pd.to_datetime(df["bail_date"], format = '%m/%d/%Y').agg(["min", "max"])

if min_date == max_date:
    str_date = min_date.strftime("%B %d, %Y")
else:
    str_date = "%s to %s"%(min_date.strftime("%B %d, %Y"), max_date.strftime("%B %d, %Y"))

# Chuck those dates in to the header
header = """\
Philadelphia | {date}
Total # Cases Arraigned: {ttl}
""".format(date = str_date, ttl = len(df))

print("\n".join([header, text_bail_type, text_cash_bail, text_amount]))
