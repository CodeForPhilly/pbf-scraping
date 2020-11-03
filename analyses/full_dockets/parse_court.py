#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Oct 20 19:28:32 2020

@author: bmargalef
"""

import pdfquery
import os
import argparse
import pandas as pd


def parse_pdf(path_folder, filename):
    ''' Parse sex and race from court summary PDF '''
    
    pdf = pdfquery.PDFQuery(path_folder+filename)
    pdf.load()

    info_sex = pdf.pq('LTTextLineHorizontal:contains("Sex:")').text()
    info_race = pdf.pq('LTTextLineHorizontal:contains("Race:")').text()
    result = {}
    result['docket_no'] = filename.split('.pdf')[0]
    result['sex'] = info_sex.split('Sex:')[1]
    result['race'] = info_race.split('Race: ')[1]
 
    return result


def main(folder, output_name):
    parsed_results = []
    for i, file in enumerate(os.listdir(folder)[0:10]): # Why just the first ten?
        try:
            print(i, file)
            data = parse_pdf(folder, file)
            parsed_results.append(data)
        except:
            print('Failed: ',file)
        

    final = pd.DataFrame(parsed_results)
    final.to_csv(output_name+'.csv', index=False)
    
    return


if __name__ == "__main__":
    cwd = os.path.join(os.path.dirname(__file__), '\test\sample')
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('-p','--path_folder', default=cwd,
                        help='Path to folder with PDFs')
    parser.add_argument('-o','--output_name', default='output_court',
                        help='Path to folder with PDFs')

    args = parser.parse_args()
    main(args.path_folder,args.output_name)
