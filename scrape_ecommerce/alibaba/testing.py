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
search_page = 1  # Adjust to desired number of pages
search_keyword = "Nike air Jordan max shoes"

# Setup Selenium configurations with headless mode for speed
options = webdriver.ChromeOptions()
# options.add_argument("--headless")
options.add_argument("--disable-gpu")
options.add_argument("--ignore-certificate-errors")
options.add_argument("--log-level=3")
browser = webdriver.Chrome(options=options)
browser.set_window_size(1920, 1080)

def retry_extraction(func, attempts=2, delay=0.5, default=""):
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

def scrape_alibaba_products():
    scraped_products = {}  # Using URL as key to avoid duplicates
    for page in range(1, search_page + 1):
        for attempt in range(retries):
            try:
                search_url = (f'https://www.alibaba.com/trade/search?fsb=y&IndexArea=product_en'
                              f'&keywords={search_keyword}&originKeywords={search_keyword}&tab=all'
                              f'&&page={page}&spm=a2700.galleryofferlist.pagination.0')
                browser.get(search_url)
                WebDriverWait(browser, 10).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
                time.sleep(1)  # Reduced sleep time
                product_cards = browser.find_elements(By.CLASS_NAME, 'fy23-search-card')
                print(f"Found {len(product_cards)} product cards on page {page}")
                for product_elem in product_cards:
                    product_json_data = {
                        "url": "",
                        "title": "",
                        "currency": "",
                        "price": "",
                        "min_order": "",
                        "supplier": "",
                        "origin": "",
                        "feedback": {"rating": "", "review": ""},
                        "images": [],
                        "videos": []
                    }
                    product = BeautifulSoup(product_elem.get_attribute('outerHTML'), 'html.parser')

                    # Extracting product url
                    try:
                        product_link = retry_extraction(
                            lambda: product.select_one('.search-card-e-slider__link').get('href')
                        )
                        if product_link:
                            if product_link.startswith('//'):
                                product_url = 'https:' + product_link
                            else:
                                product_url = product_link
                            product_json_data["url"] = product_url
                    except Exception as e:
                        print("Error extracting product url:", e)

                    # Extracting product title
                    try:
                        title_elem = retry_extraction(
                            lambda: product.select_one('.search-card-e-title span')
                        )
                        if title_elem:
                            product_title = title_elem.get_text(strip=True)
                            product_json_data["title"] = product_title
                    except Exception as e:
                        print("Error extracting product title:", e)

                    # Avoid duplicate products by URL
                    if product_json_data["url"] in scraped_products:
                        continue

                    # Extracting product currency and price
                    try:
                        currency_price_elem = retry_extraction(
                            lambda: product.select_one('.search-card-e-price-main')
                        )
                        if currency_price_elem:
                            text = currency_price_elem.get_text(strip=True)
                            if text:
                                # Remove digits, dots, hyphens, and spaces to get currency symbol(s)
                                currency = ''.join([c for c in text if not c.isdigit() and c not in ['.', '-', ' ']]).strip()
                                if currency:
                                    fixed_currency = currency[0]
                                    product_json_data["currency"] = fixed_currency
                                    product_json_data["price"] = text.replace(fixed_currency, '').strip()
                    except Exception as e:
                        print("Error extracting product currency and price:", e)
                    
                    # Extracting product min order
                    try:
                        min_order_elem = retry_extraction(
                            lambda: product.select_one('.search-card-m-sale-features__item')
                        )
                        if min_order_elem:
                            min_order_text = min_order_elem.get_text(strip=True)
                            if min_order_text.startswith('Min. order:'):
                                product_json_data["min_order"] = min_order_text.replace('Min. order:', '').strip()
                    except Exception as e:
                        print("Error extracting product min order:", e)
                    
                    # Extracting product supplier
                    try:
                        supplier_elem = product.select_one('.search-card-e-company')
                        if supplier_elem:
                            supplier_name = supplier_elem.get_text(strip=True)
                            product_json_data["supplier"] = supplier_name
                    except Exception as e:
                        print("Error extracting product supplier:", e)
                    
                    # Open product page to extract more details
                    if product_json_data["url"]:
                        try:
                            browser.execute_script("window.open('');")
                            browser.switch_to.window(browser.window_handles[-1])
                            browser.get(product_json_data["url"])
                            WebDriverWait(browser, 10).until(
                                lambda d: d.execute_script("return document.readyState") == "complete"
                            )
                            time.sleep(1)  # Reduced sleep time
                            product_page_html = BeautifulSoup(browser.page_source, "html.parser")

                            # Extracting product images using Selenium & BeautifulSoup together
                            try:
                                media_body = browser.find_element(
                                    By.CSS_SELECTOR, '[data-submodule="ProductImageThumbsList"]'
                                ).get_attribute('outerHTML')
                                media_soup = BeautifulSoup(media_body, 'html.parser')
                                image_elements = media_soup.select('[style*="background-image"]')
                                image_urls = set()
                                for element in image_elements:
                                    style = element.get('style', '')
                                    m = re.search(r'url\("?(.*?)"?\)', style)
                                    if m:
                                        img_url = m.group(1)
                                        if img_url.startswith('//'):
                                            img_url = 'https:' + img_url
                                        image_urls.add(img_url)
                                product_json_data["images"] = list(image_urls)
                            except Exception as e:
                                print("Error extracting product images", e)

                            # Extracting product videos
                            try:
                                video_urls = set()
                                video_elements = browser.find_elements(By.TAG_NAME, 'video')
                                for element in video_elements:
                                    video_url = element.get_attribute('src')
                                    if video_url:
                                        # Remove query string if present
                                        if '?' in video_url:
                                            video_url = video_url.split('?')[0]
                                        video_urls.add(video_url)
                                product_json_data["videos"] = list(video_urls)
                            except Exception as e:
                                print("Error extracting product videos", e)

                            # Extracting product origin
                            try:
                                attr_body = browser.find_element(By.CLASS_NAME, 'attribute-info').get_attribute('outerHTML')
                                attr_soup = BeautifulSoup(attr_body, 'html.parser')
                                for item in attr_soup.find_all('div', class_='attribute-item'):
                                    left_div = item.find('div', class_='left')
                                    if left_div and left_div.text.strip().lower() == 'place of origin':
                                        right_div = item.find('div', class_='right')
                                        if right_div:
                                            origin_value = right_div.text.strip()
                                            product_json_data["origin"] = origin_value
                                            break
                            except Exception as e:
                                print("Error extracting product origin", e)

                            print("success")

                        except Exception as e:
                            print("Error processing product page:", e)
                        finally:
                            browser.close()
                            browser.switch_to.window(browser.window_handles[0])
                    
                    scraped_products[product_json_data["url"]] = product_json_data

                break  # Exit retries for this page if successful
            except Exception as e:
                print(f"Attempt {attempt+1}/{retries}: Error scraping products from page {page}: {e}")
                time.sleep(1)
        else:
            print(f"Failed to scrape products from page {page} after {retries} attempts.")

    with open("products.json", "w", encoding="utf-8") as f:
        json.dump(list(scraped_products.values()), f, ensure_ascii=False, indent=4)
    browser.quit()
    print("Scraping completed and saved to products.json")

scrape_alibaba_products()
