from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
import scrape1
import requests
import time
import os


def download(link,docketNumber):
    #os.system('curl "'+link+'" >> downloads\\'+docketNumber+".pdf")
    dir="D:\\Code for Philly\\PBF\\downloads\\"
    r_pdf = requests.get(link, headers={"User-Agent": "ParsingThing"})
    with open(dir+docketNumber+'.pdf', 'wb') as f:
        f.write(r_pdf.content)

def main():
    #docketNumbers=["MC-51-CR-0016015-2020","MC-51-CR-0016016-2020","MC-51-CR-0016017-2020","MC-51-CR-0016018-2020"]
    scrape1.main()
    docketNumbers=scrape1.listOfDocketNumbers
    print(docketNumbers)
    fireFoxOptions = webdriver.FirefoxOptions()
    fireFoxOptions.headless=True
    driver = webdriver.Firefox(firefox_options=fireFoxOptions)
    driver.maximize_window()
    links=[]
    count=0
    for item in docketNumbers:
        try:
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
            final_click=driver.find_element_by_xpath("/html/body/form/div[3]/div[2]/table/tbody/tr/td/div[2]/div/div[3]/table/tbody/tr/td[1]/div/div/table/tbody/tr[1]/td/table/tbody/tr/td/a")
            hover=ActionChains(driver).move_to_element(driver.find_element_by_xpath("/html/body/form/div[3]/div[2]/table/tbody/tr/td/div[2]/div/div[3]/table/tbody/tr/td[1]/div/table/tbody/tr/td/table/tbody/tr/td/a/img")).move_to_element(final_click)
            hover.perform()
            links.append(final_click.get_attribute("href"))
            count += 1
            end=time.time()
            start1=time.time()
            download(final_click.get_attribute("href"),"-".join(docketNumber))
            end1=time.time()
            print(count)
            print("-".join(docketNumber))
            print("selenium time:"+str(end-start))
            print("download time:" + str(end1- start1))
        except:
            print("could not download docket:"+"-".join(docketNumber))

    driver.close()
    print(links)

if __name__=="__main__":
    main()
