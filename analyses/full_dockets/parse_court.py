import pdfquery
import os
import argparse
import pandas as pd


def scrape_and_parse_pdf(filepath):
    """ Extract race and sex from court summary PDF file.
        Parameters:
            filepath (path): full path to PDF file
        Returns:
            parsedData (dictionary): column_name:key_value pairs
        """
    
    pdf = pdfquery.PDFQuery(filepath)
    pdf.load()

    info_sex = pdf.pq('LTTextLineHorizontal:contains("Sex:")').text()
    info_race = pdf.pq('LTTextLineHorizontal:contains("Race:")').text()

    parsedData = {}
    parsedData['docket_no'] = os.path.splitext(os.path.basename(filepath))[0]
    parsedData['sex'] = info_sex.split('Sex:')[1].strip()
    parsedData['race'] = info_race.split('Race:')[1].strip()  

    return parsedData


def test_scrape_and_parse(testdir, output_name):
    ''' Test scrape_and_parse
    
        TODO: generate test set of pdf:csv pairs and update this function to
        automatically compare the parsed output to the validated output, instead
        of dumping into csv for manual checking'''

    parsedResults = []
    countAll = 0
    countFailed = 0
    for i, file in enumerate(os.listdir(testdir)):
        countAll += 1
        try:
            print(i)
            data = scrape_and_parse_pdf(os.path.join(testdir, file))
            parsedResults.append(data)
        except:
            print('Failed: {0}'.format(file))
            countFailed += 1
    print('{0}/{1} failed'.format(countFailed, countAll))

    final = pd.DataFrame(parsedResults)
    final.to_csv(output_name+'.csv', index=False)
    

if __name__ == "__main__":
    testdir = os.path.join(os.path.dirname(__file__),'tmp/court')
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('-p','--path_folder', default=testdir,
                        help='Path to folder with PDFs')
    parser.add_argument('-o','--output_name', default='output_court',
                        help='Path to folder with PDFs')

    args = parser.parse_args()
    test_scrape_and_parse(args.path_folder,args.output_name)
