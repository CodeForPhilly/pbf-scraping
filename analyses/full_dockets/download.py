from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from sqlalchemy import create_engine
import requests
import time
import os
import sys
import pandas as pd
import argh
import parse_docket as docket
import parse_court as court

DOCKET_BUFFER = 50  # number of dockets before sleep
SLEEP_TIME = 600    # seconds


def download_and_parse(docketLink, courtLink, docketNumber):
    """ Download, write to PDF, and parse the docket and court summmary 
        corresponding to a particular docket number
        Returns the parsed information from each file as dictionaries """
        
    cwd = os.path.dirname(__file__)
    docketDir = os.path.join(cwd, "tmp/dockets/")
    courtDir = os.path.join(cwd, "tmp/court/")
    docketFile = os.path.join(docketDir, '{0}.pdf'.format(docketNumber))
    courtFile = os.path.join(courtDir, '{0}.pdf'.format(docketNumber))

    # Download and parse docket
    download_pdf(docketLink, docketFile)
    docketText = docket.scrape_pdf(docketFile)
    parsedDocket = docket.parse_pdf(docketFile, docketText)

    # Download and parse court summary
    download_pdf(courtLink, courtFile)
    parsedCourt = court.scrape_and_parse_pdf(courtFile)
        
    return parsedDocket, parsedCourt


def download_pdf(link, filepath):
    """ Save PDF at given URL link to given filepath """
    
    r_pdf = requests.get(link, headers={"User-Agent": "ParsingThing"})
    with open(filepath, 'wb') as f:
        f.write(r_pdf.content)
    

def fetch_docket_numbers(aws_access_key_id, aws_secret_access_key):
    """ Fetch and return list of at most 50 docket numbers from new_criminal_filings
        in the Athena database """
    
    config = {"AWS_ACCESS_KEY_ID": aws_access_key_id,
              "AWS_SECRET_ACCESS_KEY": aws_secret_access_key,
              "REGION_NAME": "us-east-1",
              "SCHEMA_NAME": "ncf",
              "S3_STAGING_DIR": "s3://pbf-athena-1/"}
    con_str = "awsathena+rest://{AWS_ACCESS_KEY_ID}:{AWS_SECRET_ACCESS_KEY}@athena.{REGION_NAME}.amazonaws.com:443/{SCHEMA_NAME}?s3_staging_dir={S3_STAGING_DIR}".format(
    **config)

    engine = create_engine(con_str)
    con = engine.connect()

    docket_id_query = 'SELECT DISTINCT A.docket_number FROM new_criminal_filings as A LEFT OUTER JOIN dockets_parsed_raw as B on A.docket_number = B.docket_no WHERE B.docket_no is null LIMIT 50'
    query_result = pd.read_sql(docket_id_query, con)
    docket_list = query_result['docket_number'].to_list()
    
    return docket_list


def get_pdf_links(docketstr, driver=None):
    ''' Get docket and court summary pdf file links from website.
        If web driver not provided, this will initialize and close one. '''

    closeDriver = False
    if not driver:
        closeDriver = True
        driver = initialize_webdriver()

    docketNumber = docketstr.split("-")
    
    elementBase = "ctl00_ctl00_ctl00_cphMain_cphDynamicContent_cphDynamicContent_docketNumberCriteriaControl"
    driver.get("https://ujsportal.pacourts.us/DocketSheets/MC.aspx")
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    driver.find_element_by_id("{0}_docketNumberControl_mddlCourt".format(elementBase)).send_keys(docketNumber[0])
    driver.find_element_by_id("{0}_docketNumberControl_mtxtCounty".format(elementBase)).send_keys(docketNumber[1])
    driver.find_element_by_id("{0}_docketNumberControl_mddlDocketType".format(elementBase)).send_keys(docketNumber[2])
    driver.find_element_by_id("{0}_docketNumberControl_mtxtSequenceNumber".format(elementBase)).send_keys(docketNumber[3])
    driver.find_element_by_id("{0}_docketNumberControl_mtxtYear".format(elementBase)).send_keys(docketNumber[4])
    driver.find_element_by_id("{0}_searchCommandControl".format(elementBase)).click()
    docketDocument = driver.find_element_by_xpath("/html/body/form/div[3]/div[2]/table/tbody/tr/td/div[2]/div/div[3]/table/tbody/tr/td[1]/div/div/table/tbody/tr[1]/td/table/tbody/tr/td/a")
    courtSummary = driver.find_element_by_xpath("/html/body/form/div[3]/div[2]/table/tbody/tr/td/div[2]/div/div[3]/table/tbody/tr/td[1]/div/div/table/tbody/tr[2]/td/table/tbody/tr/td/a")
    hover = ActionChains(driver).move_to_element(driver.find_element_by_xpath("/html/body/form/div[3]/div[2]/table/tbody/tr/td/div[2]/div/div[3]/table/tbody/tr/td[1]/div/table/tbody/tr/td/table/tbody/tr/td/a/img")).move_to_element(docketDocument)
    hover.perform()

    docketLink = docketDocument.get_attribute("href")
    courtLink = courtSummary.get_attribute("href")
    
    if closeDriver:
        driver.close()
    
    return docketLink, courtLink


