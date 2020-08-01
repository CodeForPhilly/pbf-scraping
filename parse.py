import datetime
import glob
import os
from textwrap import dedent
from typing import Dict, List, Union

import pandas as pd
from pandas import DataFrame, Series


def pct_by_bail_type(df: DataFrame) -> Series:
    return df["Bail Type"].value_counts().apply(lambda x: int(x / len(df) * 100))


def total_by_bail_type(df: DataFrame) -> Series:
    return df["Bail Type"].value_counts()


def money_str_as_int(v: str) -> int:
    return int(float(v.replace(",", "").replace("$", "")))


def needed_to_post(v: int) -> int:
    return int(v / 10)


def load_df(path: Union[str, None] = None) -> DataFrame:
    if path is None:
        path = glob.glob("./output/*.csv")[0]
    return pd.read_csv(path, parse_dates=True)


def construct_message(df: DataFrame) -> str:
    pct_bail_type = pct_by_bail_type(df)
    percentage_cash_bail = pct_bail_type.get("Monetary", 0)
    percentage_ror = pct_bail_type.get("ROR", 0)
    percentage_unsecured = pct_bail_type.get("Unsecured", 0)
    percentage_denied = pct_bail_type.get("Denied", 0)

    total_bail_type = total_by_bail_type(df)
    total_cash_bail = total_bail_type.get("Monetary", 0)
    total_ror = total_bail_type.get("ROR", 0)
    total_unsecured = total_bail_type.get("Unsecured", 0)
    total_denied = total_bail_type.get("Denied", 0)

    # Get all cases where cash bail was set
    all_cash_bail = df[df["Bail Type"] == "Monetary"]

    # total posted bail
    total_posted = len(all_cash_bail[all_cash_bail["Bail Status"] == "Posted"])

    # Get all with Public Defender
    all_defenders = all_cash_bail[
        all_cash_bail["Represented"].str.contains("Defender Association", na=False)
    ]
    total_defenders = len(all_defenders)
    percentage_defenders = int((total_defenders / total_cash_bail) * 100)

    # Bail amounts
    cash_bail_amounts = all_cash_bail["Bail Amount"].apply(money_str_as_int)
    min_bail = cash_bail_amounts.min()
    max_bail = cash_bail_amounts.max()
    average_bail = int(cash_bail_amounts.mean())
    total_bail = cash_bail_amounts.sum()

    yesterday = datetime.date.today() - datetime.timedelta(days=1)
    yesterday_formatted = yesterday.strftime("%B %d, %Y")

    # construct the message
    MESSAGE = f"""\
    Philadelphia | {yesterday_formatted}
    Total # Cases Arraigned: {len(df)}

    Cash bail: {percentage_cash_bail}%  ({total_cash_bail} cases)*
    ROR: {percentage_ror}% ({total_ror} cases)
    Unsecured: {percentage_unsecured}% ({total_unsecured} cases)
    Denied: {percentage_denied}% ({total_denied} cases)

    Of the {total_cash_bail} cases where bail was set:
    -{total_posted} were posted
    -in {percentage_defenders}% ({total_defenders} cases) a public defender was assigned due to indigence

    Highest cash bail: ${max_bail:,} ({needed_to_post(max_bail):,} needed to post bail)
    Lowest cash bail: ${min_bail:,} ({needed_to_post(min_bail):,} needed to post bail)
    Average bail issued: ${average_bail:,} ({needed_to_post(average_bail):,} needed to post bail)
    Total cash bail issued: ${total_bail:,} ({needed_to_post(total_bail):,} needed to post bail for all)"""
    return dedent(MESSAGE)


def main() -> None:
    df = load_df()
    message = construct_message(df)
    print(message)


if __name__ == "__main__":
    main()
