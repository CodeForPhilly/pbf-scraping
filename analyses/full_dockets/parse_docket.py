import pdfquery
import PyPDF2
import re
import os
import numpy as np
import time
from funcs_parse import *
import argparse
import pandas as pd



def scrape_pdf(filename):
    """ 
    Scrapes the PDF
    Accepts a filename, and extracts the document data page by page by using
    PyPDF2
    Parameters: 
    filename (string): path to the filename.pdf
    Returns: 
    text: Entire document as a string.
    """
    FileObj = open(filename, 'rb')
    count = 0
    text = " "  
    pdfReader = PyPDF2.PdfFileReader(FileObj)
    num_pages = pdfReader.numPages
    while count < num_pages:
        pageObj = pdfReader.getPage(count)
        count+=1
        text += pageObj.extractText()
        # check if anything was actually returned
        if text != "":
            text = text
        # use OCR to pull text if none was returned
        else:
            text = textract.process(f, method='tesseract', language='eng')
    # clean based on some basic rules
    text = clean_text(text)
    return text
def clean_text(txt):
    """ 
    Cleans document text 
    Be careful about modifications. The regex in subsequent functions
    depends on certain elements such as newline characters being removed
    Parameters: 
    txt (string): Entire document as a string
    Returns: 
    txt: A cleaner version of the entire document which includes removal of
         headers, printed dates, and newline characters.
    """
    replacements = [('\n', ' '),
                   ('CPCMS 9082', ''),
                   ('MUNICIPAL COURT OF PHILADELPHIA COUNTY', '')]
    for k, v in replacements:
        txt = txt.replace(k, v)
    # patterns of extraneous text that we can get rid of
    disclaimer_pattern = r"Recent entries made(.*?)Section 9183"
    printed_pattern = r"Printed:(.*?)\d{2}\/\d{2}\/\d{4}"
    # replace with nothing
    for pattern in [disclaimer_pattern, printed_pattern]:
        txt = re.sub(pattern, '', txt)
    return txt


