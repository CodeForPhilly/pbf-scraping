import re
import numpy as np
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfpage import PDFPage
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from io import StringIO
from offense_category import offense_dict


# Helper functions -----------------------------------------------------------
def query_contains_box(page, searchTerm):
    return 'LTPage[page_index="{}"] LTTextBoxHorizontal:contains("{}")'.format(page, searchTerm)

def query_contains_line(page, searchTerm):
    return 'LTPage[page_index="{}"] LTTextLineHorizontal:contains("{}")'.format(page, searchTerm)

def query_box(page, bounds):
    return 'LTPage[page_index="{}"] LTTextBoxHorizontal:in_bbox("{}, {}, {}, {}")'.format(page, *bounds)

def query_line(page, bounds):
    return 'LTPage[page_index="{}"] LTTextLineHorizontal:in_bbox("{}, {}, {}, {}")'.format(page, *bounds)



def find_pages(filename, string):
    """ Return list of page numbers of filename (PDF) in which string is found  """

    rsrcmgr = PDFResourceManager()
    codec = 'utf-8'
    laparams = LAParams()
    pages = []

    fp = open(filename, 'rb')
    for i,page in enumerate(PDFPage.get_pages(fp)):
        sio = StringIO()
        device = TextConverter(rsrcmgr, sio, codec=codec, laparams=laparams)
        interpreter = PDFPageInterpreter(rsrcmgr, device)
        interpreter.process_page(page)
        text = sio.getvalue()
        if re.search(string,text):
            pages.append(i)
        device.close()
        sio.close()
    fp.close()

    return pages

def offense(pdf, page, y_bottom, y_top, x0, x1, x2, x3, delta=5):
    """ Return list of charges, list of statues, and date
        
        TODO: try to reduce the amount of code, get rid of magic numbers """

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
    x_left = 0
    x_right = 60
    lineNums = pdf.pq(query_line(page, [x_left, y_bottom, x_right, y_top])).text().split(' ')
    n = len(lineNums)
    yArray_bottom = np.zeros(n)
    yArray_top = np.zeros(n)
    k = 1
    y = y_bottom  
    new_y_bottom = y_bottom
    while (y < y_top) & (k <= n):
        y = y + delta
        info = pdf.pq(query_line(page, [x_left, new_y_bottom, x_right, y])).text()   
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

        if re.search("Bail", data_cp, flags=re.IGNORECASE) and not isBailFound:
            isBailFound = True
            magistrate = data_filedBy.strip()
                
    return magistrate


# Main search functions ------------------------------------------------------
def get_bail_info(pdf, pages):
    bail_info = []
    for p in pages:
        info_1 = pdf.pq(query_contains_line(p, 'Bail Posting Status'))
        x1_0 = float(info_1.attr('x0'))
        x1_1 = float(info_1.attr('x1'))
        y1_0 = float(info_1.attr('y0'))
        info_2 = pdf.pq(query_contains_line(p, 'Percentage'))
        x2_0 = float(info_2.attr('x0'))
        x2_1 = float(info_2.attr('x1'))
        info_3 = pdf.pq(query_contains_line(p, 'CHARGES'))
        if len(info_3) == 0:
            info_3 = pdf.pq(query_contains_line(p, 'CPCMS'))
        y3_1 = float(info_3.attr('y1'))
        info_4 = pdf.pq(query_contains_line(p, 'Bail Action'))
        x4_1 = float(info_4.attr('x1'))
        info_5 = pdf.pq(query_contains_line(p, 'Bail Type'))
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
    """ Return zipcode """
    info_1 = pdf.pq(query_contains_line(page[0], 'Zip: ')).text()
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
        info_1 = pdf.pq(query_contains_line(p, 'Filed By'))
        x0 = float(info_1.attr('x0'))
        y0 = float(info_1.attr('y0'))
        # Bottom of section
        info_2 = pdf.pq(query_contains_line(p, 'CASE FINANCIAL INFORMATION'))
        if len(info_2) == 0:
            info_2 = pdf.pq(query_contains_line(p, 'CPCMS'))
        x1 = x0 + 200
        y1 = float(info_2.attr('y1'))
        
        magistrateData = bail_set_by(pdf, p, y1, y0, x0, x1)
        if magistrateData != '':
            magistrate = magistrateData

    return magistrate


