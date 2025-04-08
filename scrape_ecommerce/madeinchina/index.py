import time 
import json
import os
import requests
import random
import re

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

# Create images folder if it doesn't exist
os.makedirs("images", exist_ok=True)

# Initialize the products.json file as an empty list for incremental insertion
with open("products.json", "w", encoding="utf-8") as f:
    json.dump([], f)

# Global scraping configurations
retries = 3
search_page = 100  # Adjust to desired number of pages
search_keyword = "Christian Dior perfumes"  # Adjust to desired search keyword

# Setup Selenium configurations
options = webdriver.FirefoxOptions()
options.add_argument("--ignore-certificate-errors")
options.add_argument("--log-level=3")
browser = webdriver.Firefox(options=options)
browser.maximize_window()

def retry_extraction(func, attempts=3, delay=1, default=""):
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
            time.sleep(5)
    return default

def append_product_to_json(product):
    """
    Appends a product to the products.json file incrementally.
    Reads the existing JSON data, appends the new product, and writes it back.
    """
    try:
        if os.path.exists("products.json"):
            with open("products.json", "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except Exception:
                    data = []
        else:
            data = []
        data.append(product)
        with open("products.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print("Error appending product to JSON file:", e)

def scrape_madeinchina_products():
    scraped_products = {}  # Using URL as key to avoid duplicates
    for page in range(1, search_page+1):
        for attempt in range(retries):
            try:
                search_url = f'https://www.made-in-china.com/multi-search/{search_keyword}/F1/{page}.html?pv_id=1ik76htapa40&faw_id=null'
                browser.get(search_url)
                WebDriverWait(browser, 10).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
                time.sleep(5)  # Allow dynamic content to load
                product_cards_container = browser.find_element(By.CSS_SELECTOR, '.prod-list')
                if not product_cards_container:
                    print(f"No products found on page {page}")
                    break
                product_cards_html = BeautifulSoup(product_cards_container.get_attribute("outerHTML"), "html.parser")
                product_cards = product_cards_html.find_all("div", {"class": "prod-info"})
                for product in product_cards:
                    product_json_data = {
                        "url": "",
                        "title": "",
                        "currency": "",
                        "price": "",
                        "min_order": "",
                        "supplier": "",
                        "origin": "",
                        "feedback": {
                            "rating": "",
                            "review": "",
                        },
                        "images": [],
                        "videos": []
                    }

                    # Extracting product url
                    try:
                        product_link = product.select_one('.product-name a').get('href')
                        if product_link.startswith('//'):
                            product_url = 'https:' + product_link
                        else:
                            product_url = product_link
                        if product_url:
                            product_json_data["url"] = product_url
                    except Exception as e:
                        print("Error extracting product url:", e)

                    # Extracting product title
                    try:
                        product_title = product.select_one('.product-name').get('title').strip()
                        if product_title:
                            product_json_data["title"] = product_title
                    except Exception as e:
                        print("Error extracting product title:", e)

                    # Avoid duplicate products by URL
                    if product_json_data["url"] in scraped_products:
                        continue

                    # Extracting product currency and price
                    try:
                        currency_price_element = product.select_one('.product-property .price-info .price')
                        if currency_price_element:
                            currency_price_text = currency_price_element.get_text(strip=True)
                            if currency_price_text:
                                currency = ''.join([c for c in currency_price_text if not c.isdigit() and c not in ['.', '-', ' ']]).strip()
                                if currency:
                                    product_json_data["currency"] = currency
                                price_range = currency_price_text.replace(currency, '').strip()
                                if price_range:
                                    product_json_data["price"] = price_range
                    except Exception as e:
                        print("Error extracting product currency and price:", e)      

                    # Extracting product minimum order
                    try:
                        min_order_element = product.find_all('div', class_='info')
                        for min_order_info in min_order_element:
                            # Check if the text contains '(MOQ)'
                            if '(MOQ)' in min_order_info.text:
                                min_order_text = min_order_info.text.strip()
                                # Remove '(MOQ)' and strip extra spaces
                                min_order = min_order_text.replace('(MOQ)', '').strip()
                                product_json_data["min_order"] = min_order
                                break
                    except Exception as e:
                        print("Error extracting product minimum order:", e)
                    
                    # Extracting product supplier name
                    try:
                        supplier_name_element = product.select_one('.company-name-wrapper .compnay-name span')
                        if supplier_name_element:
                            supplier_name = supplier_name_element.get_text(strip=True)
                            if supplier_name:
                                product_json_data["supplier"] = supplier_name
                        else:
                            supplier_name_container = retry_extraction(
                                lambda: product.find("div", {"class": "company-name-wrapper"})
                            )
                            supplier_name_element = supplier_name_container.find("span", {"class": "compnay-name"})
                            supplier_name = supplier_name_element.get_text(strip=True)
                            if supplier_name:
                                product_json_data["supplier"] = supplier_name
                    except Exception as e:
                        print("Error extracting product supplier name:", e)
                    
                    # Open product page to extract
                    if product_json_data["url"]:
                        try:
                            browser.execute_script("window.open('');")
                            browser.switch_to.window(browser.window_handles[-1])
                            browser.get(product_json_data["url"])
                            WebDriverWait(browser, 10).until(
                                lambda d: d.execute_script("return document.readyState") == "complete"
                            )
                            time.sleep(5)
                            product_page_html = BeautifulSoup(browser.page_source, "html.parser")

                            # Extracting product origin
                            try:
                                product_origin_info = product_page_html.select_one('.basic-info-list')
                                if product_origin_info:
                                    product_origin_container = product_origin_info.find_all('div', class_='bsc-item cf')
                                    for item in product_origin_container:
                                        label = item.find('div', class_='bac-item-label fl')
                                        if label and 'Origin' in label.text:
                                            product_origin_element = item.find('div', class_='bac-item-value fl')
                                            if product_origin_element:
                                                product_origin = product_origin_element.get_text(strip=True)
                                                product_json_data["origin"] = product_origin
                            except Exception as e:
                                print("Error extracting product origin:", e)
                            
                            # Extracting product images and videos
                            try:
                                product_media_swiper_container = retry_extraction(
                                    lambda: product_page_html.find("div", {"class": "sr-proMainInfo-slide-container swiper-container J-pic-list-container swiper-container-horizontal swiper-container-autoheight"})
                                )
                                product_media_swiper_element = retry_extraction(
                                    lambda: product_media_swiper_container.find("div", {"class": "swiper-wrapper"})
                                )
                                product_media_containers = retry_extraction(
                                    lambda: product_media_swiper_element.find_all("div", {"class": "sr-prMainInfo-slide-inner"})
                                )
                                for media in product_media_containers:
                                    # video
                                    product_video_element = media.find_all("script", {"type": "text/data-video"})
                                    if product_video_element:
                                        for video_element in product_video_element:
                                            video_script_text = video_element.get_text(strip=True)
                                            try:
                                                video_data = json.loads(video_script_text)
                                                video_url = video_data.get("videoUrl")
                                                product_json_data["videos"].append(video_url)
                                            except Exception as e:
                                                print("Error parsing video data:", e)
                                    # Images
                                    product_img_element = media.find_all("img")
                                    if product_img_element:
                                        for img_element in product_img_element:
                                            img = img_element["src"]
                                            if img.startswith('//'):
                                                img = 'https:' + img
                                            product_json_data["images"].append(img)
                            except Exception as e:
                                print("Error extracting product media: images and videos:", e)
                            
                            if not product_json_data["images"] and not product_json_data["videos"]:
                                try:
                                    product_image_container = retry_extraction(
                                        lambda: product_page_html.find("div", {"id": "pic-list"})
                                    )
                                    product_image = retry_extraction(
                                        lambda: product_image_container.find("img", {"data-faw_img": "true"})["src"]
                                    )
                                    if product_image:
                                        if  product_image.startswith("//"):
                                            product_image = 'https:'+product_image
                                        product_json_data["images"].append(product_image)
                                except Exception as e:
                                    print("Error extracting product media: images and videos:", e)

                        except Exception as e:
                            print("Error processing product page:", e)
                        finally:
                            browser.close()
                            browser.switch_to.window(browser.window_handles[0]) 

                    # Download images and update the images list with local filenames
                    downloaded_images = []
                    for image_url in product_json_data["images"]:
                        try:
                            rand_number = random.randint(100000, 999999)
                            if product_json_data["url"]:
                                domain = re.findall(r'https?://(?:www\.)?([^/]+)', product_json_data["url"])
                                website_name = domain[0] if domain else "unknown"
                            else:
                                website_name = "unknown"
                            formatted_keyword = search_keyword.replace(" ", "-")
                            filename = f"{website_name}-{formatted_keyword}-{rand_number}.jpg"
                            response = requests.get(image_url, stream=True)
                            if response.status_code == 200:
                                filepath = os.path.join("images", filename)
                                with open(filepath, "wb") as f:
                                    for chunk in response.iter_content(1024):
                                        f.write(chunk)
                                downloaded_images.append(filename)
                            else:
                                print("Failed to download image from", image_url)
                        except Exception as e:
                            print("Error downloading image:", e)
                    product_json_data["images"] = downloaded_images

                    # Save unique product and append to JSON file incrementally
                    scraped_products[product_json_data["url"]] = product_json_data
                    append_product_to_json(product_json_data)
                
                # Break out of the retry loop for the page if successful
                break
            except Exception as e:
                print(f"Attempt {attempt+1}/{retries}: Error scraping products from page {page}: {e}")
                time.sleep(5)
        else:
            print(f"Failed to scrape products from page {page} after {retries} attempts.")
    
    # Save all unique scraped products to a JSON file
    with open("products.json", "w", encoding="utf-8") as f:
        json.dump(list(scraped_products.values()), f, ensure_ascii=False, indent=4)
    browser.quit()
    print("Scraping completed and saved to products.json")

scrape_madeinchina_products()
