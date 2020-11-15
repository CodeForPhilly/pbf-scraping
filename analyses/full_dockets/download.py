from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from sqlalchemy import create_engine
import requests
import time
import os
import sys
import pandas as pd
import parse_docket as docket
import parse_court as court

DOCKET_BUFFER = 50  # number of dockets before sleep
SLEEP_TIME = 600    # seconds


def download_and_parse(docketLink, courtLink, docketNumber):
    ''' Download, write to PDF, and parse the docket and court summmary 
        corresponding to a particular docket number
        Returns the parsed information from both files as a single dictionary '''
        
    cwd = os.path.dirname(__file__)
    docketDir = os.path.join(cwd, "tmp/dockets/")
    courtDir = os.path.join(cwd, "tmp/court/")
    docketFile = os.path.join(docketDir, '{0}.pdf'.format(docketNumber))
    courtFile = os.path.join(courtDir, '{0}.pdf'.format(docketNumber))

    # Download and parse docket
    r_pdf = requests.get(docketLink, headers={"User-Agent": "ParsingThing"})
    with open(docketFile, 'wb') as f:
        f.write(r_pdf.content)
    parsedDocket = docket.scrape_and_parse_pdf(docketFile)

    # Download and parse court summary
    r_pdf = requests.get(courtLink, headers={"User-Agent": "ParsingThing"})
    with open(courtFile, 'wb') as f:
        f.write(r_pdf.content)
    parsedCourt = court.scrape_and_parse_pdf(courtFile) # Need to change parse_court to accept court file
    
    # Add court summary data (sex and race) to, double-checking docket number
    assert parsedDocket['docket_no'] == parsedCourt['docket_no'], "docket file and court summary file docket numbers don't match"
    parsedDocket.update(parsedCourt)
    
    return parsedDocket


def fetch_docket_numbers(aws_access_key_id, aws_secret_access_key):
    ''' Fetch and return list of at most 50 docket numbers from new_criminal_filings
        in the Athena database '''
    
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


def get_pdf_links(driver, docketstr):
    ''' Get docket and court summary pdf file links from website '''

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
    
    return docketLink, courtLink


def process_docket(docketstr, driver=None):
    ''' Given a docket number, find, download, scrape, and parse the corresponding 
        docket and court summary files, returning the parsed data as a dictionary '''
        
    if not driver:
        driver = initialize_web_driver()      

    docketLink, courtLink = get_pdf_links(driver, docketstr)
    dataDict = download_and_parse(docketLink, courtLink, docketstr)    
    
    return dataDict
    

def initialize_web_driver():
    ''' Initialize and return the web driver object '''
    
    fireFoxOptions = webdriver.FirefoxOptions()
    fireFoxOptions.headless = True
    driver = webdriver.Firefox(options=fireFoxOptions)
    driver.maximize_window()
    
    return driver


def main():
    ''' Fetch all new docket numbers and download, parse, and save .csv for
        docket and court summary corresponding to each number '''
    
    docketList = fetch_docket_numbers(str(sys.argv[1]), str(sys.argv[2]))
    print('{0} docket numbers found'.format(len(docketList)))
    
    # Initialize web driver
    driver = initialize_web_driver()   

    # Navigate to docket and court pdf files, then download and parse
    parsedData = []
    for i, docketstr in docketList:
        if (i%DOCKET_BUFFER==0 and i>0):
            print("\nSleeping for {0} seconds...".format(SLEEP_TIME))
            time.sleep(SLEEP_TIME)
            print("wait complete\n")
            
        try:
            data = process_docket(docketstr, driver=driver)
            if data != {}:
                parsedData.append(data)
            else:
                print("warning: skipping empty/invalid docket {0}".format(docketstr))
            
        except Exception as e:
            print("could not download docket {0}".format(docketstr))
            print(e)

    driver.close()

    # Save all docket and court summary data to .csv
    dirname = os.path.dirname(__file__)
    os.mkdir(os.path.join(dirname, "tmp/parsed_docket_data"))
    filename = "tmp/parsed_docket_data/docket-data-{0}.csv".format(time.strftime("%Y-%m-%d-%H%M%S"))
    filepath = os.path.join(dirname, filename)
    
    final = pd.DataFrame(parsedData)
    final.to_csv(filepath, index=False)

    return


def test_download(testfile='', outfile='download_test'):
    ''' Test download function given csv of [docket_link, court_link, docket_no] '''

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
    #main()
    test_download()
