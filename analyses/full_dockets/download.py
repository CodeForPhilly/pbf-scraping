from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
import requests
import time
import os
import sys
import pandas as pd
from sqlalchemy import create_engine
import parse_docket as docket
#import parse_court as court


def download(docket_link, court_link, docketNumber):
    ''' Download, write to PDF, and parse the docket and court summmary 
        corresponding to a particular docket number and return the parsed docket '''
        
    dirname = os.path.dirname(__file__)
    dockets_path = os.path.join(dirname, "tmp/dockets/")
    court_path = os.path.join(dirname, "tmp/court/")
    dockets_file = dockets_path + docketNumber+'.pdf'
    court_file   = court_path + docketNumber+'.pdf'

    # Download and parse docket
    r_pdf = requests.get(docket_link, headers={"User-Agent": "ParsingThing"})
    with open(dockets_file, 'wb') as f:
        f.write(r_pdf.content)
    text_d = docket.scrape_pdf(dockets_file)
    parse_d = docket.parse_pdf(dockets_file, text_d)

    # Download and parse court summary
    r_pdf = requests.get(court_link, headers={"User-Agent": "ParsingThing"})
    with open(court_file, 'wb') as f:
        f.write(r_pdf.content)
    #parse_c = court.parse_pdf(court_file) # Need to change parse_court to accept court file
    
    return parse_d


def fetch_docket_numbers(aws_access_key_id, aws_secret_access_key):
    ''' Fetch and return list of at most 50 docket numbers from new_criminal_filings
        in the Athena database '''
    
    config = {
        "AWS_ACCESS_KEY_ID": aws_access_key_id,
        "AWS_SECRET_ACCESS_KEY": aws_secret_access_key,
        "REGION_NAME": "us-east-1",
        "SCHEMA_NAME": "ncf",
        "S3_STAGING_DIR": "s3://pbf-athena-1/"
    }
    con_str = "awsathena+rest://{AWS_ACCESS_KEY_ID}:{AWS_SECRET_ACCESS_KEY}@athena.{REGION_NAME}.amazonaws.com:443/{SCHEMA_NAME}?s3_staging_dir={S3_STAGING_DIR}".format(
    **config)

    engine = create_engine(con_str)
    con = engine.connect()

    docket_id_query = 'SELECT DISTINCT A.docket_number FROM new_criminal_filings as A LEFT OUTER JOIN dockets_parsed_raw as B on A.docket_number = B.docket_no WHERE B.docket_no is null LIMIT 50'
    query_result = pd.read_sql(docket_id_query, con)
    docket_list = query_result['docket_number'].to_list()
    
    return docket_list


def main():
    ''' Fetch all new docket numbers and download, parse, and save .csv for
        docket and court summary corresponding to each number '''
    
    docketNumbers = fetch_docket_numbers(str(sys.argv[1]), str(sys.argv[2]))
    print('docketNumber count: ' + str(len(docketNumbers)))
    print(docketNumbers)
    
    # Initialize web driver
    fireFoxOptions = webdriver.FirefoxOptions()
    fireFoxOptions.headless=True
    driver = webdriver.Firefox(options=fireFoxOptions)
    driver.maximize_window()
    
    count = 0
    parsed_results = []
    for item in docketNumbers:
        # Navigate to docket and court pdf files, then download and parse
        try:
            if (count%50==0 and count>0):
                print("\nSleeping for 600 seconds... ")
                time.sleep(600)
                print("wait complete\n")

            docketNumber = item.split("-")
            elementBase = "ctl00_ctl00_ctl00_cphMain_cphDynamicContent_cphDynamicContent_docketNumberCriteriaControl"
            t0 = time.time()
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
            count += 1
            t1 = time.time()
            
            data = download(docketDocument.get_attribute("href"),courtSummary.get_attribute("href"),"-".join(docketNumber))
            parsed_results.append(data)
            print('results count: ' + str(len(parsed_results)))
            print('results.last: ' + str(parsed_results[-1]))
            t2 = time.time()
            
            print(count)
            print("-".join(docketNumber))
            print("selenium time:" + str(t1-t0))
            print("download time:" + str(t2-t1))
            
        except Exception as e:
            print("could not download docket:"+"-".join(docketNumber))
            print(e)

    driver.close()

    # Save docket data to .csv
    final = pd.DataFrame(parsed_results)
    dirname = os.path.dirname(__file__)
    os.mkdir(os.path.join(dirname, "tmp/parsed_docket_data"))
    filepath = os.path.join(
        dirname, "tmp/parsed_docket_data/docket-data-" + time.strftime("%Y-%m-%d-%H%M%S") + ".csv")
    final.to_csv(filepath, index=False)

    return


if __name__=="__main__":
    #main()
    #docket_link = 'https://ujsportal.pacourts.us/DocketSheets/CPReport.ashx?docketNumber=MC-51-CR-0021093-2020&dnh=T5sMlImSwJL%2fHGYhgVW1Bw%3d%3d'
    #court_link = 'https://ujsportal.pacourts.us/DocketSheets/CourtSummaryReport.ashx?docketNumber=MC-51-CR-0021093-2020&dnh=T5sMlImSwJL%2fHGYhgVW1Bw%3d%3d'
    #docket_number = 'MC-51-CR-0021093-2020'
    docket_link = 'https://ujsportal.pacourts.us/DocketSheets/CPReport.ashx?docketNumber=MC-51-CR-0021092-2020&dnh=opCBR5L87X8YHtI1L%2bEowA%3d%3d'
    court_link = 'https://ujsportal.pacourts.us/DocketSheets/CourtSummaryReport.ashx?docketNumber=MC-51-CR-0021092-2020&dnh=opCBR5L87X8YHtI1L%2bEowA%3d%3d'
    docket_number = 'MC-51-CR-0021092-2020'
    
    parsed = download(docket_link, court_link, docket_number)
    for key, value in parsed.items():
        print("{0}:\t {1}".format(key, value))
