# -*- encoding: utf-8 -*-
'''
@File    :   ziniao_new.py
@Time    :   2025/01/02 10:35:50
@Author  :   chaopaoo12 
@Version :   1.0
@Contact :   chaopaoo12@hotmail.com
'''

# here put the import lib

import hashlib
import os
import shutil
import time
import traceback
import uuid
import json
import platform

import requests
import subprocess
from selenium import webdriver
from selenium.common import NoSuchElementException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By


def delete_all_cache():
    """
    删除所有店铺缓存
    非必要的，如果店铺特别多、硬盘空间不够了才要删除
    """
    is_windows = platform.system() == 'Windows'
    is_mac = platform.system() == 'Darwin'
    if not is_windows:
        return
    local_appdata = os.getenv('LOCALAPPDATA')
    cache_path = os.path.join(local_appdata, 'SuperBrowser')
    if os.path.exists(cache_path):
        shutil.rmtree(cache_path)


def delete_all_cache_with_path(path):
    """
    :param path: 启动客户端参数使用--enforce-cache-path时设置的缓存路径
    删除所有店铺缓存
    非必要的，如果店铺特别多、硬盘空间不够了才要删除
    """
    is_windows = platform.system() == 'Windows'
    is_mac = platform.system() == 'Darwin'

    if not is_windows:
        return
    cache_path = os.path.join(path, 'SuperBrowser')
    if os.path.exists(cache_path):
        shutil.rmtree(cache_path)

def download_file(url, save_path):
    # 发送GET请求获取文件内容
    response = requests.get(url, stream=True)
    # 检查请求是否成功
    if response.status_code == 200:
        # 创建一个本地文件并写入下载的内容（如果文件已存在，将被覆盖）
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
        print(f"文件已成功下载并保存到：{save_path}")
    else:
        print(f"下载失败，响应状态码为：{response.status_code}")

def download_driver(driver_folder_path):
    is_windows = platform.system() == 'Windows'
    is_mac = platform.system() == 'Darwin'

    if is_windows:
        config_url = "https://cdn-superbrowser-attachment.ziniao.com/webdriver/exe_32/config.json"
    elif is_mac:
        arch = platform.machine()
        if arch == 'x86_64':
            config_url = "https://cdn-superbrowser-attachment.ziniao.com/webdriver/mac/x64/config.json"
        elif arch == 'arm64':
            config_url = "https://cdn-superbrowser-attachment.ziniao.com/webdriver/mac/arm64/config.json"
        else:
            return
    else:
        return
    response = requests.get(config_url)
    # 检查请求是否成功
    if response.status_code == 200:
        # 获取文本内容
        txt_content = response.text
        config = json.loads(txt_content)
    else:
        print(f"下载驱动失败，状态码：{response.status_code}")
        exit()
    if not os.path.exists(driver_folder_path):
        os.makedirs(driver_folder_path)

    # 获取文件夹中所有chromedriver文件
    driver_list = [filename for filename in os.listdir(driver_folder_path) if filename.startswith('chromedriver')]

    for item in config:
        filename = item['name']
        if is_windows:
            filename = filename + ".exe"
        local_file_path = os.path.join(driver_folder_path, filename)
        if filename in driver_list:
            # 判断sha1是否一致
            file_sha1 = encrypt_sha1(local_file_path)
            if file_sha1 == item['sha1']:
                print(f"驱动{filename}已存在，sha1校验通过...")
            else:
                print(f"驱动{filename}的sha1不一致，重新下载...")
                download_file(item['url'], local_file_path)
                # mac首次下载修改文件权限
                if is_mac:
                    cmd = ['chmod', '+x', local_file_path]
                    subprocess.Popen(cmd)
        else:
            print(f"驱动{filename}不存在，开始下载...")
            download_file(item['url'], local_file_path)
            # mac首次下载修改文件权限
            if is_mac:
                cmd = ['chmod', '+x', local_file_path]
                subprocess.Popen(cmd)

def encrypt_sha1(fpath: str) -> str:
    with open(fpath, 'rb') as f:
        return hashlib.new('sha1', f.read()).hexdigest()