def initialize_webdriver():
    """ Initialize headless Firefox webdriver """
    
    fireFoxOptions = webdriver.FirefoxOptions()
    fireFoxOptions.headless = True
    driver = webdriver.Firefox(options=fireFoxOptions)
    driver.maximize_window() 
    
    return driver


@argh.arg("--docket", help="Full docket number", default='')
@argh.arg("--awsid", help="AWS ID", default='')
@argh.arg("--awskey", help="AWS key", default='')
def main(docket='', awsid='', awskey=''):
    ''' Fetch all new docket numbers and download, parse, and save .csv for
        docket and court summary corresponding to each number.
        Can be used either with a specific docket number or with the AWS
        Athena database id-key pair. '''
    
    # Check that one of the two use cases is met
    assert (docket != '') or (awsid != '' and awskey != ''), print('Please specify either one docket number or AWS information (id-key pair) to fetch docket list')

    if docket != '':
        # Use single docket if docket number provided
        docketList = [docket]
        print(docketList)
    else:
        # Fetch list of docket numbers from AWS Athena database
        docketList = fetch_docket_numbers(awsid, awskey)
        print('{0} docket numbers found'.format(len(docketList)))

    driver = initialize_webdriver()
        
    parsedDockets = []
    parsedCourts = []
    failedDockets = []
    
    # Download and parse each file in the list
    for i, docketstr in enumerate(docketList):

        # To keep server from kicking us out, don't send too many requests at once
        if (i % DOCKET_BUFFER == 0 and i > 0):
            print("\nSleeping for {0} seconds...".format(SLEEP_TIME))
            time.sleep(SLEEP_TIME)
            print("wait complete\n")
        
        # Navigate to docket and court pdf files, then download and parse
        try:
            docketLink, courtLink = get_pdf_links(docketstr, driver=driver)
            docketDict, courtDict = download_and_parse(docketLink, courtLink, docketstr)

            if docketDict != {} and courtDict != {}:
                parsedDockets.append(docketDict)
                parsedCourts.append(courtDict)
            else:
                failedDockets.append(docketstr)
        except Exception as e:
            print("Exception for docket {0}:".format(docketstr))
            print(e)
            failedDockets.append(docketstr)
            
    driver.close()               
    
    # Save docket and court summary data to two .csv files
    dirname = os.path.dirname(__file__)
    tmpdir = "tmp/parsed_docket_data"
    os.mkdir(os.path.join(dirname, tmpdir))
    tag = time.strftime("%Y-%m-%d-%H%M%S")
    
    docketName = "{0}/docket-data-{1}.csv".format(tmpdir, tag)
    courtName = "{0}/court-data-{1}.csv".format(tmpdir, tag)
    docketPath = os.path.join(dirname, docketName)
    courtPath = os.path.join(dirname, courtName)
    docketDF = pd.DataFrame(parsedDockets)
    courtDF = pd.DataFrame(parsedDockets)
    docketDF.to_csv(docketPath, index=False)
    courtDF.to_csv(courtPath, index=False)
    
    if len(failedDockets) > 0:
        print("{0} dockets could not be downloaded/parsed:".format(len(failedDockets)))
        print(", ".join(failedDockets))


def test_download_and_parse(testfile='', outfile='download_test'):
    ''' Test download function on .csv containing [docket_link, court_link, docket_no] '''

    cwd = os.path.dirname(__file__)
    savedir = os.path.join(cwd,'tmp/')
    if testfile == '':
        testname = 'download_links_test.csv'
        testfile = os.path.join(savedir, testname)

    testDF = pd.read_csv(testfile)

    parsedDockets = []
    countAll = 0
    countFailed = 0
    for i, row in testDF.iterrows():
        countAll += 1
        try:
            print(i)
            data = download_and_parse(row['docket_link'], row['court_link'], row['docket_no'])
            if data != {}:
                parsedDockets.append(data)
        except:
            print('Failed: {0}'.format(row['docket_no']))
            countFailed += 1
    print('{0}/{1} failed'.format(countFailed, countAll))

    final = pd.DataFrame(parsedDockets)
    final.to_csv(os.path.join(savedir, '{0}.csv'.format(outfile)), index=False)    


if __name__=="__main__":
    argh.dispatch_command(main)
