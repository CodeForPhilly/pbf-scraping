# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.3'
#       jupytext_version: 0.8.6
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# # Scraping for the Philadelphia Bail Bond
#
# This code will scrape data from the Philadelphia Courts, cleans the data, and outputs a CSV file. Future implementation is to have it check pages on its own, but for now manual entry of end page is necessary.

# ## Import Libraries

from bs4 import BeautifulSoup
import requests
import pandas as pd
import re
import argh

from datetime import date


PAGE_URL = "https://www.courts.phila.gov/NewCriminalFilings/date/default.aspx"


@argh.arg("--record-date", help = "Date of records to parse (must be within last 7 days)")
@argh.arg("--out", help = "Name of a file for resulting CSV.")
def main(record_date = None, out = None):
    """Scrape data from the Philadelphia Courts, clean, and output a CSV file.

    """

    if record_date is None:
        record_date = str(date.today())

    # This list will hold the scraped data from each page
    scraped_list_per_page = []
    # The current page is 1 and the end page as of now is 3 (this needs to be manually checked)
    curr_page_num, end_page = (1,3)
    # Starting at the current page and stopping at the last page of the website
    for curr_page_num in range(end_page):
        # Take the current page number and increament it each iteration
        curr_page_num = 1 + curr_page_num
        # The current webpage stores up to 24 criminal files and we are going through each page by updating the page number in the format
        params = {
                "search": record_date,
                "page": curr_page_num
                }
        # Then get the HTML file of the page as text
        source = requests.get(PAGE_URL, params = params).text
        # Then create a BeautifulSoup object of the text, this makes pulling data out of HTML files easier
        # To learn more about it read here (https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
        soup = BeautifulSoup(source)
        # After inspecting the source code I noticed the criminal files were listed under this specific div tag
        # The findAll function will grab each criminal file from that page
        list_of_criminal_filings = soup.findAll("div", {"class": "well well-sm"})
        # Then pass the list of all criminal fiilings into the extract_attributes function
        # After the extract_attributes function completes it will return a list of that whole page's scraped criminal
        # filings and then it will continue to the next page and at the end we will have one complete joined list
        scraped_list_per_page = (extract_attributes(list_of_criminal_filings)) + scraped_list_per_page
    # The joined list will then be passed into the create_csv function and converted to CSV
    create_csv(out, scraped_list_per_page)

def extract_attributes(list_of_criminal_filings):
    list_of_criminal_file_scraped = []
    # For each criminal file in the list of criminal filings pass it into the scrape_and_store function
    # Then afterwards return everything to main and it will repeat this cycle for the amount of pages
    for criminal_file in list_of_criminal_filings:
        criminal_file_scraped = scrape_and_store(criminal_file.text)
        list_of_criminal_file_scraped.append(criminal_file_scraped)
    return list_of_criminal_file_scraped

# This is just regex functions that helped me clean the data you can read more about regex here (https://docs.python.org/3/library/re.html)
def scrape_and_store(text):
    hold = text.splitlines()
    defendant_name = re.split('Name (.*?)', hold[3])[-1]
    age = re.split('Age (.*?)', hold[4])[-1]
    address = hold[6]
    city = re.split('\t ', address.split(',')[0])[1]
    state = re.split(" (.*?) ", re.split(",", address)[1])[1]
    zip_code = re.split(" (.*?) ", re.split(",", address)[1])[2]
    docket_number = re.split("Number (.*?)", hold[11])[2]
    filing = re.split(" ", hold[12])
    filing_date = filing[2]
    filing_time = " ".join(filing[3:5])
    charge = re.split("Charge ", hold[13])[1]
    represented = hold[15].strip()
    in_custody = hold[16]
    if len(in_custody) != 1:
        try:
            in_custody = re.split("Custody (.*?)", in_custody)[2]
        except IndexError as error:
            in_custody = ""
    bail_status = re.split("\t(.*?)", hold[-10])[-1]
    bail_datetime = re.split(" ", hold[-9])
    bail_date = bail_datetime[2]
    bail_time = " ".join(bail_datetime[3:5])
    bail_type = re.split(": (.*?)", hold[-8])[-1]
    bail_amount = re.split(": (.*?)", hold[-7])[-1]
    outstanding_bail_amt = re.split(" ", hold[-6])[-1]
    # Return a list of all the attributes
    return [defendant_name, age, city, state, zip_code, docket_number, filing_date, filing_time, charge, represented, in_custody, bail_status, bail_date, bail_time, bail_type, bail_amount, outstanding_bail_amt]

# This function will make the list of lists into a CSV file with Pandas
def create_csv(fname, list_of_criminal_file_scraped):
    df = pd.DataFrame(list_of_criminal_file_scraped)
    df.to_csv(fname, index=False, header=["Defendant Name", "Age", "City", "State", "Zip Code", "Docket Number", "Filing Date", "Filing Time", "Charge", "Represented", "In Custody", "Bail Status", "Bail Date", "Bail Time", "Bail Type", "Bail Amount", "Outstanding Bail Amount"])

if __name__ == "__main__":
    argh.dispatch_command(main)
