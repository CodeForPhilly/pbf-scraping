import PyPDF2
import re
import numpy as np
import pdfquery

# Helper functions -----------------------------------------------------------
def query_contains(page, searchTerm):
    return 'LTPage[page_index="{}"] LTTextLineHorizontal:contains("{}")'.format(page, searchTerm)

def query_box(page, bounds):
    return 'LTPage[page_index="{}"] LTTextBoxHorizontal:in_bbox("{}, {}, {}, {}")'.format(page, *bounds)

def query_line(page, bounds):
    return 'LTPage[page_index="{}"] LTTextLineHorizontal:in_bbox("{}, {}, {}, {}")'.format(page, *bounds)


def find_pages(filename, string):
    """ Return list of page numbers of filename (PDF) in which string is found  """

    pdfReader = PyPDF2.PdfFileReader(filename)
    nPages = pdfReader.numPages
    pages = []
    for i in range(0, nPages):
        pageObj = pdfReader.getPage(i)
        text = pageObj.extractText()
        if re.search(string, text):
            pages.append(i)
            
    return pages


def offense(pdf, page, y_bottom, y_top, x0, x1, x2, x3, delta=5):
    """ Return list of charges, list of statues, and date """

    x_left = 0
    x_right = 80 # Or 70?

    charges = []
    statutes = []
    date = ''
    lineNums = pdf.pq(query_line(page, [x_left, y_bottom, x_right, y_top])).text().split(' ') #80
    if lineNums[0] != '':
        lineNums = [int(x) for x in lineNums]
        nLines = len(lineNums)
        
        h = 0
        k = 0
        yArray_bottom = np.zeros(nLines)
        yArray_top = np.zeros(nLines)
        y = y_top  
        lineNums.sort()
        while y > y_bottom:
            y = y - delta
            info = pdf.pq(query_line(page, [x_left, y, x_right, y_top])).text().split(' ') #70
            if len(info[0]) > 0:
                if int(info[-1]) == lineNums[k]:
                    yArray_bottom[k-h] = y
                else:
                    if k <= nLines - 1:
                        k = k+1

        y = y_bottom
        index = 0
        a = 0
        for i in range(int((y_top-y_bottom)/delta)):
            if abs(a-1) > len(lineNums):
                break
            y = y + delta
            info = pdf.pq(query_line(page, [x_left, y_bottom, x_right, y])).text()    #70
            info = (re.sub("\s+", ",", info.strip())).split(',')
            if len(info[0]) > 0:
                if lineNums[a-1] in [int(x) for x in info]:
                    yArray_top[-index-1] = y
                    index = index+1
                    a = a-1
                    
        yArray_top[0] = y_top
        yArray_bottom[-1] = y_bottom
        for y0, y1 in zip(yArray_bottom,yArray_top):
            data_charges = pdf.pq(query_line(page, [x0, y0, x1, y1])).text()
            data_statutes = pdf.pq(query_line(page, [x3, y0, x0, y1])).text()
            date = pdf.pq(query_line(page, [x1, y0, x2, y1])).text()
            charges.append(data_charges)
            statutes.append(data_statutes)
            
    return charges, date, statutes


def bail_set_by(pdf, page, y_bottom, y_top, x0, x1, delta=5):
    """ Find magistrate and whether bail is set or otherwise """
    
    magistrate = ''

    # Find lines
    lineNums = pdf.pq(query_line(page, [0, y_bottom, 60, y_top])).text().split(' ')
    n = len(lineNums)
    yArray_bottom = np.zeros(n)
    yArray_top = np.zeros(n)
    k = 1
    y = y_bottom  
    new_y_bottom = y_bottom
    while (y < y_top) & (k <= n):
        y = y + delta
        info = pdf.pq(query_line(page, [0, new_y_bottom, 60, y])).text()   
        if len(info) > 0:
            if int(info[0]) == int(lineNums[-1-(k-1)]):
                yArray_top[-1-(k-1)] = y
                new_y_bottom = y
                k = k+1
                    
    yArray_bottom[-1] = y_bottom
    yArray_bottom[0:n-1] = yArray_top[1:]

    # Find first line referring to bail decision being made (set or denied)
    isBailFound = False
    for y0, y1 in zip(yArray_bottom, yArray_top):
        data_filedBy = pdf.pq(query_line(page, [x0, y0, x1, y1])).text()
        data_cp = pdf.pq(query_line(page, [0, y0, x0, y1])).text()

        #if re.search("Bail Set", data_cp, flags=re.IGNORECASE):
        #    isBailSet = 1 # Bail is set
        if re.search("Bail", data_cp, flags=re.IGNORECASE) and not isBailFound:
            isBailFound = True
            magistrate = data_filedBy
                
    return magistrate


