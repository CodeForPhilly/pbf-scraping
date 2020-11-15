import pdfquery
import PyPDF2
import re
import os
import argparse
import pandas as pd
import funcs_parse as funcs


def scrape_pdf(filename):
    """ 
    Scrapes the PDF, extracting text page by page, then cleans output

    Parameters: 
        filename (string): path to the filename.pdf
    Returns: 
        text (string): entire document
    """
    
    fileObj = open(filename, 'rb')
    text = ""
    try:
        pdfReader = PyPDF2.PdfFileReader(fileObj)
    except:
        print("Warning: skipping invalid pdf {0}".format(os.path.basename(filename)))
        return text
    
    num_pages = pdfReader.numPages
    for i in range(num_pages):
        pageObj = pdfReader.getPage(i)
        text += pageObj.extractText()

    # clean based on some basic rules
    text = clean_text(text)
    
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
    parsePatterns = {'docket_no':   r"MC-\d{2}-CR-\d{7}-\d{4}",
                     'dob':     r"Date Of Birth:(.*?)City",
                     'arrest_date': r"Arrest Date:(.*?)(?<=\d{2}\/\d{2}\/\d{4})",
                     'case_status': r"Case Status:(.*?)Arrest",
                     'arresting_officer': r"Arresting Officer :(.*?)Complaint\/Incident"}
    for key, value in parsePatterns.items():
        try:
            parsedData[key] = re.findall(value, text, re.DOTALL)[0].strip()
        except:
            print('Warning: could not parse {0}'.format(key))
            parsedData[key] = ''

    # Extract some fields using regexp plus further parsing:
    specialPatterns = {'attorney': r"(?<=ATTORNEY INFORMATION Name:)(.*?)(?=\d|Supreme)",
                       'attorney_type': r"(Public|Private|Court Appointed)",
                       'prelim':  r"(?<=Calendar Event Type )(.*?)(?=Scheduled)",
                       'date':    r"\d{2}\/\d{2}\/\d{4}",
                       'time':    r"((1[0-2]|0?[1-9]):([0-5][0-9]) ?([AaPp][Mm]))"}    
    data_attorney = re.findall(specialPatterns['attorney'], text, re.DOTALL)
    if len(data_attorney) > 0:
        data_attorney = data_attorney[0]
        attorney_match = re.search(specialPatterns['attorney_type'], data_attorney)
        if attorney_match:
            attorney_type = attorney_match.group(0).strip()
            attorney_information = data_attorney.split(attorney_type)[0]
        else:
            attorney_type = ''
            attorney_information = data_attorney
        parsedData['attorney'] = attorney_information
        parsedData['attorney_type'] = attorney_type
    else:
        parsedData['attorney'] = ''
    # Note: though this is structured as if multiple events might be found, the
    # 'prelim' regex as defined will only find the first event. Is this the
    # intended behavior?
    prelim = re.findall(specialPatterns['prelim'], text, re.DOTALL)
    if len(prelim) > 0:
        parsedData['prelim_hearing_date'] = re.findall(specialPatterns['date'], str(prelim))[0]
        parsedData['prelim_hearing_time'] = re.findall(specialPatterns['time'], str(prelim))[0][0]
    else: 
        parsedData['prelim_hearing_date'] = ''
        parsedData['prelim_hearing_time'] = ''
        
    # Extract remaining fields using pdfquery: 
    # Create PDFQuery object, in addition to given text, for scraping from columns
    pages_charges = funcs.find_pages(filename,'Statute Description')
    pages_bail_set = funcs.find_pages(filename,'Filed By')
    pages_bail_info = funcs.find_pages(filename,'Bail Posting Status')
    pages_zip = funcs.find_pages(filename,'Zip:')
    pages = list(set(pages_charges + pages_bail_set + pages_bail_info + pages_zip))
    pdfObj = pdfquery.PDFQuery(filename)
    pdfObj.load(pages)
    # Use PDFQuery object to find location on page where the information appears
    parsedData['offenses'],parsedData['offense_date'],parsedData['statute'] = funcs.get_charges(pdfObj, pages_charges)
    parsedData['zip'] = funcs.get_zip(pdfObj, pages_zip)
    parsedData['bail_set_by'] = funcs.get_magistrate(pdfObj, pages_bail_set)
    parsedData['bail_amount'],parsedData['bail_paid'],parsedData['bail_date'],parsedData['bail_type'] = funcs.get_bail_info(pdfObj, pages_bail_info)
    
    return parsedData


def test_scrape_and_parse(folder, output_name):
    ''' Test scrape_pdf and parse_pdf.
    
        TODO: generate test set of pdf:csv pairs and update this function to
        automatically compare the parsed output to the validated output, instead
        of dumping into csv for manual checking'''

    parsed_results = []
    countAll = 0
    countFailed = 0
    for i, file in enumerate(sorted(os.listdir(folder))):
        countAll += 1
        try:
            print('{0}\t {1}'.format(i, file))
            text = scrape_pdf(folder+file)
            if text != '':
                data = parse_pdf(folder+file,text)
                parsed_results.append(data)
        except:
            print('Failed: {0}'.format(file))
            countFailed += 1
    print('{0}/{1} failed'.format(countFailed, countAll))

    final = pd.DataFrame(parsed_results)
    final.to_csv(output_name+'.csv', index=False)
    
    return


if __name__ == "__main__":
    cwd = os.path.split(os.path.abspath(__file__))[0]
    testdir = os.path.join(cwd, 'tmp/dockets/sample/')

    parser = argparse.ArgumentParser(description='')
    parser.add_argument('-p','--path_folder', default=testdir,
                        help='Path to folder with PDFs')
    parser.add_argument('-o','--output_name', default='output',
                        help='Path to folder with PDFs')

    args = parser.parse_args()
    test_scrape_and_parse(args.path_folder,args.output_name)

