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

import csv
from datetime import date
from typing import Dict, Generator, List, Set, Tuple, Union

import argh
import requests
from bs4 import BeautifulSoup
from bs4 import element as BsElement

BASE_URL = "https://www.courts.phila.gov/NewCriminalFilings/date/default.aspx"


def get_page(date: str, page: int = 1) -> BeautifulSoup:
    params: Dict[str, Union[int, str]] = {"search": date, "page": page}
    response = requests.get(BASE_URL, params=params)
    response.raise_for_status()
    return BeautifulSoup(response.content, "html.parser")


class PageParser:
    def __init__(self, soup: BeautifulSoup) -> None:
        self.soup = soup

    @property
    def has_next_page(self) -> bool:
        page_nums = (
            anchor.text
            for anchor in self.soup.find("ul", {"class": "pagination"}).find_all("a")
        )
        # This is unicode character U+00BB / HTML entity &#187
        return "»" in page_nums

    def parse_filings(self) -> Generator[Dict[str, str], None, None]:
        """Return a generator of {heading: datum} dicts for each filing"""

        for filing in self.soup.find_all("div", {"class": "well well-sm"}):
            yield {header: data for header, data in self._parse_filing(filing)}

    def _parse_filing(
        self, filing: BsElement
    ) -> Generator[Tuple[str, str], None, None]:
        """Return a generator of (heading, datum) tuples for a filing

        Each filing in a div.well.well-sm tag, data is split into three p
        tags which map to the 3 columns of data on the page. Beautiful Soup can
        handle these p tags easily, but the HTML contained within doesn't lend
        itself to clean parsing.
        """
        for column in filing.find_all("p"):
            headers = [
                element.extract().text.strip(":")
                for element in column.find_all("strong")
            ]
            data = [
                datum for text in column.text.split("\n") if (datum := text.strip())
            ]
            for header, datum in zip(headers, data):
                yield header, datum


class Filings:
    def __init__(self) -> None:
        self.filings: List[Dict[str, str]] = []
        self.seen_headers: Set[str] = set()

    def append_filing(self, filing: Dict[str, str]) -> None:
        self.seen_headers = self.seen_headers.union(filing.keys())
        self.filings.append(filing)

    def to_csv(self, path: str) -> None:
        with open(path, "w", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=sorted(self.seen_headers))
            writer.writeheader()
            writer.writerows(self.filings)


@argh.arg(
    "--record-date",
    default=date.today().isoformat(),
    help="Date of records to parse (must be within last 7 days)",
)
@argh.arg("--out", default="output/filings.csv", help="Pathname for resulting CSV.")
def main(record_date=None, out=None) -> None:

    filings = Filings()

    page_num = 1
    while True:
        soup = get_page(record_date, page_num)
        page = PageParser(soup)
        for filing in page.parse_filings():
            filings.append_filing(filing)
        if not page.has_next_page:
            break
        page_num += 1

    filings.to_csv(out)


if __name__ == "__main__":
    argh.dispatch_command(main)
