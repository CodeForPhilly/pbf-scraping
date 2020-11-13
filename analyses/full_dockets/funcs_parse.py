import PyPDF2
import re
import numpy as np
import pdfquery

# Helper functions -----------------------------------------------------------
def query_contains(page, searchTerm):
    return 'LTPage[page_index="{}"] LTTextLineHorizontal:contains("{}")'.format(page, searchTerm)


def query_box(page, bounds):
    return 'LTPage[page_index="{}"] LTTextBoxHorizontal:in_bbox("{}, {}, {}, {}")'.format(
        page, *bounds)


def query_line(page, bounds):
    return 'LTPage[page_index="{}"] LTTextLineHorizontal:in_bbox("{}, {}, {}, {}")'.format(
        page, *bounds)


def find_pages(filename, string):
    """ Return list of page numbers of filename (PDF) in which string is found  """

    pdfReader = PyPDF2.PdfFileReader(filename)
    num_pages = pdfReader.numPages
    pages = []
    for i in range(0, num_pages):
        PageObj = pdfReader.getPage(i)
        Text = PageObj.extractText()
        if re.search(string,Text):
            pages.append(i)
            
    return pages


def offense(pdf, page, y_bottom, y_top, x0, x1, x2, x4, charges, date, statutes, delta=5):
    """" TODO: update so that you don't need charges/data/statues for this to run"""
    
    
    n_lines = pdf.pq(query_line(page, [0, y_bottom, 80, y_top])).text().split(' ')
    n = len(n_lines)
    if n_lines[0] == '':
        charges, date, statutes = charges, date, statutes
    else:
        n_offenses =[int(x) for x in n_lines]
        n = len(n_offenses)
        h = 0
        if len(charges) > 0:
            h = 1
            if charges[0] == '':
                charges = []
                statutes = []
                h = 0
        y_array_bottom = np.zeros(n)
        y_array_top = np.zeros(n)
        k = 0
        y = y_top  
        n_offenses.sort()
        while y > y_bottom:
            y = y-delta
            info = pdf.pq(query_line(page, [0, y, 70, y_top])).text().split(' ')
            if len(info[0]) > 0:
                if int(info[-1]) == n_offenses[k]:
                    y_array_bottom[k-h] = y
                else:
                    if k <= n-1:
                        k = k+1

        y = y_bottom
        index = 0
        a = 0
        for i in range(int((y_top-y_bottom)/delta)):
            if abs(a-1) > len(n_offenses):
                break
            y = y + delta
            info = pdf.pq(query_line(page, [0, y_bottom, 70, y])).text()   
            info = (re.sub("\s+", ",", info.strip())).split(',')
            if len(info[0]) > 0:
                if n_offenses[a-1] in [int(x) for x in info]  :
                    y_array_top[-index-1] = y
                    index = index+1
                    a = a-1
                    
        y_array_top[0] = y_top
        y_array_bottom[-1] = y_bottom
        for y0, y1 in zip(y_array_bottom,y_array_top):
            data_charges = pdf.pq(query_line(page, [x0, y0, x1, y1])).text()
            data_statutes = pdf.pq(query_line(page, [x4, y0, x0, y1])).text()
            date = pdf.pq(query_line(page, [x1, y0, x2, y1])).text()
            charges.append(data_charges)
            statutes.append(data_statutes)

    return charges, date, statutes


def bail_set(pdf, page, y_bottom, y_top, x0, x1, bail, bail_type, delta=5):
    n_lines = pdf.pq(query_line(page, [0, y_bottom, 60, y_top])).text().split(' ')
    n = len(n_lines)
    y_array_bottom = np.zeros(n)
    y_array_top = np.zeros(n)
    k = 1
    y = y_bottom  
    new_y_bottom = y_bottom
    while (y < y_top) & (k<=n):
        y = y+delta
        info = pdf.pq(query_line(page, [0, new_y_bottom, 60, y])).text()   
        if len(info) > 0:
            if int(info[0]) == int(n_lines[-1-(k-1)]):
                y_array_top[-1-(k-1)] = y
                new_y_bottom = y
                k = k+1

                    
    y_array_bottom[-1] = y_bottom
    y_array_bottom[0:n-1] = y_array_top[1:]
    bail_set = []
    bail_other = []
    if bail_type == 0:
        bail_set = bail
    else:
        bail_other = bail
    for y0, y1 in zip(y_array_bottom,y_array_top):
        data = pdf.pq(query_line(page, [x0, y0, x1, y1])).text()
        data_cp = pdf.pq(query_line(page, [0, y0, x0, y1])).text()

        if re.search("Bail Set+", data_cp, flags=re.IGNORECASE) :
            bail_set = data
        elif re.search("Bail+", data_cp, flags=re.IGNORECASE) :
            bail_other = data
        if bail_type == 1:
            if len(bail_set) > 0:
                bail = bail_set
                bail_type = 0
            else:
                bail = bail_other
                bail_type = 1
    return bail, bail_type


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

                 
def get_bail_set(pdf, pages):
    bail = []
    bail_type = 1 #0: Bail Set, 1: Other e.g. Bail Posted, changed, denied...
    for p in pages:
        info_1 = pdf.pq(query_contains(p, 'Filed By'))
        x1_0 = float(info_1.attr('x0'))
        y1_0 = float(info_1.attr('y0'))
        info_2 = pdf.pq(query_contains(p, 'CASE FINANCIAL INFORMATION'))
        if len(info_2) == 0:
            info_2 = pdf.pq(query_contains(p, 'CPCMS'))
        y2_1 = float(info_2.attr('y1'))
        bail,bail_type = bail_set(pdf,p,y2_1,y1_0,x1_0,x1_0+200,bail,bail_type)

    return bail


def get_charges(pdf, pages):

    charges = []
    statutes = []
    date = ''
    for p in pages:
        info_1 = pdf.pq(query_contains(p, 'Statute Description'))
        x1_0 = float(info_1.attr('x0'))
        y1_0 = float(info_1.attr('y0'))
        info_2 = pdf.pq(query_contains(p, 'DISPOSITION SENTENCING'))
        if len(info_2) == 0:
            info_2 = pdf.pq(query_contains(p, 'CPCMS'))
        y2_1 = float(info_2.attr('y1'))
        info_3 = pdf.pq(query_contains(p, 'Offense Dt'))
        x3_0 = float(info_3.attr('x0'))
        x3_1 = float(info_3.attr('x1'))+10
        info_4 = pdf.pq(query_contains(p, 'Statute'))
        x4_0 = x1_0 -100 #float(info_4.attr('x0'))
        charges,date, statute = offense(pdf,p,y2_1,y1_0,x1_0,x3_0,x3_1,x4_0,charges,date,statutes)

    return charges, date, statute