def get_offense_type(statute):
    """ Parse statute information and gets offense type """
    # input: (list of strings) statute output of 'get_charges'
    # output: (list of strings) offense type 
    offense_type = []

    # find title and chapter numbers of offenses
    for item in statute:
        statute_idx = item.replace("."," ")
        statute_idx = statute_idx.replace("-"," ")
        statute_idx = statute_idx.replace('§'," ")
        statute_idx = statute_idx.split()
        
        # get title 
        title = statute_idx[0]

        # get default chapter
        chapter = statute_idx[1][:2]

        # adjust chapter numbers
        if title == '0':
            chapter = '0'
        if title == '18':
            if len(statute_idx[1]) == 4:
                chapter = statute_idx[1][:2]
            else:
                chapter = statute_idx[1][:1]
        elif title == '35':
            chapter = statute_idx[1]
        elif title == '75':
            if int(statute_idx[1]) < 3731:
                # Chapter 37 subchapter A
                chapter = '1'
            elif int(statute_idx[1]) < 3741:
                # Chapter 37 subchapter B
                chapter = '2'
            elif int(statute_idx[1]) < 3800:
                # Chapter 38 subchapter C
                chapter = '3'
            else:
                chapter = statute_idx[1][:2]
        
        # find offense type
        if (int(title), int(chapter)) in offense_dict.keys():
            offense_type.append(offense_dict[(int(title), int(chapter))])
        else:
            offense_type.append('NA')
            print('Warning: could not parse statute title ' + title + ' chapter ' + chapter)
    return offense_type

def get_charges(pdf, pages):
    """ Return the list of charges and statutes """

    chargeList = []
    statuteList = []
    date = ''
    for p in pages:
        # Charge description bottom left
        info_1 = pdf.pq(query_contains_line(p, 'Statute Description'))
        x1_0 = float(info_1.attr('x0'))
        y1_0 = float(info_1.attr('y0'))
        # Bottom of charges section
        info_2 = pdf.pq(query_contains_line(p, 'DISPOSITION SENTENCING'))
        if len(info_2) == 0:
            info_2 = pdf.pq(query_contains_line(p, 'CPCMS'))
        y2_1 = float(info_2.attr('y1'))
        # Offense date left and right
        info_3 = pdf.pq(query_contains_line(p, 'Offense Dt'))
        x3_0 = float(info_3.attr('x0'))
        x3_1 = float(info_3.attr('x1'))+10
        # Statute number left
        #info_4 = pdf.pq(query_contains_line(p, 'Statute'))
        x4_0 = x1_0 - 100 #float(info_4.attr('x0'))
        
        charges, date, statutes = offense(pdf, p, y2_1, y1_0, x1_0, x3_0, x3_1, x4_0)
        chargeList.extend(charges)
        statuteList.extend(statutes)

    offense_type = get_offense_type(statuteList)
    return chargeList, date, statuteList, offense_type

def get_dob(pdf,pages):
    p = pages[0]
    info_1 = pdf.pq(query_contains_line(p,'Date Of Birth:'))
    x1_1 = float(info_1.attr('x1'))
    y1_0 = float(info_1.attr('y0'))
    y1_1 = float(info_1.attr('y1'))
    info_2 = pdf.pq(query_contains_line(p,'City/State/Zip:'))
    x2_0 = float(info_2.attr('x0'))

    dob = pdf.pq(query_line(p, [x1_1, y1_0-1, x2_0, y1_1+1])).text()

    return dob


def get_status(pdf,pages):
    """ Return case status and arrest date"""

    p = pages[0]
    info_1 = pdf.pq(query_contains_line(p,'Case Status:'))
    x1_1 = float(info_1.attr('x1'))
    y1_0 = float(info_1.attr('y0'))
    y1_1 = float(info_1.attr('y1'))
    info_2 = pdf.pq(query_contains_line(p,'Status Date'))
    x2_0 = float(info_2.attr('x0'))
    info_3 = pdf.pq(query_contains_line(p,'Arrest Date:'))
    x3_1 = float(info_3.attr('x1'))

    case_status = pdf.pq(query_line(p, [x1_1, y1_0-1, x2_0, y1_1+1])).text()
    arrest_date = pdf.pq(query_line(p, [x3_1, y1_0-1, x3_1+200, y1_1+1])).text()

    return case_status,arrest_date


def get_prelim_hearing(pdf,pages):
    """ Return preliminary arraignment date and time """

    p = pages[0]
    info_1 = pdf.pq(query_contains_box(p,'Schedule Start Date'))
    x1_0 = float(info_1.attr('x0'))
    y1_0 = float(info_1.attr('y0'))
    info_2 = pdf.pq(query_contains_box(p,'Start Time'))
    x2_0 = float(info_2.attr('x0'))
    info_3 = pdf.pq(query_contains_line(p,'Room'))
    x3_0 = float(info_3.attr('x0'))

    prelim_hearing_date = pdf.pq(query_line(p, [x1_0, y1_0-30, x2_0, y1_0])).text()
    prelim_hearing_time = pdf.pq(query_line(p, [x2_0, y1_0-30, x3_0, y1_0])).text()

    return prelim_hearing_date, prelim_hearing_time

def get_arresting_officer(pdf,pages):
    """ Return arresting officer """
    p = pages[0]
    info_1 = pdf.pq(query_contains_line(p,'Arresting Officer:'))
    arresting_officer = info_1.text().split('Arresting Officer:')[1].strip()

    return arresting_officer

