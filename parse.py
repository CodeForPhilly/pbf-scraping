import pandas as pd
import argh
import datetime
import os
import glob

def main():
    today = datetime.date.today()

    yesterday = today - datetime.timedelta(days=1)

    file_name = glob.glob("./output/*.csv")[0]
    df = pd.read_csv(file_name)

    #Total cases is just number of rows in the csv
    total_cases = len(df)

    #Get all cases where cash bail was set
    all_cash_bail = df[df['Bail Type'].fillna("").str.contains('Monetary')]
    total_cash_bail = (len(all_cash_bail))
    percentage_cash_bail = int((total_cash_bail / total_cases) * 100)

    #Get all ROR cases
    all_ror = df[df['Bail Type'].fillna("").str.contains('ROR')]
    total_ror = (len(all_ror))
    percentage_ror  = int((total_ror / total_cases) * 100)

    #Get all Unsecured cases
    all_unsecured = df[df['Bail Type'].fillna("").str.contains('Unsecured')]
    total_unsecured = (len(all_unsecured))
    percentage_unsecured  = int((total_unsecured / total_cases) * 100)

    # Get all ROR cases
    all_denied = df[df['Bail Type'].fillna("").str.contains('Denied')]
    total_denied = (len(all_denied))
    percentage_denied = int((total_denied / total_cases) * 100)

    ##Now some stats on the cases where cash bail was set

    #Get all where bail was posted
    all_posted = all_cash_bail[all_cash_bail['Bail Status'].fillna("").str.contains('Posted')]
    total_posted = len(all_posted)
    percentage_posted = int((total_posted / total_cash_bail) * 100)

    #Get all with Public Defender
    all_defenders = all_cash_bail[all_cash_bail['Represented'].str.contains('Defender Association', na=False)]
    total_defenders = len(all_defenders)
    percentage_defenders = int((total_defenders / total_cash_bail) * 100)

    #Get just bail amounts
    all_cash_bail_amounts = all_cash_bail['Bail Amount']
    all_cash_bail_amounts_clean = all_cash_bail_amounts.apply(clean_up_money)
    values = all_cash_bail_amounts_clean.astype(int)
    list = values.sort_values().values

    #min bail
    min_bail = list[0]
    min_needed_to_post = int(min_bail / 10)
    min_bail_formatted = "${:,}".format(min_bail)
    min_needed_to_post_formatted = "${:,}".format(min_needed_to_post)

    #max bail
    max_bail = list[-1]
    max_needed_to_post = int(max_bail / 10)
    max_bail_formatted = "${:,}".format(max_bail)
    max_needed_to_post_formatted = "${:,}".format(max_needed_to_post)

    #average bail
    avg_bail = int(sum(list) / len(list))
    avg_needed_to_post = int(avg_bail / 10)
    avg_bail_formatted = "${:,}".format(avg_bail)
    avg_needed_to_post_formatted = "${:,}".format(avg_needed_to_post)

    #total bail
    total_bail = sum(list)
    total_needed_to_post = int(total_bail / 10)
    total_bail_formatted = "${:,}".format(total_bail)
    total_needed_to_post_formatted = "${:,}".format(total_needed_to_post)

    #construct the message
    total = 'Total # Cases Arraigned: %s' % total_cases
    cash_bail = 'Cash bail:  {0}%  ({1} cases)*'.format(percentage_cash_bail, total_cash_bail)
    ror = 'ROR: {0}% ({1} cases)'.format(percentage_ror, total_ror)
    unsecured = 'Unsecured: {0}% ({1} cases)'.format(percentage_unsecured, total_unsecured)
    denied = 'Denied: {0}% ({1} cases)'.format(percentage_denied, total_denied)
    cases_bail_set = 'Of the {0} cases where bail was set:'.format(total_cash_bail)
    number_posted = '-{0} were posted'.format(total_posted)
    public_defender = '-in {0}% ({1} cases) a public defender was assigned due to indigence'.format(percentage_defenders,
                                                                                                   total_defenders)
    highest = 'Highest cash bail: {0} ({1} needed to post bail)'.format(max_bail_formatted, max_needed_to_post_formatted)
    lowest = 'Lowest cash bail: {0} ({1} needed to post bail)'.format(min_bail_formatted, min_needed_to_post_formatted)
    average = 'Average bail issued: {0} ({1} needed to post bail)'.format(avg_bail_formatted, avg_needed_to_post_formatted)
    final_sum = 'Total cash bail issued: {0} ({1} needed to post bail for all)'.format(total_bail_formatted,
                                                                                           total_needed_to_post_formatted)

    yesterdayFormatted = yesterday.strftime("%B %d, %Y")
    topPart = 'Philadelphia | {0}'.format(yesterdayFormatted)

    MESSAGE = topPart + "\n" + total + "\n" + "\n" + cash_bail + "\n" + ror + "\n" + unsecured + "\n" + denied + "\n" + "\n" + cases_bail_set + "\n" + number_posted + "\n" + public_defender + "\n" + "\n" + highest + "\n" + lowest + "\n" + average + "\n" + final_sum
    print(MESSAGE)

def clean_up_money(x):
    no_dollar_sign = x[1:len(x) - 3]
    return no_dollar_sign.replace(',', '')


main()
