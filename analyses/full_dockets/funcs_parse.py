import re
import numpy as np
from datetime import datetime
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
    """ Return list of page numbers of filename (PDF) in which string is found """

    rsrcmgr = PDFResourceManager()
    codec = 'utf-8'
    laparams = LAParams()
    pages = []

    fp = open(filename, 'rb')
    for i, page in enumerate(PDFPage.get_pages(fp)):
        sio = StringIO()
        device = TextConverter(rsrcmgr, sio, codec=codec, laparams=laparams)
        interpreter = PDFPageInterpreter(rsrcmgr, device)
        interpreter.process_page(page)
        text = sio.getvalue()
        if re.search(string, text):
            pages.append(i)
        device.close()
        sio.close()
    fp.close()

    return pages


def offense(pdf, page, y_bottom, y_top, x0, x1, x2, x3, delta=5):
    """ Return list of charges, list of statues, and date """

    x_left = 0
    x_right = 80  # Or 70?

    charges = []
    statutes = []
    date = ''
    lineNums = pdf.pq(query_line(page, [x_left, y_bottom, x_right, y_top])).text().split(' ')  # 80


    if lineNums[0] != '':
        #Some dockets use 99,999 as a seq number, so we need to strip out the comma before the conversion to int.
        #Aso done on line 82
        lineNums = map(lambda x: x.replace(',','') , lineNums)
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
            info = pdf.pq(query_line(page, [x_left, y, x_right, y_top])).text().split(' ')  # 70
            if len(info[0]) > 0:
                info = map(lambda x: x.replace(',',''),info)
                info_int = [int(x) for x in info]
                info_int.sort()
                if info_int[-1] == lineNums[k]:
                    yArray_bottom[k - h] = y
                else:
                    if k <= nLines - 1:
                        k = k + 1

        y = y_bottom
        index = 0
        a = 0
        for i in range(int((y_top - y_bottom) / delta)):
            if abs(a - 1) > len(lineNums):
                break
            y = y + delta
            info = pdf.pq(query_line(page, [x_left, y_bottom, x_right, y])).text()  # 70
            info = (re.sub("\s+", ",", info.strip())).split(',')
            if len(info[0]) > 0:
                if lineNums[a - 1] in [int(x) for x in info]:
                    yArray_top[-index - 1] = y
                    index = index + 1
                    a = a - 1

        yArray_top[0] = y_top
        yArray_bottom[-1] = y_bottom
        for y0, y1 in zip(yArray_bottom, yArray_top):
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
            if int(info[0]) == int(lineNums[-1 - (k - 1)]):
                yArray_top[-1 - (k - 1)] = y
                new_y_bottom = y
                k = k + 1

    yArray_bottom[-1] = y_bottom
    yArray_bottom[0:n - 1] = yArray_top[1:]
    
    # Find first line referring to bail decision being made (set or denied)
    isBailFound = False
    for y0, y1 in zip(yArray_bottom, yArray_top):
        data_filedBy = pdf.pq(query_line(page, [x0, y0, x1, y1])).text()
        data_cp = pdf.pq(query_line(page, [0, y0, x0, y1])).text()

        if ((re.search("Bail Set", data_cp, flags=re.IGNORECASE)
             or re.search("Bail Denied", data_cp, flags=re.IGNORECASE)
             or re.search("Order Denying Motion to Set Bail", data_cp, flags=re.IGNORECASE))
            and not (isBailFound or re.search("Posted", data_cp, flags=re.IGNORECASE))):
            isBailFound = True
            magistrate = data_filedBy.strip()
            # sometimes bail is changed over the course of a case, but we're interested in the initial bail, so break out of the loop if we found it.
            break

    return magistrate


# Main search functions ------------------------------------------------------
def parse_bail_actions(action_str):
    """Get list of Bail Actions, splitting by keywords.
    
    NOTE: this keywords list may not be complete!! May result in incorrect parsing."""
    
    keywords = ['Deny', 'Denied', 'Set', 'Change', 'Increase', 'Decrease', 'Revoke', 'Reinstate']
    list1 = re.findall('|'.join(keywords), action_str)
    list2 = re.split('|'.join(keywords), action_str)[1:]
    action_list = [(s1 + s2).strip().replace('\n',' ') for (s1, s2) in list(zip(list1, list2))]

    return action_list


