#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Sep 15 19:18:24 2020

@author: bmargalef
"""

import PyPDF2
import re
import numpy as np
import pdfquery


def find_pages(filename, string):
    #Find the page numbers where 'string' is found in the pdf

    pdfReader = PyPDF2.PdfFileReader(filename)
    num_pages = pdfReader.numPages
    pages = []
    for i in range(0, num_pages):
        PageObj = pdfReader.getPage(i)
        Text = PageObj.extractText()
        if re.search(string,Text):
            pages.append(i)
    return pages


def offense(pdf,page,y_bottom,y_top, x0, x1,charges,delta = 5):
    n_lines = pdf.pq('LTPage[page_index="{}"] LTTextLineHorizontal:in_bbox("{}, {}, {}, {}")'.format(page,0, y_bottom, 70, y_top)).text()
    n_lines = n_lines.split(' ')
    n = len(n_lines)
    h = 0
    if len(charges) > 0:
        h = 1
        if charges[0] == '':
            charges = []
            h = 0
    y_array_bottom = np.zeros(n)
    y_array_top = np.zeros(n)
    k = 1
    y = y_top  
    while y > y_bottom:
        y = y-delta
        info = pdf.pq('LTPage[page_index="{}"] LTTextLineHorizontal:in_bbox("{},{},{},{}")'.format(page,0,y,70,y_top)).text().split(' ')
        if len(info[0]) > 0:
            if int(info[-1]) == k:
                y_array_bottom[k-1-h] = y
            else:
                if k <= n:
                    k = k+1
    k = n+h
    y = y_bottom
    for i in range(int((y_top-y_bottom)/delta)):
        y = y+delta
        info = pdf.pq('LTPage[page_index="{}"] LTTextLineHorizontal:in_bbox("{},{},{},{}")'.format(page,0,y_bottom,70,y)).text()   
        info = (re.sub("\s+", ",", info.strip())).split(',')
        if len(info[0]) > 0:
            if k in [int(i) for i in info]  :
                y_array_top[k-1-h] = y
                k = k-1
          
    y_array_top[0] = y_top
    y_array_bottom[-1] = y_bottom
    for y0, y1 in zip(y_array_bottom,y_array_top):
        data = pdf.pq('LTPage[page_index="{}"] LTTextLineHorizontal:in_bbox("{}, {}, {}, {}")'.format(page,x0, y0, x1, y1)).text()
        charges.append(data)
    
    return charges

def bail_set(pdf,page,y_bottom,y_top, x0, x1,bail,bail_type,delta = 5):
    n_lines = pdf.pq('LTPage[page_index="{}"] LTTextLineHorizontal:in_bbox("{}, {}, {}, {}")'.format(page,0, y_bottom, 70, y_top)).text().split(' ')
    n = len(n_lines)
    y_array_bottom = np.zeros(n)
    y_array_top = np.zeros(n)
    k = 1
    y = y_bottom  
    new_y_bottom = y_bottom
    while (y < y_top) & (k<=n):
        y = y+delta
        info = pdf.pq('LTPage[page_index="{}"] LTTextLineHorizontal:in_bbox("{},{},{},{}")'.format(page,0,new_y_bottom,70,y)).text()   
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
        data = pdf.pq('LTPage[page_index="{}"] LTTextLineHorizontal:in_bbox("{}, {}, {}, {}")'.format(page,x0, y0, x1, y1)).text()
        data_cp = pdf.pq('LTPage[page_index="{}"] LTTextLineHorizontal:in_bbox("{}, {}, {}, {}")'.format(page,0, y0, x0, y1)).text()
        #bail.append(data)
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
                 
def get_bail(pdf,pages):
    bail = []
    bail_type = 1 #0: Bail Set, 1: Other e.g. Bail Posted, changed, denied...
    for p in pages:
        info_1 = pdf.pq('LTPage[page_index="{}"] LTTextLineHorizontal:contains("Filed By")'.format(p))
        x1_0 = float(info_1.attr('x0'))
        y1_0 = float(info_1.attr('y0'))
        info_2 = pdf.pq('LTPage[page_index="{}"] LTTextLineHorizontal:contains("CASE FINANCIAL INFORMATION")'.format(p))
        if len(info_2) == 0: info_2 = pdf.pq('LTPage[page_index="{}"] LTTextLineHorizontal:contains("CPCMS")'.format(p))
        y2_1 = float(info_2.attr('y1'))
        bail,bail_type = bail_set(pdf,p,y2_1,y1_0,x1_0,x1_0+200,bail,bail_type)
    return bail


def get_charges(pdf,pages):

    charges = []
    for p in pages:
        info_1 = pdf.pq('LTPage[page_index="{}"] LTTextLineHorizontal:contains("Statute Description")'.format(p))
        x1_0 = float(info_1.attr('x0'))
        y1_0 = float(info_1.attr('y0'))
        info_2 = pdf.pq('LTPage[page_index="{}"] LTTextLineHorizontal:contains("DISPOSITION SENTENCING")'.format(p))
        if len(info_2) == 0: info_2 = pdf.pq('LTPage[page_index="{}"] LTTextLineHorizontal:contains("CPCMS")'.format(p))
        y2_1 = float(info_2.attr('y1'))
        info_3 = pdf.pq('LTPage[page_index="{}"] LTTextLineHorizontal:contains("Offense Dt")'.format(p))
        x3_0 = float(info_3.attr('x0'))
        charges = offense(pdf,p,y2_1,y1_0,x1_0,x3_0,charges)
    return charges

def get_bail_re(sections):
    pattern_bailset0 = r"\s\d{2}\/\d{2}\/\d{5}(.*)Bail Set"
    pattern_bailset1 = r"\s\d{2}\/\d{2}\/\d{4} \d{1}(.*)Bail Set"
    pattern_bailset2 = r"By\d{2}\/\d{2}\/\d{5}(.*)Bail Set"
    pattern_bailset3 = r"By\d{2}\/\d{2}\/\d{5}(.*)"
    pattern_bailset4 = r"\s\d{2}\/\d{2}\/\d{5}(.*)"


    bailset =  re.findall(pattern_bailset0, sections, re.DOTALL)
    if len(bailset) == 0:
        bailset = re.findall(pattern_bailset1, sections, re.DOTALL)
        if len(bailset) == 0:
            bailset = re.findall(pattern_bailset2, sections, re.DOTALL)
            if len(bailset) == 0:
                bailset = ''
            else:
                if re.search(pattern_bailset3, bailset[0], re.DOTALL):
                    bailset = re.findall(pattern_bailset3, bailset[0], re.DOTALL)
                if re.search(pattern_bailset4, bailset[0], re.DOTALL):
                    bailset = re.findall(pattern_bailset4, bailset[0], re.DOTALL)
    else:
        if re.search('(.*)Bail Set',bailset[0],re.DOTALL):
            bailset = re.findall('(.*)Bail Set',bailset[0],re.DOTALL)
  
    return bailset