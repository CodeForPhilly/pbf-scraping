import pdfquery
import os
import argh
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


@argh.arg("--testdir", help="Directory where test files are located")
@argh.arg("--outfile", help="Filename for output file [outfile].csv")
def test_scrape_and_parse(testdir='', outfile='court_summary_test'):
    ''' Test scrape_and_parse
    
        TODO: generate test set of pdf:csv pairs and update this function to
        automatically compare the parsed output to the validated output, instead
        of dumping into csv for manual checking'''

    if testdir == '':
        cwd = os.path.dirname(__file__)
        testdir = os.path.join(cwd,'tmp/court/')
        savedir = os.path.join(cwd,'tmp/')

    parsedSummaries = []
    countAll = 0
    countFailed = 0
    for i, file in enumerate(os.listdir(testdir)):
        if (os.path.splitext(file)[1] == '.pdf'):
            countAll += 1
            try:
                print('{0}\t {1}'.format(i, file))
                data = scrape_and_parse_pdf(os.path.join(testdir, file))
                parsedSummaries.append(data)
            except:
                print('Failed: {0}'.format(file))
                countFailed += 1
    print('{0}/{1} failed'.format(countFailed, countAll))

    final = pd.DataFrame(parsedSummaries)
    final.to_csv(os.path.join(savedir, '{0}.csv'.format(outfile)), index=False)
    

if __name__ == "__main__":
    argh.dispatch_command(test_scrape_and_parse)