def get_bail_info(pdf, pages):
    """Get all information in the bail section
    
    Note that the method used is fairly brittle: rather than going row by row,
    it get all information in each column as a list (where column lists may be
    of different lengths) and tries to match row items across columns.
    
    Return:
        bail_entries_all: list of dictionaries of bail action information, containing
            bail_action, bail_date, bail_type, bail_percentage, and bail_amount keys
        bail_posted: amount of bail posted, computed from NEWEST bail info
        bail_posted_date: date that bail was posted (if any, otherwise '')
    """
    
    dateFormat = "%m/%d/%Y"
    
    bail_entries_all = [] # From bail actions columns
    bail_posted_all = [] # From bail posted columns
    for p in pages:
        # Get column x positions
        result = pdf.pq(query_contains_line(p, 'Bail Action'))
        x0_bailAction = float(result.attr('x0'))
        x1_bailAction = float(result.attr('x1'))
        
        result = pdf.pq(query_contains_line(p, 'Bail Type'))
        x0_bailType = float(result.attr('x0'))

        result = pdf.pq(query_contains_line(p, 'Percentage'))
        x0_percentage = float(result.attr('x0'))
        x1_percentage = float(result.attr('x1'))

        result = pdf.pq(query_contains_line(p, 'Bail Posting Status'))
        x0_bailPostingStatus = float(result.attr('x0'))
        x1_bailPostingStatus = float(result.attr('x1'))
        y_top = float(result.attr('y0')) # Top of section content
        
        result = pdf.pq(query_contains_line(p, 'Posting Date'))
        x0_postingDate = float(result.attr('x0'))
        x1_postingDate = float(result.attr('x1'))
        
        # Get bottom of section content
        result = pdf.pq(query_contains_line(p, 'CHARGES'))
        if len(result) == 0:
            result = pdf.pq(query_contains_line(p, 'CPCMS'))
        y_bottom = float(result.attr('y1'))
        
        # Get lists of bail action, bail date, bail type, percentage, and amount
        bail_action_text = pdf.pq(query_box(p, [x0_bailAction, y_bottom, x1_bailAction + 50, y_top])).text()
        bail_action_list = parse_bail_actions(bail_action_text)
        bail_date_list = pdf.pq(query_box(p, [x1_bailAction, y_bottom, x0_bailType, y_top])).text().split(' ')
        bail_type_list = pdf.pq(query_box(p, [x0_bailType, y_bottom, x0_percentage, y_top])).text().split(' ')
        bail_percentage_list = pdf.pq(query_box(p, [x0_percentage, y_bottom, x1_percentage, y_top])).text().split(' ')
        bail_amount_list = pdf.pq(query_box(p, [x1_percentage, y_bottom, x0_bailPostingStatus, y_top])).text().split(' ')       
        
        # If couldn't correctly split bail actions, just don't store it
        if len(bail_action_list) != len(bail_date_list):
            bail_action_list = [''] * len(bail_date_list)

        # Occasionally parser grabs the rows in the wrong order (but the same wrong order for all columns); sort
        if len(bail_date_list) > 1:
            datetime_list = [datetime.strptime(s, '%m/%d/%Y') for s in bail_date_list]
            indices_sorted = [i for i, v in sorted(enumerate(datetime_list), key=lambda x: x[1])]
        else:
            indices_sorted = [0]

        # Get each row of bail information
        bail_info_page = []
        counter_percent = 0
        counter_amount = 0
        bailDeniedCount = 0
        for i in indices_sorted:
            bail_action = bail_action_list[i]
            bail_date = bail_date_list[i]
            if (bail_action == 'Denied') or ('Deny' in bail_action):
                bailDeniedCount += 1
                bail_type = 'Denied' # No bail type listed in this case
            else:
                bail_type = bail_type_list[i-bailDeniedCount]
            
            if bail_type == 'Monetary':
                try:
                    bail_percentage = float(bail_percentage_list[counter_percent].strip('%'))
                except (IndexError, ValueError):
                    bail_percentage = 10.0 # If monetary bail without percentage specified, assume 10% is posted
                counter_percent += 1
            else:
                bail_percentage = 100.0 # For other bail types, e.g., unsecured, assume full amount is posted

            if bail_type in ['Monetary', 'Unsecured', 'Nominal']:
                bail_amount = float(bail_amount_list[counter_amount].strip('$').replace(',', ''))
                counter_amount += 1
            else:
                bail_amount = 0.0
                
            bail_dict = {'bail_action': bail_action,
                         'bail_date': bail_date,
                         'bail_type': bail_type,
                         'bail_percentage': bail_percentage,
                         'bail_amount': bail_amount}
            bail_info_page.append(bail_dict)
        
        # Check if bail has been posted
        check_posted = pdf.pq(query_line(p, [x0_bailPostingStatus, y_bottom, x1_bailPostingStatus, y_top])).text()
        bail_first_posted_amount = 0
        bail_first_posted_date = ''
        bail_posted_list = []
        if 'Posted' in check_posted:
            # Occasionally more than one date is listed; grab info for all non-duplicate entries
            bail_posted_date_list = pdf.pq(query_line(p, [x0_postingDate, y_bottom, x1_postingDate + 5, y_top])).text().split(' ')
            bail_posted_date_list = list(set(bail_posted_date_list))
            
            for postedDate in bail_posted_date_list:
                # Use the bail amount and percentage set immediately prior to the bail posted date (last item in list of prior actions)
                priorInfo = [d for d in bail_info_page if datetime.strptime(d['bail_date'], dateFormat) < datetime.strptime(postedDate, dateFormat)][-1]
                bailPosted = 0.01 * priorInfo['bail_percentage'] * priorInfo['bail_amount']
                if bail_first_posted_amount == 0:
                    bail_first_posted_amount = bailPosted
                if bail_first_posted_date == '':
                    bail_first_posted_date = postedDate
                bail_posted_list.append({'date': postedDate, 'amount': bailPosted})
        
        bail_entries_all.extend(bail_info_page)
        bail_posted_all.extend(bail_posted_list)
    
    # For validation, check that all entries are unique
    entries_seen = []
    for entry in bail_entries_all:
        d = entry.copy()
        d.pop('bail_date')
        s = ' '.join([str(v) for v in d.values()])
        entries_seen.append(s)
    entries_seen_unique = list(set(entries_seen))
    if len(entries_seen_unique) != len(entries_seen):
        print("Warning: duplicate entries found, which may indicate an issue with how bail_action was parsed. Other bail information is probably okay, but may want to double check")

    return bail_entries_all, bail_first_posted_amount, bail_first_posted_date, bail_posted_all


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

        # Handles edge case where if bail is set twice in a case it takes the earlier one
        if magistrate != '':
            break

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

    if magistrate == '':
        magistrate = 'No Magistrate Found'

    return magistrate


