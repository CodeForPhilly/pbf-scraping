import pdfquery
import PyPDF2
#import textract
import re
import os
import argparse
import pandas as pd
import funcs_parse as funcs


def scrape_pdf(filename):
    """ 
    Scrapes the PDF, extracting text page by page with PyPDF2.
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
    
    #with open(os.path.splitext(filename)[0] + '_clean.txt', 'w') as f:
    #    f.write(text)
    
    return text


def clean_text(txt):
    """ 
    Cleans document text.
    Be careful about modifications. The regex in subsequent functions
    depends on certain elements such as newline characters being removed
    Parameters: 
        txt (string): Entire document as a string
    Returns: 
        txt: A cleaner version of the entire document which includes removal of
             headers, printed dates, and newline characters.
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
    This methodology relies heavily on regex and is extremely brittle. Testing must
    be thorough in order to account for differences in format.
    If the format of the court systems changes, we can expect this entire function to break.
    We start by identifying sections of the document, and then we use secondary pattern matching
    to extract specific elements.
    Parameters: 
        text (string): Cleaned document as a string
    Returns: 
        result: a dictionary of specific elements 
    """

    # Set RegEx patterns to first break the document into sections
    # note: recently made all strings raw - second half didn't used to be
    sectionPatterns = {'docket':    r"(?<=DOCKET)(.*?)(?=CASE INFORMATION)",
                       'caseinfo':  r"(?<=CASE INFORMATION)(.*?)(?=STATUS INFORMATION)",
                       'status':    r"(?<=STATUS INFORMATION)(.*?)(?=CALENDAR EVENTS)",
                       'calendar':  r"(?<=CALENDAR EVENTS)(.*?)(?=DEFENDANT INFORMATION)", 
                       'defendant': r"(?<=DEFENDANT INFORMATION)(.*?)(?=CASE PARTICIPANTS)",
                       'participants': r"(?<=CASE PARTICIPANTS)(.*?)(?=BAIL INFORMATION)",
                       'bailinfo':  r"(?<=BAIL INFORMATION)(.*?)(?=CHARGES)",
                       'charges':   r"(?<=CHARGES)(.*?)(?=DISPOSITION SENTENCING)",
                       'dispo':     r"(?<=DISPOSITION SENTENCING/PENALTIES)(.*?)(?=COMMONWEALTH INFORMATION)",
                       'contactinfo': r"(?<=COMMONWEALTH INFORMATION)(.*?)(?=ENTRIES)",
                       'entries':   r"(?<=ENTRIES)(.*)"}

    # Loop through RegEx patterns to break document into sections
    sections = {}
    for key, value in sectionPatterns.items():
        section = re.findall(value, text, re.DOTALL)
        assert section != [], "Section '{0}' not found".format(key)
        sections[key] = section[0].strip()

    # Create PDFQuery object, in addition to given text, for scraping from columns
    pages_charges = funcs.find_pages(filename,'Statute Description')
    pages_bail_set = funcs.find_pages(filename,'Filed By')
    pages_bail_info = funcs.find_pages(filename,'Bail Posting Status')
    pages_zip = funcs.find_pages(filename,'Zip:')
    pages = list(set(pages_charges + pages_bail_set + pages_bail_info + pages_zip))
    pdfObj = pdfquery.PDFQuery(filename)
    pdfObj.load(pages)

    # Extract specific fields using regexp:
    # docket number, arrest date, case statuus, arresting officer, attorney, 
    # DOB, prelim hearing
    parsedData = {}
    parsePatterns = {'docket_no':   r"MC-\d{2}-CR-\d{7}-\d{4}",
                     'dob':         r"Date Of Birth:(.*?)City",
                     'arrest_dt':   r"Arrest Date:(.*?)(?<=\d{2}\/\d{2}\/\d{4})",
                     'case_status': r"Case Status:(.*?)Arrest",
                     'arresting_officer': r"Arresting Officer :(.*?)Complaint\/Incident"}
    
    for key, value in parsePatterns.items():
        try:
            parsedData[key] = re.findall(value, text, re.DOTALL)[0]
        except:
            print('Warning: could not parse {0}'.format(key))
            parsedData[key] = ''
    '''
    pattern_docket = r"MC-\d{2}-CR-\d{7}-\d{4}"
    parsedData['docket_no'] = re.findall(pattern_docket, text, re.DOTALL)[0]
    pattern_dob = r"Date Of Birth:(.*?)City"
    parsedData['dob'] = re.findall(pattern_dob, sections['defendant'], re.DOTALL)[0].strip()
    pattern_arrestdt = r"Arrest Date:(.*?)(?<=\d{2}\/\d{2}\/\d{4})"
    parsedData['arrest_dt'] = re.findall(pattern_arrestdt, sections['status'], re.DOTALL)[0]
    pattern_status = r"Case Status:(.*?)Arrest"
    parsedData['case_status'] = re.findall(pattern_status, sections['status'], re.DOTALL)[0]
    pattern_officer = r"Arresting Officer :(.*?)Complaint\/Incident"
    parsedData['arresting_officer'] = re.findall(pattern_officer, sections['caseinfo'], re.DOTALL)[0].strip()

    '''
    # Change this to extract public/private/court appointed rather than specific attorney?
    pattern_atty = r"(?<=ATTORNEY INFORMATION Name:)(.*?)(?=\d|Supreme)"
    data_attorney = re.findall(pattern_atty, sections['contactinfo'], re.DOTALL)
    if len(data_attorney) > 0:
        data_attorney = data_attorney[0]
        attorney_match = re.search(r"(Public|Private|Court Appointed)", data_attorney)
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
    pattern_prelim = r"(?<=Calendar Event Type )(.*?)(?=Scheduled)"
    prelim = re.findall(pattern_prelim, sections['calendar'], re.DOTALL)
    parsedData['prelim_hearing_dt'] = re.findall(r"\d{2}\/\d{2}\/\d{4}", str(prelim))[0]
    parsedData['prelim_hearing_time'] = re.findall(r"((1[0-2]|0?[1-9]):([0-5][0-9]) ?([AaPp][Mm]))", str(prelim))[0][0]

    # Extract specific fields using pdfquery: 
    # bail info, charges, zip, 
    parsedData['offenses'],parsedData['offense_date'],parsedData['statute'] = funcs.get_charges(pdfObj, pages_charges)
    parsedData['zip'] = funcs.get_zip(pdfObj, pages_zip)
    parsedData['bail_set_by'] = funcs.get_bail_set(pdfObj,pages_bail_set)
    parsedData['bail_amount'],parsedData['bail_paid'],parsedData['bail_date'],parsedData['bail_type'] = funcs.get_bail_info(pdfObj, pages_bail_info)

    ###  Uncomment to print a section during development
    ###  so we can build RegEx using online tools because RegEx is hard
    ###  https://regex101.com/r/12KSAf/1/
    
    return parsedData


def main(folder, output_name):
    ''' Test docket parsing '''

    parsed_results = []
    countAll = 0
    countFailed = 0
    for i, file in enumerate(os.listdir(folder)):
        countAll += 1
        try:
            print(i)
            text = scrape_pdf(folder+file)
            if text != '':
                data = parse_pdf(folder+file,text)
                #for key, value in data.items():
                #    print("{0}:\t {1}".format(key, value))
                parsed_results.append(data)
        except:
            print('Failed: {0}'.format(file))
            countFailed += 1
    print('{0}/{1} failed'.format(countFailed, countAll))

    final = pd.DataFrame(parsed_results)
    final.to_csv(output_name+'.csv', index=False)


if __name__ == "__main__":
    #cwd = os.path.join(os.path.dirname(__file__), '\tmp\dockets\sample')
    cwd = '/home/notchia/pbf-scraping/analyses/full_dockets/tmp/dockets/sample/'
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('-p','--path_folder', default=cwd,
                        help='Path to folder with PDFs')
    parser.add_argument('-o','--output_name', default='output',
                        help='Path to folder with PDFs')

    args = parser.parse_args()
    main(args.path_folder,args.output_name)

