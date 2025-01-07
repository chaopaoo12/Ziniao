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
from selenium.webdriver.support.select import Select
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

def is_Applying(driver):
    try:
        driver.find_element(By.XPATH, "//kat-button[contains(@label,'Apply')]")
        return True
    except:
        return False

def is_loging(driver):
    try:
        driver.find_element(By.XPATH, "//*[@id='dropdown-account-switcher-container']")
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
        self.document_start = f'{dataset.title()}_Manufacturing_Retail'
        self.document_end = f'Custom_{report_date}_{report_date}'

    def prepare_shop(self):

        self.driver.find_element(By.XPATH, '//div[contains(@class, "dropdown-account-switcher")]').click()
        elements = self.driver.find_elements(By.XPATH, '//div[contains(@class, "dropdown-account-switcher-list-item")]')
        shop_names = []
        for i in elements:
            shop_names.append(i.get_attribute('title'))
        shop_names = [i for i in shop_names if len(i) > 0]

        self.select_shops = [i for i in shop_names if i in self.shop_list]

    def choose_shop(self, shop_name):
        self.driver.find_element(By.XPATH, f"//*[contains(text(),'{shop_name}')]").click()
        if self.driver.find_element(By.XPATH, '//div[contains(@class, "dropdown-account-switcher")]').text == shop_name:
            print(f"=====选择店铺：{shop_name}=====")
        else:
            print(f"=====店铺选择失败：{shop_name}=====")

    def deal_login(self):
        while is_loging(self.driver) is False:
            if self.driver.find_element(By.XPATH, "//input[contains(@id,'continue')]") is not None:
                self.driver.find_element(By.XPATH, "//input[contains(@id,'continue')]").click()
                time.sleep(3)
                self.driver.find_element(By.XPATH, "//input[contains(@id,'signInSubmit')]").click()
                time.sleep(3)
                self.driver.find_element(By.XPATH, "//input[contains(@id,'auth-signin-button')]").click()
                time.sleep(3)
        print("prepare shop list")
        self.prepare_shop()

    def run_task(self):
        self.driver.get(self.url)
        while is_Applying(self.driver) is False:
            self.driver.get(self.url)

        while self.driver.find_element(By.XPATH, "//kat-button[contains(@label,'Apply')]").get_attribute("disabled") == "true":
            time.sleep(10)

        print("Applying data filter")
        self.driver.find_element(By.XPATH, "//kat-button[contains(@label,'Apply')]").click()

        while self.driver.find_element(By.XPATH, "//kat-button[contains(@label,'CSV')]").get_attribute("disabled") == "true":
            time.sleep(10)

        print("Applying CSV Download")
        self.driver.find_element(By.XPATH, "//kat-button[contains(@label,'CSV')]").click()

    def run_download(self):
        print("Opening Download")
        self.driver.find_element(By.XPATH, "//*[contains(text(),'View and manage your downloads.')]").click()

        while is_Porcessing(self.driver):
            print("data processing, please wait...")
            time.sleep(10)

        kat_table = self.driver.find_element(By.XPATH, "//kat-table[contains(@role,'table')]")

        kat_dict = []
        documents = []

        for i in kat_table.find_elements(By.XPATH, "//kat-table-cell[contains(@role,'cell')]"):
            if i.text in ["Download", "Processing"]:
                kat_dict.append(i.find_element(By.XPATH, ".//a").get_attribute("href"))
            else:
                kat_dict.append(i.find_element(By.XPATH, ".//div").text)
        res = convert(kat_dict)

        documents = [i for i in res.keys() if i.startswith(self.document_start) and i.endswith(self.document_end)]

        return pd.read_csv(res[documents[0]], skiprows=1, header=0)

    def get_store_data(self, browser, report_date, dataset):
        self.open_store_driver(browser)
        # your job here
        self.prepare_env(browser)
        print(self.site_name, self.site_url, report_date)
        self.set_dateset(dataset, report_date)
        print(self.url, self.document_start, self.document_end)
        print("deal login")
        self.deal_login()
        data_sets = []
        for shop in self.select_shops:
            self.choose_shop(shop)

            self.run_task()
            data_set = self.run_download()
            data_set = data_set.assign(site_name=browser['platform_name'], type=dataset, report_date=report_date, Store_code=shop)
            if dataset == 'inventory':
                data_set.columns = ['ASIN','Product_title','Brand','Sourceable_Product_OOS','Vendor_Confirmation_Rate','Net_Received',
                                    'Net_Received_Units','Open_Purchase_Order_Quantity','Receive_Fill_Rate','Overall_Vendor_Lead_days',
                                    'Unfilled_Customer_Ordered_Units','Aged_90_Days_Sellable_Inventory','Aged_90_Days_Sellable_Units',
                                    'Sellable_On_Hand_Inventory','Sellable_On_Hand_Units','Unsellable_On_Hand_Inventory','Unsellable_On_Hand_Units',
                                    'site_name','type','report_date','Store_code']
            data_set.columns = [i.replace(' ', '_').lower() for i in data_set.columns]
            data_sets.append(data_set)
        return pd.concat(data_sets)

    def run_store_driver(self, browser, report_date):
        for dataset in ['sales', 'inventory']:
            df = self.get_store_data(browser, report_date, dataset)

        self.close_store_driver(browser)

    def run_all_store_driver(self, browser_list, report_date):
        for browser in browser_list:
            self.run_store_driver(browser, report_date)
