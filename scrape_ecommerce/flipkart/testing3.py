import re
import time
import json
import csv
import os
import requests

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Global scraping configurations
retries = 2
search_page = 10
search_keyword = "Rolex Watches"

# File and folder setup
json_file = "flipkart.json"
csv_file = "flipkart.csv"
images_folder = "images"

# Ensure images folder exists
os.makedirs(images_folder, exist_ok=True)

# Initialize JSON file if not present
if not os.path.exists(json_file):
    with open(json_file, 'w', encoding='utf-8') as jf:
        json.dump([], jf, ensure_ascii=False, indent=4)

# Initialize CSV file and header if not present
csv_fields = [
    'Product Number', 'Product Name', 'Price', 'Link', 'Details', 'Rating',
    'Review', 'Seller Info', 'Color Info', 'Manufacturer Info', 'In the box',
    'bestseller_info', 'modelno info', 'discount info', 'MRP info',
    'Price after discount', 'Delivery details', 'Display Size', 'images'
]
if not os.path.exists(csv_file):
    with open(csv_file, 'w', newline='', encoding='utf-8') as cf:
        writer = csv.DictWriter(cf, fieldnames=csv_fields)
        writer.writeheader()

# Setup Selenium configurations
def selenium_config():
    options = webdriver.ChromeOptions()
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--log-level=3")
    # options.add_argument("--headless")
    browser = webdriver.Chrome(options=options)
    browser.maximize_window()
    return browser

# Retry helper
def retry_extraction(func, attempts=1, delay=1, default=""):
    for i in range(attempts):
        try:
            result = func()
            if result is not None:
                return result
        except Exception:
            time.sleep(delay)
    return default

# Main scraping function
def scrape_flipkart_products(browser):
    scraped_products = {}
    count = 0
    for page in range(1, search_page + 1):
        for attempt in range(retries):
            try:
                url = (
                    f'https://www.flipkart.com/search?q={search_keyword}'
                    f'&otracker=search&otracker1=search&marketplace=FLIPKART'
                    f'&as-show=on&as=off&page={page}'
                )
                browser.get(url)
                WebDriverWait(browser, 10).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
                time.sleep(2)

                selectors = ["div._1sdMkc.LFEi7Z", "div.tUxRFH"]
                product_cards = None
                for sel in selectors:
                    try:
                        elems = WebDriverWait(browser, 10).until(
                            EC.presence_of_all_elements_located((By.CSS_SELECTOR, sel))
                        )
                        if elems:
                            product_cards = elems
                            break
                    except:
                        continue

                if not product_cards:
                    print(f"No products on page {page}")
                    break

                for card in product_cards:
                    data = {
                        "url": "", "title": "", "currency": "", "price": "", "description": "",
                        "images": [], 'Product Number': None, 'Product Name': '', 'Details': '',
                        'Rating': '', 'Review': '', 'Seller Info': '', 'Color Info': '',
                        'Manufacturer Info': [], 'In the box': '', 'bestseller_info': '',
                        'modelno info': '', 'discount info': '', 'MRP info': '',
                        'Price after discount': '', 'Delivery details': '', 'Display Size': ''
                    }

                    # assign incremental number
                    count += 1
                    data['Product Number'] = count

                    # extract URL
                    try:
                        a = card.find_element(By.TAG_NAME, 'a')
                        link = a.get_attribute('href')
                        data['url'] = link
                        data['Link'] = link
                    except:
                        continue

                    # open product page
                    browser.execute_script("window.open('');")
                    browser.switch_to.window(browser.window_handles[-1])
                    browser.get(link)
                    WebDriverWait(browser, 10).until(
                        lambda d: d.execute_script("return document.readyState") == "complete"
                    )
                    time.sleep(1)

                    # title
                    try:
                        title = browser.find_element(By.CSS_SELECTOR, 'span.VU-ZEz').text.strip()
                        data['title'] = title
                        data['Product Name'] = title
                    except:
                        pass

                    # price & currency
                    try:
                        pc = browser.find_element(By.CSS_SELECTOR, 'div.Nx9bqj.CxhGGd').text.strip()
                        m = re.match(r'([^0-9]+)([0-9,]+)', pc)
                        if m:
                            data['currency'] = m.group(1)
                            data['price'] = m.group(2)
                            data['Price after discount'] = pc
                    except:
                        pass

                    # description
                    try:
                        desc_elems = browser.find_elements(By.CSS_SELECTOR, 'div.pqHCzB')
                        desc = ' '.join(e.text.strip() for e in desc_elems if e.text.strip())
                        data['description'] = desc
                        data['Details'] = desc
                    except:
                        pass

                    # images
                    try:
                        main = browser.find_element(By.CSS_SELECTOR, 'div.qOPjUY')
                        thumbs = main.find_elements(By.CSS_SELECTOR, 'li.YGoYIP')
                        for idx, tb in enumerate(thumbs):
                            try:
                                browser.execute_script("arguments[0].scrollIntoView(true);", tb)
                                tb.click()
                                time.sleep(1)
                                wrap = main.find_element(By.CSS_SELECTOR, 'div.vU5WPQ')
                                img = wrap.find_element(By.TAG_NAME, 'img').get_attribute('src')
                                data['images'].append(img)
                            except:
                                continue
                    except:
                        pass

                    # close tab
                    browser.close()
                    browser.switch_to.window(browser.window_handles[0])

                    # save to JSON
                    with open(json_file, 'r+', encoding='utf-8') as jf:
                        try:
                            arr = json.load(jf)
                        except:
                            arr = []
                        arr.append(data)
                        jf.seek(0)
                        json.dump(arr, jf, ensure_ascii=False, indent=4)
                        jf.truncate()

                    # save to CSV
                    with open(csv_file, 'a', newline='', encoding='utf-8') as cf:
                        writer = csv.DictWriter(cf, fieldnames=csv_fields)
                        row = {k: data.get(k, '') for k in csv_fields}
                        row['Manufacturer Info'] = ';'.join(data['Manufacturer Info'])
                        row['images'] = ';'.join(data['images'])
                        writer.writerow(row)

                    # download images
                    for idx, url_img in enumerate(data['images']):
                        try:
                            content = requests.get(url_img, timeout=10).content
                            ext = os.path.splitext(url_img.split('?')[0])[1] or '.jpg'
                            name = re.sub(r'[^A-Za-z0-9]+', '_', data['title'])[:50]
                            fname = f"{name}_{idx}{ext}"
                            with open(os.path.join(images_folder, fname), 'wb') as f:
                                f.write(content)
                        except:
                            pass

                break
            except Exception as e:
                print(f"Page {page} attempt {attempt+1} failed: {e}")
                time.sleep(1)
        else:
            print(f"Failed page {page} after retries.")
    print("Scraping completed.")

if __name__ == '__main__':
    browser = selenium_config()
    retry_extraction(lambda: scrape_flipkart_products(browser), attempts=1)
    browser.quit()
