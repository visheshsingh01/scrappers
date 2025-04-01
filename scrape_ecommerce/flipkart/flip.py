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
search_page = 1 
search_keyword = "iphone"

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
    for i in range(attempts):
        try:
            result = func()
            if result:
                return result
        except Exception:
            time.sleep(delay)
    return default

def scrape_flipkart_products(browser):
    scraped_products = {}
    for page in range(1, search_page+1):
        for attempt in range(retries):
            try:
                search_url = f'https://www.flipkart.com/search?q={search_keyword}&otracker=search&otracker1=search&marketplace=FLIPKART&as-show=on&as=off&page={page}'
                browser.get(search_url)
                WebDriverWait(browser, 10).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
                time.sleep(2)
                product_cards_selectors = ["div._1sdMkc.LFEi7Z", "div.tUxRFH"]
                product_cards = None
                for product_cards_selector in product_cards_selectors:
                    try:
                        product_card_elements = WebDriverWait(browser, 10).until(
                            EC.presence_of_all_elements_located((By.CSS_SELECTOR, product_cards_selector))
                        )
                        if product_card_elements:
                            product_cards = product_card_elements
                            break
                    except Exception as e:
                        continue
                if product_cards is None:
                    print("No product found")
                    return
                else:
                    print("product found")
                    for product_card in product_cards:
                        product_json_data = {
                            "url": "",
                            "title": "",
                            "currency": "",
                            "price": "",
                            "description": "",
                            "images": []
                        }
                        # Extracting product url
                        product_url_tag = product_card.find_element(By.TAG_NAME, "a")
                        product_url = product_url_tag.get_attribute("href")
                        product_json_data["url"] = product_url

                        # Open product in new tab
                        if product_json_data["url"]:
                            try:
                                browser.execute_script("window.open('');")
                                browser.switch_to.window(browser.window_handles[-1])
                                browser.get(product_json_data["url"])
                                WebDriverWait(browser, 10).until(
                                    lambda d: d.execute_script("return document.readyState") == "complete"
                                )
                                time.sleep(1)
                                
                                # Extracting product title
                                product_title_elem = browser.find_element(
                                    By.CSS_SELECTOR, "span.VU-ZEz"
                                )
                                product_title = product_title_elem.text.strip()
                                if product_title:
                                    product_json_data["title"] = product_title
                                    print(product_json_data["title"])

                                # Extracting product price and currency
                                product_price_currency_elem = browser.find_element(
                                    By.CSS_SELECTOR, "div.Nx9bqj.CxhGGd"
                                )
                                product_price_currency = product_price_currency_elem.text.strip()
                                product_price_currency_match = re.match(r'([^0-9]+)([0-9,]+)', product_price_currency)
                                if product_price_currency_match:
                                    product_currency = product_price_currency_match.group(1)
                                    if product_currency:
                                        product_json_data["currency"] = product_currency
                                    product_price = product_price_currency_match.group(2)
                                    if product_price:
                                        product_json_data["price"] = product_price
                                
                                # Extracting product images
                                product_images_main_elem = browser.find_element(By.CSS_SELECTOR, "div.qOPjUY")
                                if product_images_main_elem:
                                    imgButtons = product_images_main_elem.find_elements(By.CSS_SELECTOR, "li.YGoYIP")
                                    print(len(imgButtons))
                                    for imgButton in imgButtons:
                                        try:
                                            time.sleep(1)
                                            browser.execute_script("arguments[0].scrollIntoView(true);", imgButton)
                                            imgButton.click()
                                            time.sleep(1)
                                            try:
                                                product_image_wrapper = product_images_main_elem.find_element(By.CSS_SELECTOR, "div.vU5WPQ")
                                            except Exception as wrapper_err:
                                                continue

                                            try:
                                                product_image_elem = product_image_wrapper.find_element(By.TAG_NAME, "img")
                                                product_image = product_image_elem.get_attribute("src")
                                                product_json_data["images"].append(product_image)
                                            except Exception as img_err:
                                                continue
                                        except Exception as e:
                                            continue
                                else:
                                    print("No product images main element found.")

                                # Extracting product description
                                product_description_main_elem = browser.find_elements(
                                    By.CSS_SELECTOR, "div.pqHCzB"
                                )
                                product_description = "".join(
                                    elem.text.strip() for elem in product_description_main_elem if elem.text.strip()
                                )
                                product_json_data["description"] = product_description
                                print(product_json_data["description"])

                            except Exception as e:
                                print("Error processing product page:", e)
                            finally:
                                browser.close()
                                browser.switch_to.window(browser.window_handles[0])
                        # Save unique product
                        scraped_products[product_json_data["url"]] = product_json_data
                    break
            except Exception as e:
                print(f"Attempt {attempt+1}/{retries}: Error scraping products from page {page}: {e}")
                time.sleep(1)
        else:
            print(f"Failed to scrape products from page {page} after {retries} attempts.")
    
    # Save all unique scraped products to a JSON file
    with open("flipkart.json", "w", encoding="utf-8") as f:
        json.dump(list(scraped_products.values()), f, ensure_ascii=False, indent=4)
    print("Scraping completed and saved to flipkart.json")

browser = selenium_config()
retry_extraction(
    scrape_flipkart_products(browser)
)
browser.quit()