def check_env(driver_folder_path, client_path, socket_port):
    """
    检查运行环境
    :return:
    """
    is_windows = platform.system() == 'Windows'
    is_mac = platform.system() == 'Darwin'

    if not is_windows and not is_mac:
        print("webdriver/cdp只支持windows和mac操作系统")
        exit()

    if is_windows:
        driver_folder_path = driver_folder_path  # todo 放置chromedriver的文件夹路径
        client_path = client_path  # 客户端程序starter.exe的路径
    else:
        driver_folder_path = driver_folder_path  # todo 放置chromedriver的文件夹路径
        client_path = client_path  # 客户端程序名称
    socket_port = socket_port  # 系统未被占用的端口

    return driver_folder_path, client_path, socket_port


class ZiniaoBrowser():

    def __init__(self, driver_folder_path, client_path, socket_port, user_info):
        self.driver_folder_path, self.client_path, self.socket_port, self.user_info = driver_folder_path, client_path, socket_port, user_info
        """
        windows用
        有店铺运行的时候，会删除失败
        删除所有店铺缓存，非必要的，如果店铺特别多、硬盘空间不够了才要删除
        delete_all_cache()

        启动客户端参数使用--enforce-cache-path时用这个方法删除，传入设置的缓存路径删除缓存
        delete_all_cache_with_path(path)
        """

        '''下载各个版本的webdriver驱动'''
        download_driver(self.driver_folder_path)

        # 终止紫鸟客户端已启动的进程
        self.kill_process()
        self.start_browser()
        self.update_core(self.user_info)

    def start_browser(self):
        is_windows = platform.system() == 'Windows'
        is_mac = platform.system() == 'Darwin'
        """
        启动客户端
        :return:
        """
        try:
            if is_windows:
                cmd = [
                    self.client_path,
                    '--run_type=web_driver',
                    '--ipc_type=http',
                    '--port=' + str(self.socket_port)
                    ]
            elif is_mac:
                cmd = ['open', '-a', self.client_path, '--args', '--run_type=web_driver', '--ipc_type=http',
                    '--port=' + str(self.socket_port)]
            else:
                exit()
            subprocess.Popen(cmd)
            time.sleep(5)
        except Exception:
            print('start browser process failed: ' + traceback.format_exc())
            exit()
    
    def update_core(self, user_info):
        """
        下载所有内核，打开店铺前调用，需客户端版本5.285.7以上
        因为http有超时时间，所以这个action适合循环调用，直到返回成功
        """
        data = {
            "action": "updataCore",
            "requestId": str(uuid.uuid4()),
        }
        data.update(user_info)
        while True:
            result = self.send_http(data)
            print(result)
            if result is None:
                print("等待客户端启动...")
                time.sleep(2)
                continue
            if result.get("statusCode") is None or result.get("statusCode") == -10003:
                print("当前版本不支持此接口，请升级客户端")
                return
            elif result.get("statusCode") == 0:
                print("更新内核完成")
                return
            else:
                print(f"等待更新内核: {json.dumps(result)}")
                time.sleep(2)    
    
    def send_http(self, data):
        """
        通讯方式
        :param data:
        :return:
        """
        try:
            url = 'http://127.0.0.1:{}'.format(self.socket_port)
            response = requests.post(url, json.dumps(data).encode('utf-8'), timeout=120)
            return json.loads(response.text)
        except Exception as err:
            print(err)

    def get_driver(self, open_ret_json):
        is_windows = platform.system() == 'Windows'
        is_mac = platform.system() == 'Darwin'
        core_type = open_ret_json.get('core_type')
        if core_type == 'Chromium' or core_type == 0:
            major = open_ret_json.get('core_version').split('.')[0]
            if is_windows:
                chrome_driver_path = os.path.join(self.driver_folder_path, 'chromedriver%s.exe') % major
            else:
                chrome_driver_path = os.path.join(self.driver_folder_path, 'chromedriver%s') % major
            print(f"chrome_driver_path: {chrome_driver_path}")
            port = open_ret_json.get('debuggingPort')
            options = webdriver.ChromeOptions()
            options.add_argument('--log-level=3')
            options.add_experimental_option("debuggerAddress", '127.0.0.1:' + str(port))
            return webdriver.Chrome(service=Service(chrome_driver_path), options=options)
        else:
            return None
        
    def open_ip_check(self, driver, ip_check_url):
        """
        打开ip检测页检测ip是否正常
        :param driver: driver实例
        :param ip_check_url ip检测页地址
        :return 检测结果
        """
        try:
            driver.get(ip_check_url)
            driver.find_element(By.XPATH, '//button[contains(@class, "styles_btn--success")]')
            return True
        except NoSuchElementException:
            print("未找到ip检测成功元素")
            return False
        except Exception as e:
            print("ip检测异常:" + traceback.format_exc())
            return False

    def open_launcher_page(self, driver, launcher_page):
        driver.get(launcher_page)
        time.sleep(6)

    def get_exit(self):
        """
        关闭客户端
        :return:
        """
        data = {"action": "exit", "requestId": str(uuid.uuid4())}
        data.update(self.user_info)
        print('@@ get_exit...' + json.dumps(data, ensure_ascii=False))
        self.send_http(data)

    def kill_process(self):
        """
        终止紫鸟客户端已启动的进程
        """
        is_windows = platform.system() == 'Windows'
        is_mac = platform.system() == 'Darwin'
        # 确认是否继续
        #confirmation = input("在启动之前，需要先关闭紫鸟浏览器的主进程，确定要终止进程吗？(y/n): ")
        confirmation = "y"
        if confirmation.lower() == 'y':
            if is_windows:
                os.system('taskkill /f /t /im SuperBrowser.exe')
            elif is_mac:
                os.system('killall ziniao')
                time.sleep(3)
        else:
            exit()


