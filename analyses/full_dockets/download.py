from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
import scrape1
import requests
import time
import os
import pandas as pd
from funcs_parse import *
from parse_docket import *


def download(docket_link, court_link, docketNumber):
    #os.system('curl "'+link+'" >> downloads\\'+docketNumber+".pdf")
    dockets_path = "analyses/full_dockets/tmp/dockets/"
    court_path   = "analyses/full_dockets/tmp/court/"
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
    file = "analyses/full_dockets/august_sm.csv"
    f = open(file, 'r')
    lines = f.readlines()
    new=[]
    for line in lines:
        new.append(line[:-1])
    print(new)
    return new

def main():
    #docketNumbers=["MC-51-CR-0016015-2020","MC-51-CR-0016016-2020","MC-51-CR-0016017-2020","MC-51-CR-0016018-2020"]
    #fetch1()
    docketNumbers=fetch1()
    print(len(docketNumbers))
    print(docketNumbers)
    fireFoxOptions = webdriver.FirefoxOptions()
    fireFoxOptions.headless=True
    fireFoxOptions.add_argument('--no-sandbox')
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
    final.to_csv('tmp/test.csv', index=False)

if __name__=="__main__":
    main()
    #fetch1()
