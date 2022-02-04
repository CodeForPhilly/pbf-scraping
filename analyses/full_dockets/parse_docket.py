import re
import os
import argh
import pandas as pd
import pdfquery
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfpage import PDFPage
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from io import StringIO
import funcs_parse as funcs


def scrape_and_parse_pdf(filepath):
    """ Extract fields from docket file.
        Parameters:
            filepath (path): full path to PDF file
        Returns:
            parsedData (dictionary): column_name:key_value pairs
        """

    text = scrape_pdf(filepath)
    text = clean_text(text)

    parsedData = parse_pdf(filepath, text)

    return parsedData


def scrape_pdf(filepath):
    """
    Scrapes the PDF, extracting text page by page

    Parameters:
        filename (string): path to the filename.pdf
    Returns:
        text (string): entire document
    """

    rsrcmgr = PDFResourceManager()
    sio = StringIO()
    codec = 'utf-8'
    laparams = LAParams()
    device = TextConverter(rsrcmgr, sio, codec=codec, laparams=laparams)
    interpreter = PDFPageInterpreter(rsrcmgr, device)

    try:
        with open(filepath, 'rb') as fp:
            pages = PDFPage.get_pages(fp, check_extractable=True)
            for page in pages:
                interpreter.process_page(page)
        text = sio.getvalue()
    except:
        print("Warning: skipping empty/unopenable file {0}".format(os.path.basename(filepath)))
        text = ''

    device.close()
    sio.close()

    return text


def clean_text(txt):
    """
    Cleans document text according to some basic rules.

    Be careful about modifications. The regex in subsequent functions
    depends on certain elements such as newline characters being removed
    Parameters:
        txt (string): Entire document as a string
    Returns:
        txt (string): A cleaner version of the entire document
    """

    if txt == '':
        return txt

    # Replace unnecessary text with space (for newline) or empty char
    replacements = [('\n', ' '),
                    ('CPCMS 9082', ''),
                    ('MUNICIPAL COURT OF PHILADELPHIA COUNTY', '')]
    for k, v in replacements:
        txt = txt.replace(k, v)

    # Replace unnecessary text patterns with empty char
    substitutions = [r"Recent entries made(.*?)Section 9183",
                     r"Printed:([\s]*)\d{2}([\s]*)\/\d{2}\/\d{4}",
                     r"Page \d+ of \d+"]
    for pattern in substitutions:
        txt = re.sub(pattern, '', txt)

    # Replace any whitespace greater than one space with just one space
    txt = re.sub(r"\s+", ' ', txt)

    return txt