class ZiniaoShop():
    def __init__(self, company, username, password, driver_folder_path, client_path, socket_port):
        self.user_info = {
            "company": company,
            "username": username,
            "password": password
            }
        self.driver_folder_path, self.client_path, self.socket_port = check_env(driver_folder_path, client_path, socket_port)
        self.browser = ZiniaoBrowser(self.driver_folder_path, self.client_path, self.socket_port, self.user_info)

    def get_store(self):
        is_windows = platform.system() == 'Windows'
        is_mac = platform.system() == 'Darwin'

        if not is_windows and not is_mac:
            print("webdriver/cdp只支持windows和mac操作系统")
            exit()

        """
        windows用
        有店铺运行的时候，会删除失败
        删除所有店铺缓存，非必要的，如果店铺特别多、硬盘空间不够了才要删除
        delete_all_cache()

        启动客户端参数使用--enforce-cache-path时用这个方法删除，传入设置的缓存路径删除缓存
        delete_all_cache_with_path(path)
        """

        """获取店铺列表"""
        print("=====获取店铺列表=====")
        browser_list = self.get_browser_list()
        if browser_list is None:
            print("browser list is empty")
            exit()
        return browser_list

    def get_browser_list(self) -> list:
        request_id = str(uuid.uuid4())
        data = {
            "action": "getBrowserList",
            "requestId": request_id
        }
        data.update(self.user_info)

        r = self.browser.send_http(data)
        if str(r.get("statusCode")) == "0":
            print(r)
            return r.get("browserList")
        elif str(r.get("statusCode")) == "-10003":
            print(f"login Err {json.dumps(r, ensure_ascii=False)}")
            exit()
        else:
            print(f"Fail {json.dumps(r, ensure_ascii=False)} ")
            exit()

    def open_store(self, store_info, isWebDriverReadOnlyMode=0, isprivacy=0, isHeadless=0, cookieTypeSave=0, jsInfo=""):
        request_id = str(uuid.uuid4())
        data = {
            "action": "startBrowser"
            , "isWaitPluginUpdate": 0
            , "isHeadless": isHeadless
            , "requestId": request_id
            , "isWebDriverReadOnlyMode": isWebDriverReadOnlyMode
            , "cookieTypeLoad": 0
            , "cookieTypeSave": cookieTypeSave
            , "runMode": "1"
            , "isLoadUserPlugin": False
            , "pluginIdType": 1
            , "privacyMode": isprivacy
        }
        data.update(self.user_info)

        if store_info.isdigit():
            data["browserId"] = store_info
        else:
            data["browserOauth"] = store_info

        if len(str(jsInfo)) > 2:
            data["injectJsInfo"] = json.dumps(jsInfo)

        r = self.browser.send_http(data)
        if str(r.get("statusCode")) == "0":
            return r
        elif str(r.get("statusCode")) == "-10003":
            print(f"login Err {json.dumps(r, ensure_ascii=False)}")
            exit()
        else:
            print(f"Fail {json.dumps(r, ensure_ascii=False)} ")
            exit()


    def close_store(self, browser_oauth):
        request_id = str(uuid.uuid4())
        data = {
            "action": "stopBrowser"
            , "requestId": request_id
            , "duplicate": 0
            , "browserOauth": browser_oauth
        }
        data.update(self.user_info)

        r = self.browser.send_http(data)
        if str(r.get("statusCode")) == "0":
            return r
        elif str(r.get("statusCode")) == "-10003":
            print(f"login Err {json.dumps(r, ensure_ascii=False)}")
            exit()
        else:
            print(f"Fail {json.dumps(r, ensure_ascii=False)} ")
            exit()
    
    def open_store_driver(self, browser):
        # 如果要指定店铺ID, 获取方法:登录紫鸟客户端->账号管理->选择对应的店铺账号->点击"查看账号"进入账号详情页->账号名称后面的ID即为店铺ID
        store_id = browser.get('browserOauth')
        store_name = browser.get("browserName")
        # 打开店铺
        print(f"=====打开店铺：{store_name}=====")
        ret_json = self.open_store(store_id)
        print(ret_json)
        store_id = ret_json.get("browserOauth")
        if store_id is None:
            store_id = ret_json.get("browserId")
        # 使用驱动实例开启会话
        self.driver = self.browser.get_driver(ret_json)
        if self.driver is None:
            print(f"=====关闭店铺：{store_name}=====")
            self.close_store(store_id)
            return

        # 获取ip检测页地址
        ip_check_url = ret_json.get("ipDetectionPage")
        if not ip_check_url:
            print("ip检测页地址为空，请升级紫鸟浏览器到最新版")
            self.driver.quit()
            print(f"=====关闭店铺：{store_name}=====")
            self.close_store(store_id)
            exit()
        # 执行脚本
        self.driver.implicitly_wait(60)
        if self.browser.open_ip_check(self.driver, ip_check_url):
            print("ip检测通过，打开店铺平台主页")
            self.browser.open_launcher_page(self.driver, ret_json.get("launcherPage"))
            # 打开店铺平台主页后进行后续自动化操作
        else:
            print("ip检测不通过，请检查")

    def close_store_driver(self, browser):
        store_id = browser.get('browserOauth')
        store_name = browser.get("browserName")
        self.driver.quit()
        print(f"=====关闭店铺：{store_name}=====")
        self.close_store(store_id)


    def run_store_driver(self, browser):
        self.open_store_driver(browser)
        # your job here
        self.close_store_driver(browser)

    def run_all_store_driver(self, browser_list):
        for browser in browser_list:
            self.run_store_driver(browser)

    def get_exit(self):
        self.browser.get_exit()



if __name__ == "__main__":
    """ 需要从系统右下角角标将紫鸟浏览器退出后再运行"""
    company = "tenghangda"
    username = "zhangchao"
    password = "Zhangchao123"
    driver_folder_path = r'C:\ProgramData\anaconda3'
    client_path = r'D:\Program Files\SuperBrowser\starter.exe'
    socket_port = 16851

    shop = ZiniaoShop(company, username, password, driver_folder_path, client_path, socket_port)

    print("=====获取店铺列表=====")
    browser_list = shop.get_store()
    if browser_list is None:
        print("browser list is empty")
        exit()

    """打开第一个店铺运行脚本"""
    shop.run_store_driver(browser_list[0])

    """循环打开所有店铺运行脚本"""
    # shop.run_all_store_driver(browser_list)

    """关闭客户端"""
    shop.get_exit()
