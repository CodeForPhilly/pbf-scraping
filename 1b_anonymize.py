import sys
import pandas as pd
from pathlib import Path

fname, out_fname = sys.argv[1:3]


(pd.read_csv(fname)
   .drop(columns = "Defendant Name")
   .to_csv(out_fname, index = False)
)

