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



def parse_pdf(filename):
    pdf = pdfquery.PDFQuery(filename)
    pdf.load()

    info_sex = pdf.pq('LTTextLineHorizontal:contains("Sex:")').text()
    info_race = pdf.pq('LTTextLineHorizontal:contains("Race:")').text()
    result = {}
    result['sex'] = info_sex.split('Sex:')[1]
    result['race'] = info_race.split('Race: ')[1]
 
    return result


def main(folder, output_name):
    parsed_results = []
    for enu,file in enumerate(os.listdir(folder)):
        try:
            print(enu, file)
            data = parse_pdf(path_folder+file)
            parsed_results.append(data)
        except:
            print('Failed: ',file)
        

    final = pd.DataFrame(parsed_results)
    final.to_csv(output_name+'.csv', index=False)

if __name__ == "__main__":
    path_folder = '/home/bmargalef/MEGA/pbf-scraping-pdf_scraping/sampledockets/sampledockets/downloads/court/'
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('-p','--path_folder', default= path_folder,
                        help='Path to folder with PDFs')
    parser.add_argument('-o','--output_name', default= 'output_court',
                        help='Path to folder with PDFs')

    args = parser.parse_args()
    main(args.path_folder,args.output_name)
