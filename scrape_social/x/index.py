import re
import time
import json

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Global scraping configurations
retries = 2
search_tweets = 30  # number of tweets need to scrape
search_keyword = "kartik aryan"
x_username = "diwakar.jha@brancosoft.com"
x_password = "Diwakar@1234;"
x_verification = "BrancoSoft_DJ"

# Setup Selenium configurations
def selenium_config():
    options = webdriver.ChromeOptions()
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--log-level=3")
    # options.add_argument("--headless")
    browser = webdriver.Chrome(options=options)
    browser.maximize_window()
    return browser

def retry_extraction(func, attempts=1, delay=1, default=""):
    """
    Helper function that retries an extraction function up to 'attempts' times.
    Returns the result if successful, otherwise returns 'default'.
    """
    for i in range(attempts):
        try:
            result = func()
            if result:
                return result
        except Exception:
            time.sleep(delay)
    return default

def x_login(browser):
    try:
        browser.get('https://x.com/i/flow/login')
        WebDriverWait(browser,20).until(
            lambda d: d.execute_script('return document.readyState')== 'complete'
        )
        # X username
        WebDriverWait(browser, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR , 'input[name="text"]'))
        )
        usernameField = WebDriverWait(browser, 20).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR , 'input[name="text"]'))
        )
        usernameField.clear()
        usernameField.send_keys(x_username)
        username_next_button = WebDriverWait(browser, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//button[@role="button" and contains(., "Next")]'))
        )
        username_next_button.click()
        time.sleep(1)
        try:
            # X verfication
            verificationField = WebDriverWait(browser, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR , 'input[name="text"]'))
            )
            verificationField.clear()
            verificationField.send_keys(x_verification)
            verification_next_button = WebDriverWait(browser, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//button[@data-testid="ocfEnterTextNextButton"]'))
            )
            verification_next_button.click()
            time.sleep(3)
        except:
            pass
        # X password
        passwordField = WebDriverWait(browser,10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR , 'input[name="password"]'))
        )
        passwordField.clear()
        passwordField.send_keys(x_password)
        loginform_login_button = WebDriverWait(browser, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//button[@data-testid="LoginForm_Login_Button"]'))
        )
        loginform_login_button.click()
        time.sleep(2)
        return True
    except Exception as e:
        print("Login failed", e)
        return False

def x_tweets():
    pass

def x_public_tweets(browser):
    total_tweets = 0
    try:
        browser.get(f'https://x.com/search?q={search_keyword}&src=typed_query&f=top')
        WebDriverWait(browser,20).until(
            lambda d: d.execute_script('return document.readyState')== 'complete'
        )
        total_tweets_articles = browser.find_elements(By.XPATH, '//article[@]')
    except Exception as e:
        pass

def scrape_x_data():
    scrapped_data = {}
    # selenium browser activate
    browser = selenium_config()
    # login to X
    retry_extraction(
        x_login(browser), attempts=3, delay=2
    )
    # 


scrape_x_data()