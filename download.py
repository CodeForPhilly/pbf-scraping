from selenium.webdriver.common.action_chains import ActionChains
from selenium import webdriver
from selenium.webdriver.support.ui import Select
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import scrape1
import requests
import time
import os


def download(link1,link2,docketNumber):
    #os.system('curl "'+link+'" >> downloads\\'+docketNumber+".pdf")
    dir1="D:\\Code for Philly\\Downloads\\docket\\"
    dir2="D:\\Code for Philly\\Downloads\\court\\"
    r_pdf = requests.get(link1, headers={"User-Agent": "ParsingThing"})
    with open(dir1+docketNumber+'.pdf', 'wb') as f:
        f.write(r_pdf.content)
    r_pdf = requests.get(link2, headers={"User-Agent": "ParsingThing"})
    with open(dir2+docketNumber+'.pdf', 'wb') as f:
        f.write(r_pdf.content)

def fetch():
    scrape1.main()
    return scrape1.listOfDocketNumbers

def fetch1():
    file="august.csv"
    f = open(file, 'r')
    lines = f.readlines()
    new=[]
    for line in lines:
        new.append(line[:-1])
    print(new)
    return new[1:]

def main():
    #docketNumbers=["MC-51-CR-0016015-2020","MC-51-CR-0016016-2020","MC-51-CR-0016017-2020","MC-51-CR-0016018-2020"]
    #fetch1()
    docketNumbers=fetch1()
    print(len(docketNumbers))
    print(docketNumbers)
    fireFoxOptions = webdriver.FirefoxOptions()
    fireFoxOptions.headless=True
    #driver = webdriver.Firefox(options=fireFoxOptions)
    chrome_options = Options()
    # chrome_options.add_argument("--disable-extensions")
    # chrome_options.add_argument("--disable-gpu")
    # chrome_options.add_argument("--no-sandbox") # linux only
    chrome_options.add_argument("--headless")
    driver=webdriver.Chrome(options=chrome_options)
    driver.maximize_window()
    links=[]
    count=0
    for item in docketNumbers:
        try:

            if(count%25==0 and count>0):
                print("\nSleeping for 600 seconds")
                time.sleep(600)
                print("wait complete\n")
            docketNumber=item.split("-")
            start=time.time()
            driver.get("https://ujsportal.pacourts.us/DocketSheets/MC.aspx")
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            driver.find_element_by_id("ctl00_ctl00_ctl00_cphMain_cphDynamicContent_cphDynamicContent_docketNumberCriteriaControl_docketNumberControl_mddlCourt" ).send_keys(docketNumber[0])
            driver.find_element_by_id("ctl00_ctl00_ctl00_cphMain_cphDynamicContent_cphDynamicContent_docketNumberCriteriaControl_docketNumberControl_mtxtCounty").send_keys(docketNumber[1])
            drop_down=Select(driver.find_element_by_id("ctl00_ctl00_ctl00_cphMain_cphDynamicContent_cphDynamicContent_docketNumberCriteriaControl_docketNumberControl_mddlDocketType"))
            drop_down.select_by_visible_text(docketNumber[2])
            driver.find_element_by_id("ctl00_ctl00_ctl00_cphMain_cphDynamicContent_cphDynamicContent_docketNumberCriteriaControl_docketNumberControl_mtxtSequenceNumber").send_keys(docketNumber[3])
            driver.find_element_by_id("ctl00_ctl00_ctl00_cphMain_cphDynamicContent_cphDynamicContent_docketNumberCriteriaControl_docketNumberControl_mtxtYear").send_keys(docketNumber[4])
            driver.find_element_by_id("ctl00_ctl00_ctl00_cphMain_cphDynamicContent_cphDynamicContent_docketNumberCriteriaControl_searchCommandControl").click()
            docketDocument=driver.find_element_by_xpath("/html/body/form/div[3]/div[2]/table/tbody/tr/td/div[2]/div/div[3]/table/tbody/tr/td[1]/div/div/table/tbody/tr[1]/td/table/tbody/tr/td/a")
            courtSummary=driver.find_element_by_xpath("/html/body/form/div[3]/div[2]/table/tbody/tr/td/div[2]/div/div[3]/table/tbody/tr/td[1]/div/div/table/tbody/tr[2]/td/table/tbody/tr/td/a")
            hover=ActionChains(driver).move_to_element(driver.find_element_by_xpath("/html/body/form/div[3]/div[2]/table/tbody/tr/td/div[2]/div/div[3]/table/tbody/tr/td[1]/div/table/tbody/tr/td/table/tbody/tr/td/a/img")).move_to_element(docketDocument)
            hover.perform()
            end=time.time()
            start1=time.time()
            download(docketDocument.get_attribute("href"),courtSummary.get_attribute("href"),"-".join(docketNumber))
            end1=time.time()
            print(count)
            print("-".join(docketNumber))
            print("selenium time:"+str(end-start))
            print("download time:" + str(end1- start1))
            count += 1
        except Exception as e:
            print("could not download docket:"+"-".join(docketNumber))
            print(e)
            count += 1
    driver.close()

if __name__=="__main__":
    main()
    #fetch1()