def get_offense_type(statute):
    """ Parse statute information and get offense type 
        input: (list of strings) statute output of 'get_charges'
        output: (list of strings) offense type 
    """

    statute = filter(lambda x: x != '', statute)

    offense_type = []

    # find title and chapter numbers of offenses
    for item in statute:
        statute_idx = item.replace(".", " ")
        statute_idx = statute_idx.replace("-", " ")
        statute_idx = statute_idx.replace('§', " ")
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
        x3_1 = float(info_3.attr('x1')) + 10
        # Statute number left
        # info_4 = pdf.pq(query_contains_line(p, 'Statute'))
        x4_0 = x1_0 - 100  # float(info_4.attr('x0'))

        charges, date, statutes = offense(pdf, p, y2_1, y1_0, x1_0, x3_0, x3_1, x4_0)
        chargeList.extend(charges)
        statuteList.extend(statutes)

    offense_type = get_offense_type(statuteList)
    return chargeList, date, statuteList, offense_type


def get_dob(pdf, pages):
    p = pages[0]
    info_1 = pdf.pq(query_contains_line(p, 'Date Of Birth:'))
    x1_1 = float(info_1.attr('x1'))
    y1_0 = float(info_1.attr('y0'))
    y1_1 = float(info_1.attr('y1'))
    info_2 = pdf.pq(query_contains_line(p, 'City/State/Zip:'))
    x2_0 = float(info_2.attr('x0'))

    dob = pdf.pq(query_line(p, [x1_1, y1_0 - 1, x2_0, y1_1 + 1])).text()

    return dob


def get_status(pdf, pages):
    """ Return case status and arrest date"""

    p = pages[0]
    info_1 = pdf.pq(query_contains_line(p, 'Case Status:'))
    x1_1 = float(info_1.attr('x1'))
    y1_0 = float(info_1.attr('y0'))
    y1_1 = float(info_1.attr('y1'))
    info_2 = pdf.pq(query_contains_line(p, 'Status Date'))
    x2_0 = float(info_2.attr('x0'))
    info_3 = pdf.pq(query_contains_line(p, 'Arrest Date:'))
    x3_1 = float(info_3.attr('x1'))

    case_status = pdf.pq(query_line(p, [x1_1, y1_0 - 1, x2_0, y1_1 + 1])).text()
    arrest_date = pdf.pq(query_line(p, [x3_1, y1_0 - 1, x3_1 + 200, y1_1 + 1])).text()

    return case_status, arrest_date


def get_prelim_hearing(pdf, pages):
    """ Return preliminary arraignment date and time """

    p = pages[0]
    info_1 = pdf.pq(query_contains_box(p, 'Schedule Start Date'))
    x1 = float(info_1.attr('x0'))
    info_2 = pdf.pq(query_contains_box(p, 'Start Time'))
    x2 = float(info_2.attr('x0'))
    info_3 = pdf.pq(query_contains_line(p, 'Room'))
    x3 = float(info_3.attr('x0'))
    info_y = pdf.pq(query_contains_box(p, 'Preliminary Arraignment'))
    y1 = float(info_y.attr('y1'))

    prelim_hearing_date = pdf.pq(query_line(p, [x1, y1 - 20, x2, y1 + 5])).text()
    prelim_hearing_time = pdf.pq(query_line(p, [x2, y1 - 20, x3, y1 + 5])).text()

    return prelim_hearing_date, prelim_hearing_time


def get_arresting_officer(pdf, pages):
    """ Return arresting officer """
    p = pages[0]
    info_1 = pdf.pq(query_contains_line(p, 'Arresting Officer:'))
    arresting_officer = info_1.text().split('Arresting Officer:')[1].strip()

    return arresting_officer