def parse_pdf(filename, text):
    """
    Parses specific elements from the string.

    This methodology relies heavily on regex and is extremely brittle. Testing
    must be thorough in order to account for differences in format. If the
    format of the court systems changes, we can expect this entire function
    to break. We start by identifying sections of the document, and then we use
    secondary pattern matching to extract specific elements.

    For easier regex debugging, see https://regex101.com/r/12KSAf/1/

    Parameters:
        text (string): Cleaned document as a string
    Returns:
        parsedData (dictionary): column heading:item value pairs for parsed items
    """

    parsedData = {}

    # Return empty dictionary if no text provided
    if text == '':
        return {}

    # Extract some fields directly using regexp
    parsePatterns = {'docket_no': r"(?:MC|CP)-\d{2}-CR-\d{7}-\d{4}"}

    for key, value in parsePatterns.items():
        try:
            parsedData[key] = re.findall(value, text, re.DOTALL)[0].strip()
            print(parsedData[key])

        except:
            print('Warning: could not parse {0}'.format(key))
            parsedData[key] = ''

    # Extract some fields using regexp plus further parsing:
    specialPatterns = {'attorney': r"(?<=ATTORNEY INFORMATION)(.*?)(?=\d|Supreme)",
                       'attorney_type': r"(Public|Private|Court Appointed)"}
    badPrefixes = ["Name:", "Philadelphia County District Attorney's Office Prosecutor"]

    data_attorney = re.findall(specialPatterns['attorney'], text, re.DOTALL)
    if len(data_attorney) > 0:  # skips empty space also   
        data_attorney = data_attorney[0].strip()
        for prefix in badPrefixes:
            if data_attorney.startswith(prefix):
                data_attorney = data_attorney[len(prefix):].strip()
        if data_attorney.startswith("Sequence Number"):
            print('Warning: could not parse attorney')
            data_attorney = ''

        attorney_match = re.search(specialPatterns['attorney_type'], data_attorney)
        if attorney_match:
            attorney_type = attorney_match.group(0).strip()
            attorney_information = data_attorney.split(attorney_type)[0].strip()
        else:
            if len(data_attorney) != 0:
                # In some cases, no attorney information is listed (len(data_attorney) == 0)
                # but in that case no warning should be raised
                print('Warning: could not parse {0}'.format('attorney type'))
            attorney_type = ''
            attorney_information = data_attorney.strip()
        parsedData['attorney'] = attorney_information
        parsedData['attorney_type'] = attorney_type
    else:
        print('Warning: could not parse attorney')
        parsedData['attorney'] = ''
        parsedData['attorney_type'] = ''

    # Extract remaining fields using pdfquery:
    # Create PDFQuery object, in addition to given text, for scraping from columns
    pages_charges = funcs.find_pages(filename, 'Statute Description')
    pages_bail_set = funcs.find_pages(filename, 'Filed By')
    pages_bail_info = funcs.find_pages(filename, 'Bail Posting Status')
    pages_dob = funcs.find_pages(filename, 'Date Of Birth:')
    pages_zip = funcs.find_pages(filename, 'Zip:')
    pages_arresting_officer = funcs.find_pages(filename, 'Arresting Officer:')
    pages_status = funcs.find_pages(filename, 'Case Status')
    pages_prelim_hearing = funcs.find_pages(filename, 'Event Type')

    pages = list(set(
        pages_charges + pages_bail_set + pages_bail_info + pages_dob + pages_zip + pages_arresting_officer + pages_status + pages_prelim_hearing))
    pdfObj = pdfquery.PDFQuery(filename)
    pdfObj.load(pages)

    # Use PDFQuery object to find location on page where the information appears - non-bail info
    parsedData['offenses'], parsedData['offense_date'], parsedData['statute'], parsedData[
        'offense_type'] = funcs.get_charges(pdfObj, pages_charges)
    parsedData['bail_set_by'] = funcs.get_magistrate(pdfObj, pages_bail_set)
    parsedData['dob'] = funcs.get_dob(pdfObj, pages_dob)
    parsedData['zip'] = funcs.get_zip(pdfObj, pages_zip)
    parsedData['arresting_officer'] = funcs.get_arresting_officer(pdfObj, pages_arresting_officer)
    parsedData['case_status'], parsedData['arrest_dt'] = funcs.get_status(pdfObj, pages_status)

    # Use PDFQuery object to find location on page where the information appears - bail info
    bail_info_list, bail_first_posted, bail_first_posted_date, bail_posted_list = funcs.get_bail_info(pdfObj, pages_bail_info)
    first_bail_info = bail_info_list[0]
    parsedData['bail_date'] = first_bail_info['bail_date']
    parsedData['bail_type'] = first_bail_info['bail_type']
    parsedData['bail_percentage'] = first_bail_info['bail_percentage']
    parsedData['bail_amount'] = first_bail_info['bail_amount']
    parsedData['bail_paid'] = bail_first_posted
    parsedData['bail_paid_date'] = bail_first_posted_date
    parsedData['bail_info_list'] = bail_info_list
    parsedData['bail_posted_list'] = bail_posted_list

    #CP dockets have a different method of presenting prelim hearing information that is not currently supported by this script.
    if 'CP-51' in filename:
        parsedData['prelim_hearing_dt'], parsedData['prelim_hearing_time'] = ('CP Docket Not Supported', 'CP Docket Not Supported')
    else:
      parsedData['prelim_hearing_dt'], parsedData['prelim_hearing_time'] = funcs.get_prelim_hearing(pdfObj,
                                                                                                  pages_prelim_hearing)

    return parsedData


@argh.arg("--testdir", help="Directory where test files are located")
@argh.arg("--outfile", help="Filename for output file [outfile].csv")
@argh.arg("--failed", help="Filename for failed file [failed].csv")
def test_scrape_and_parse(testdir='', outfile='docket_test', failed='failed'):
    """ Test scrape_pdf and parse_pdf.

        TODO: generate test set of pdf:csv pairs and update this function to
        automatically compare the parsed output to the validated output, instead
        of dumping into csv for manual checking"""

    f_failed = open('{0}.txt'.format(failed), "w")

    if testdir == '':
        cwd = os.path.dirname(__file__)
        testdir = os.path.join(cwd, 'tmp/dockets/')
        savedir = os.path.join(cwd, 'tmp/')
    else:
        savedir = testdir

    parsedDockets = []
    countAll = 0
    countFailed = 0
    for i, file in enumerate(sorted(os.listdir(testdir))):
        countAll += 1
        try:
            print('{0}\t {1}'.format(i, file))
            data = scrape_and_parse_pdf(os.path.join(testdir, file))
            if data != {}:
                parsedDockets.append(data)
        except:
            f_failed.write('{}   FAILED\n'.format(file))
            print('Failed: {0}'.format(file))
            countFailed += 1
    print('{0}/{1} failed'.format(countFailed, countAll))

    f_failed.close()

    final = pd.DataFrame(parsedDockets)
    final.to_csv(os.path.join(savedir, '{0}.csv'.format(outfile)), index=False)


if __name__ == "__main__":
    argh.dispatch_command(test_scrape_and_parse)
