from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
import scrape1
import requests
import time
import os
import pandas as pd
import sys
from sqlalchemy import create_engine
from funcs_parse import *
from parse_docket import *


def download(docket_link, court_link, docketNumber):
    #os.system('curl "'+link+'" >> downloads\\'+docketNumber+".pdf")
    dirname = os.path.dirname(__file__)
    dockets_path = os.path.join(dirname, "tmp/dockets/")
    court_path = os.path.join(dirname, "tmp/court/")
    dockets_file = dockets_path + docketNumber+'.pdf'
    court_file   = court_path + docketNumber+'.pdf'

    r_pdf = requests.get(docket_link, headers={"User-Agent": "ParsingThing"})
    with open(dockets_file, 'wb') as f:
        f.write(r_pdf.content)
    text = scrape_pdf(dockets_file)
    parse = parse_pdf(dockets_file, text)
    print(parse)

    r_pdf = requests.get(court_link, headers={"User-Agent": "ParsingThing"})
    with open(court_file, 'wb') as f:
        f.write(r_pdf.content)
    return parse

def fetch():
    scrape1.main()
    return scrape1.listOfDocketNumbers

def fetch1():
    dirname = os.path.dirname(__file__)
    file = os.path.join(dirname, "august_sm.csv")
    f = open(file, 'r')
    lines = f.readlines()
    new=[]
    for line in lines:
        new.append(line[:-1])
    print(new)
    return new

def fetch2(aws_access_key_id, aws_secret_access_key):
    config = {
        "AWS_ACCESS_KEY_ID": aws_access_key_id,
        "AWS_SECRET_ACCESS_KEY": aws_secret_access_key,
        "REGION_NAME": "us-east-1",
        "SCHEMA_NAME": "ncf",
        "S3_STAGING_DIR": "s3://pbf-athena-1/"
    }
    conn_str = "awsathena+rest://{AWS_ACCESS_KEY_ID}:{AWS_SECRET_ACCESS_KEY}@athena.{REGION_NAME}.amazonaws.com:443/{SCHEMA_NAME}?s3_staging_dir={S3_STAGING_DIR}".format(
    **config)

    engine = create_engine(conn_str)
    con = engine.connect()

    docket_id_query = 'SELECT DISTINCT A.docket_number FROM new_criminal_filings as A LEFT OUTER JOIN dockets_parsed_raw as B on A.docket_number = B.docket_no WHERE B.docket_no is null LIMIT 200'
    query_result = pd.read_sql(docket_id_query, con)
    docket_list = query_result['docket_number'].to_list()
    return docket_list

def main():
    #docketNumbers=["MC-51-CR-0016015-2020","MC-51-CR-0016016-2020","MC-51-CR-0016017-2020","MC-51-CR-0016018-2020"]
    #fetch1()
    docketNumbers = fetch2(str(sys.argv[1]), str(sys.argv[2]))

    print(len(docketNumbers))
    print(docketNumbers)
    fireFoxOptions = webdriver.FirefoxOptions()
    fireFoxOptions.headless=True
    driver = webdriver.Firefox(options=fireFoxOptions)
    driver.maximize_window()
    links=[]
    count=0
    parsed_results = []
    for item in docketNumbers:
        try:
            if(count%50==0 and count>0):
                print("\nSleeping for 600 seconds")
                time.sleep(600)
                print("wait complete\n")

            docketNumber=item.split("-")
            start=time.time()
            driver.get("https://ujsportal.pacourts.us/DocketSheets/MC.aspx")
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            driver.find_element_by_id("ctl00_ctl00_ctl00_cphMain_cphDynamicContent_cphDynamicContent_docketNumberCriteriaControl_docketNumberControl_mddlCourt" ).send_keys(docketNumber[0])
            driver.find_element_by_id("ctl00_ctl00_ctl00_cphMain_cphDynamicContent_cphDynamicContent_docketNumberCriteriaControl_docketNumberControl_mtxtCounty").send_keys(docketNumber[1])
            driver.find_element_by_id("ctl00_ctl00_ctl00_cphMain_cphDynamicContent_cphDynamicContent_docketNumberCriteriaControl_docketNumberControl_mddlDocketType").send_keys(docketNumber[2])
            driver.find_element_by_id("ctl00_ctl00_ctl00_cphMain_cphDynamicContent_cphDynamicContent_docketNumberCriteriaControl_docketNumberControl_mtxtSequenceNumber").send_keys(docketNumber[3])
            driver.find_element_by_id("ctl00_ctl00_ctl00_cphMain_cphDynamicContent_cphDynamicContent_docketNumberCriteriaControl_docketNumberControl_mtxtYear").send_keys(docketNumber[4])
            driver.find_element_by_id("ctl00_ctl00_ctl00_cphMain_cphDynamicContent_cphDynamicContent_docketNumberCriteriaControl_searchCommandControl").click()
            docketDocument=driver.find_element_by_xpath("/html/body/form/div[3]/div[2]/table/tbody/tr/td/div[2]/div/div[3]/table/tbody/tr/td[1]/div/div/table/tbody/tr[1]/td/table/tbody/tr/td/a")
            courtSummary=driver.find_element_by_xpath("/html/body/form/div[3]/div[2]/table/tbody/tr/td/div[2]/div/div[3]/table/tbody/tr/td[1]/div/div/table/tbody/tr[2]/td/table/tbody/tr/td/a")
            hover=ActionChains(driver).move_to_element(driver.find_element_by_xpath("/html/body/form/div[3]/div[2]/table/tbody/tr/td/div[2]/div/div[3]/table/tbody/tr/td[1]/div/table/tbody/tr/td/table/tbody/tr/td/a/img")).move_to_element(docketDocument)
            hover.perform()
            count += 1
            end=time.time()
            start1=time.time()
            data = download(docketDocument.get_attribute("href"),courtSummary.get_attribute("href"),"-".join(docketNumber))
            parsed_results.append(data)
            print('results count: ' + str(len(parsed_results)))
            print('results.last: ' + str(parsed_results[-1]))
            end1=time.time()
            print(count)
            print("-".join(docketNumber))
            print("selenium time:"+str(end-start))
            print("download time:" + str(end1- start1))
        except Exception as e:
            print("could not download docket:"+"-".join(docketNumber))
            print(e)

    driver.close()
    final = pd.DataFrame(parsed_results)
    dirname = os.path.dirname(__file__)
    os.mkdir(os.path.join(dirname, "tmp/parsed_docket_data"))
    filepath = os.path.join(
        dirname, "tmp/parsed_docket_data/docket-data-" + time.strftime("%Y-%m-%d-%H%M%S") + ".csv")
    final.to_csv(filepath, index=False)

if __name__=="__main__":
    main()
    #fetch1()