def parse_pdf(filename,text):
    """ 
    Parses specific elements from the string 
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
    # initialize result as an empty dictionary
    result = {}
    # Set RegEx patterns to first break the document into sections
    pat_docket = ('docket', r"(?<=DOCKET)(.*?)(?=CASE INFORMATION)")
    pat_caseinfo = ('caseinfo', r"(?<=CASE INFORMATION)(.*?)(?=STATUS INFORMATION)")
    pat_status = ('status', r"(?<=STATUS INFORMATION)(.*?)(?=CALENDAR EVENTS)")
    pat_calevents = ('calendar', r"(?<=CALENDAR EVENTS)(.*?)(?=DEFENDANT INFORMATION)") 
    pat_defendinfo = ('defendant', "(?<=DEFENDANT INFORMATION)(.*?)(?=CASE PARTICIPANTS)")
    pat_participants = ('participants', "(?<=CASE PARTICIPANTS)(.*?)(?=BAIL INFORMATION)")
    pat_bailinfo = ('bailinfo', "(?<=BAIL INFORMATION)(.*?)(?=CHARGES)")
    pat_charges = ('charges', "(?<=CHARGES)(.*?)(?=DISPOSITION SENTENCING)")
    pat_dispo = ('dispo', "(?<=DISPOSITION SENTENCING/PENALTIES)(.*?)(?=COMMONWEALTH INFORMATION)")
    pat_contactinfo = ('contactinfo', "(?<=COMMONWEALTH INFORMATION)(.*?)(?=ENTRIES)")
    pat_entries = ('entries', "(?<=ENTRIES)(.*)")
    patternlist = [pat_docket, pat_caseinfo, pat_status, pat_calevents
            , pat_defendinfo, pat_participants, pat_bailinfo
            ,pat_charges, pat_dispo, pat_contactinfo, pat_entries]
    # initialize Sections as an empty dictionary
    sections = {}
    # Loop through RegEx patterns to break document into sections
    for pattern in patternlist:
        sections[pattern[0]] = re.findall(pattern[1], text, re.DOTALL)[0].strip()
        
    pages_charges = find_pages(filename,'Statute Description')
    pages_bail_set = find_pages(filename,'Filed By')
    pages_bail_info = find_pages(filename,'Bail Posting Status')
    pages_zip = find_pages(filename,'Zip:')
    pages = list(set(pages_charges+pages_bail_set+pages_bail_info+pages_zip))
    pdf = pdfquery.PDFQuery(filename)
    pdf.load(pages)
        
    ###### Extract specific fields
    # with each pattern, we append the parsed text into the results dictionary
    ### Docket Number ###
    pattern_docket = r"MC-\d{2}-CR-\d{7}-\d{4}"
    result['docket_no'] = re.findall(pattern_docket, text, re.DOTALL)[0]
    ### Offenses ###
    result['offenses'],result['offense_date'],result['statute'] = get_charges(pdf, pages_charges)
    ### Arrest Date ###
    pattern_arrestdt = r"Arrest Date:(.*?)(?<=\d{2}\/\d{2}\/\d{4})"
    result['arrest_dt'] = re.findall(pattern_arrestdt, sections['status'], re.DOTALL)[0]
    ### Case Status ###
    pattern_status = r"Case Status:(.*?)Arrest"
    result['case_status'] = re.findall(pattern_status, sections['status'], re.DOTALL)[0]
    ## Arresting Officer ###
    pattern_officer = r"Arresting Officer :(.*?)Complaint\/Incident"
    result['arresting_officer'] = re.findall(pattern_officer, sections['caseinfo'], re.DOTALL)[0].strip()
    ## Defendant Atty ###
    pattern_atty = r"(?<=ATTORNEY INFORMATION Name:)(.*?)(?=\d|Supreme)"
    data_attorney = re.findall(pattern_atty, sections['contactinfo'], re.DOTALL)
    if len(data_attorney) > 0:
        attorney_information = data_attorney[0].strip()
        attorney_information = attorney_information.split('Public')[0]
        attorney_information = attorney_information.split('Private')[0]
        attorney_information = attorney_information.split('Court Appointed')[0]
        result['attorney'] = attorney_information
 
    else:
        result['attorney'] = ''
    ## Defendant Information ###
    pattern_dob = r"Date Of Birth:(.*?)City"
    result['dob'] = re.findall(pattern_dob, sections['defendant'], re.DOTALL)[0].strip()
    result['zip'] = get_zip(pdf, pages_zip)
    ## Bail Information ###
    result['bail_set_by'] = get_bail_set(pdf,pages_bail_set)
    result['bail_amount'],result['bail_paid'],result['bail_date'],result['bail_type'] = get_bail_info(pdf, pages_bail_info)

    ## Preliminary Details ###
    pattern_prelim = r"(?<=Calendar Event Type )(.*?)(?=Scheduled)"
    prelim = re.findall(pattern_prelim, sections['calendar'], re.DOTALL)
    result['prelim_hearing_dt'] = re.findall(r"\d{2}\/\d{2}\/\d{4}", str(prelim))[0]
    result['prelim_hearing_time'] = re.findall(r"((1[0-2]|0?[1-9]):([0-5][0-9]) ?([AaPp][Mm]))", str(prelim))[0][0]
    ###  Uncomment to print a section during development
    ###  so we can build RegEx using online tools because RegEx is hard
    ###  https://regex101.com/r/12KSAf/1/
    return result

def main(folder, output_name):


    parsed_results = []
    for enu,file in enumerate(os.listdir(folder)):
        try:
            print(enu, file)
            text = scrape_pdf(path_folder+file)
            data = parse_pdf(path_folder+file,text)
            parsed_results.append(data)
        except:
            print('Failed: ',file)

    final = pd.DataFrame(parsed_results)
    final.to_csv(output_name+'.csv', index=False)

if __name__ == "__main__":
    path_folder = '/home/bmargalef/MEGA/pbf-scraping-pdf_scraping/sampledockets/sampledockets/downloads/failed_dockets/'
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('-p','--path_folder', default= path_folder,
                        help='Path to folder with PDFs')
    parser.add_argument('-o','--output_name', default= 'output',
                        help='Path to folder with PDFs')

    args = parser.parse_args()
    main(args.path_folder,args.output_name)

