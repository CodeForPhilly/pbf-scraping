def scrape_summary_pdf(filename):
    """ 
    Scrapes the PDF
    Accepts a filename, and extracts the document data page by page by using
    PyPDF2
    Parameters: 
    filename (string): path to the filename.pdf
    Returns: 
    text: Entire document as a string.
    """
    import PyPDF2
    import re
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
            text = textract.process(filename, method='tesseract', language='eng')
    return text
def parse_summary_pdf(text):
    """ 
    Parses specific elements from the string 
    NOTE: This summary is for multiple docket numbers, so we can create multiple
    records by parsing a single summary file
    Parameters: 
    text (string): Cleaned document as a string
    Returns: 
    result: a dictionary of specific elements 
    """
    import re
    # initialize result as an empty dictionary
    result = {}
    ###### Extract specific fields
    # with each pattern, we append the parsed text into the results dictionary
    ### Docket Numbers ###
    pattern_docket = r"MC-\d{2}-CR-\d{7}-\d{4}"
    result['docket_no'] = re.findall(pattern_docket, text, re.DOTALL)
    ### Race ###
    pattern_docket = r"(?<=Race: )(.*?)(?=Hair:)"
    result['race'] = re.findall(pattern_docket, text, re.DOTALL)[0]
    ### Sex ###
    pattern_docket = r"(?<=Sex: )(.*?)(?=Active|Closed|Inactive)"
    result['sex'] = re.findall(pattern_docket, text, re.DOTALL)[0]
    ###  Uncomment to print a section during development
    ###  so we can build RegEx using online tools because RegEx is hard
    ###  https://regex101.com/r/12KSAf/1/
    #print(text)
    return result