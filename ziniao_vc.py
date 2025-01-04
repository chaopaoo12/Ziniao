# -*- encoding: utf-8 -*-
'''
@File    :   ziniao_vc.py
@Time    :   2025/01/03 14:28:24
@Author  :   chaopaoo12 
@Version :   1.0
@Contact :   chaopaoo12@hotmail.com
'''

# here put the import lib
from ziniao_core import ZiniaoShop
from selenium.webdriver.common.by import By
import time
import pandas as pd


def convert(lst):
    res_dict = {}
    for i in range(0, len(lst), 2):
        res_dict[lst[i]] = lst[i + 1]
    return res_dict


def is_Porcessing(driver):
    try:
        driver.find_element(By.XPATH, "//*[contains(text(),'Processing')]")
        return True
    except:
        return False


class ZiniaoVC(ZiniaoShop):

    def prepare_env(self, browser):

        if browser['platform_name'] == '亚马逊VC-英国':
            self.site_url = 'co.uk'
            self.site_name = 'UnitedKingdom'
        elif browser['platform_name'] == '亚马逊VC-欧洲':
            self.site_url = 'eu'
            self.site_name = 'Germany'

    def set_dateset(self, dataset, report_date):
        self.url = f"https://vendorcentral.amazon.{self.site_url}/retail-analytics/dashboard/{dataset}".format()
        self.document = f'{dataset.title()}_Manufacturing_Retail_{self.site_name}_Custom_{report_date}_{report_date}'

    def run_task(self):
        self.driver.get(self.url)
        while self.driver.find_element(By.XPATH, "//kat-button[contains(@label,'Apply')]").get_attribute("disabled") == "true":
            time.sleep(10)

        self.driver.find_element(By.XPATH, "//kat-button[contains(@label,'Apply')]").click()

        while self.driver.find_element(By.XPATH, "//kat-button[contains(@label,'CSV')]").get_attribute("disabled") == "true":
            time.sleep(10)

        self.driver.find_element(By.XPATH, "//kat-button[contains(@label,'CSV')]").click()

    def run_download(self):
        self.driver.find_element(By.XPATH, "//*[contains(text(),'View and manage your downloads.')]").click()

        while is_Porcessing(self.driver):
            print("data processing, please wait...")
            time.sleep(10)

        kat_table = self.driver.find_element(By.XPATH, "//kat-table[contains(@role,'table')]")

        kat_dict = []
        for i in kat_table.find_elements(By.XPATH, "//kat-table-cell[contains(@role,'cell')]"):
            if i.text in ["Download", "Processing"]:
                kat_dict.append(i.find_element(By.XPATH, ".//a").get_attribute("href"))
            else:
                kat_dict.append(i.find_element(By.XPATH, ".//div").text)
        res = convert(kat_dict)

        while res[self.document] is None:
            time.sleep(10)

        return pd.read_csv(res[self.document], skiprows=1, header=0)

    def run_store_driver(self, browser, report_date):
        self.open_store_driver(browser)
        # your job here
        self.prepare_env(browser)
        print(self.site_name, self.site_url, report_date)
        for dataset in ['sales', 'inventory']:
            self.set_dateset(dataset, report_date)
            print(self.url, self.document)
            self.run_task()
            data_set = self.run_download()
            print(data_set)

        self.close_store_driver(browser)

    def run_all_store_driver(self, browser_list, report_date):
        for browser in browser_list:
            self.run_store_driver(browser, report_date)