# Main search functions ------------------------------------------------------
def get_bail_info(pdf, pages):
    bail_info = []
    for p in pages:
        info_1 = pdf.pq(query_contains(p, 'Bail Posting Status'))
        x1_0 = float(info_1.attr('x0'))
        x1_1 = float(info_1.attr('x1'))
        y1_0 = float(info_1.attr('y0'))
        info_2 = pdf.pq(query_contains(p, 'Percentage'))
        x2_0 = float(info_2.attr('x0'))
        x2_1 = float(info_2.attr('x1'))
        info_3 = pdf.pq(query_contains(p, 'CHARGES'))
        if len(info_3) == 0:
            info_3 = pdf.pq(query_contains(p, 'CPCMS'))
        y3_1 = float(info_3.attr('y1'))
        info_4 = pdf.pq(query_contains(p, 'Bail Action'))
        x4_1 = float(info_4.attr('x1'))
        info_5 = pdf.pq(query_contains(p, 'Bail Type'))
        x5_0 = float(info_5.attr('x0'))
        bail_date = pdf.pq(query_box(p, [x4_1, y3_1, x5_0, y1_0])).text()
        bail_type = pdf.pq(query_box(p, [x5_0, y3_1, x2_0, y1_0])).text()
        bail_date = bail_date.split(' ')[-1]
        bail_type = bail_type.split(' ')[-1]
        bail_info = pdf.pq(query_box(p, [x2_1, y3_1, x1_0, y1_0])).text()
        bail_amount = float(bail_info.split('$')[-1].replace(',',''))
        bail_paid = 0
        check_posted = pdf.pq(query_line(p, [x1_0, y3_1, x1_1, y1_0])).text()
        
        if 'Posted' in check_posted:
            bail_paid = 0.1*bail_amount

    return bail_amount, bail_paid, bail_date, bail_type 


def get_zip(pdf, page):
    info_1 = pdf.pq(query_contains(page[0], 'Zip: ')).text()
    zip_code = info_1.split(' ')[-1]
    regnumber = re.compile(r'\d+')
    if regnumber.search(zip_code) == None:
        zip_code = ''

    return zip_code

                 
def get_magistrate(pdf, pages):
    """ Return name of person who filed document regarding bail """
    
    magistrate = ''
    for p in pages:
        # Top of section
        info_1 = pdf.pq(query_contains(p, 'Filed By'))
        x0 = float(info_1.attr('x0'))
        y0 = float(info_1.attr('y0'))
        # Bottom of section
        info_2 = pdf.pq(query_contains(p, 'CASE FINANCIAL INFORMATION'))
        if len(info_2) == 0:
            info_2 = pdf.pq(query_contains(p, 'CPCMS'))
        x1 = x0 + 200
        y1 = float(info_2.attr('y1'))
        
        magistrateData = bail_set_by(pdf, p, y1, y0, x0, x1)
        if magistrateData != '':
            magistrate = magistrateData

    return magistrate


def get_charges(pdf, pages):
    """ Return the list of charges and statutes """

    chargeList = []
    statuteList = []
    date = ''
    for p in pages:
        # Charge description bottom left
        info_1 = pdf.pq(query_contains(p, 'Statute Description'))
        x1_0 = float(info_1.attr('x0'))
        y1_0 = float(info_1.attr('y0'))
        # Bottom of charges section
        info_2 = pdf.pq(query_contains(p, 'DISPOSITION SENTENCING'))
        if len(info_2) == 0:
            info_2 = pdf.pq(query_contains(p, 'CPCMS'))
        y2_1 = float(info_2.attr('y1'))
        # Offense date left and right
        info_3 = pdf.pq(query_contains(p, 'Offense Dt'))
        x3_0 = float(info_3.attr('x0'))
        x3_1 = float(info_3.attr('x1'))+10
        # Statute number left
        info_4 = pdf.pq(query_contains(p, 'Statute'))
        x4_0 = x1_0 - 100 #float(info_4.attr('x0'))
        
        charges, date, statutes = offense(pdf, p, y2_1, y1_0, x1_0, x3_0, x3_1, x4_0)
        chargeList.extend(charges)
        statuteList.extend(statutes)

    return chargeList, date, statuteList
