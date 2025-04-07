import re
import time
import json
import os
import random
import requests
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Global scraping configurations
retries = 2
search_page = 20  # Adjust to desired number of pages
search_keyword = "Rolex Watches"

# Setup Selenium configurations
options = webdriver.ChromeOptions()
options.add_argument("--ignore-certificate-errors")
options.add_argument("--log-level=3")
# options.add_argument("--headless")  # Comment out to see the browser
browser = webdriver.Chrome(options=options)
browser.maximize_window()

# Output file for saving scraped data
output_file = "products.json"

# Create images folder if it doesn't exist
images_folder = "images"
if not os.path.exists(images_folder):
    os.makedirs(images_folder)

def initialize_json_file():
    """Initialize the JSON file with an opening bracket."""
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("[\n")

def finalize_json_file():
    """Finalize the JSON file by closing the JSON array."""
    with open(output_file, "a", encoding="utf-8") as f:
        f.write("\n]")

def save_product(product_data, first_product=False):
    """Append a product's data to the JSON file."""
    with open(output_file, "a", encoding="utf-8") as f:
        if not first_product:
            f.write(",\n")
        json.dump(product_data, f, ensure_ascii=False, indent=4)

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

def download_image(image_url, search_keyword, product_url):
    """
    Downloads an image from image_url and saves it in the images folder with a filename formatted as:
    websitename-keyword-<random six-digit number>.<extension>
    """
    try:
        # Extract website name from product_url
        parsed_product_url = urlparse(product_url)
        website = parsed_product_url.netloc.replace("www.", "") if parsed_product_url.netloc else "unknown"
        
        # Format the keyword (replace spaces with underscores)
        formatted_keyword = search_keyword.replace(" ", "_")
        
        # Generate a random six-digit number
        random_number = random.randint(100000, 999999)
        
        # Extract the file extension from the image URL
        parsed_image_url = urlparse(image_url)
        path = parsed_image_url.path
        ext = os.path.splitext(path)[1]
        if not ext:
            ext = ".jpg"
        
        # Construct the file name and path
        file_name = f"{website}-{formatted_keyword}-{random_number}{ext}"
        file_path = os.path.join(images_folder, file_name)
        
        # Download the image
        response = requests.get(image_url, timeout=10)
        if response.status_code == 200:
            with open(file_path, "wb") as f:
                f.write(response.content)
            print(f"Downloaded image: {file_name}")
        else:
            print(f"Failed to download image: {image_url}, status: {response.status_code}")
    except Exception as e:
        print(f"Error downloading image: {image_url}, error: {e}")

def scrape_alibaba_products():
    initialize_json_file()
    scraped_urls = set()  # Using URL to avoid duplicates
    first_product = True  # Flag to check if we are saving the first product
    for page in range(1, search_page + 1):
        for attempt in range(retries):
            try:
                search_url = f'https://www.alibaba.com/trade/search?fsb=y&IndexArea=product_en&keywords={search_keyword}&originKeywords={search_keyword}&tab=all&&page={page}&spm=a2700.galleryofferlist.pagination.0'
                browser.get(search_url)
                time.sleep(3)  # Allow dynamic content to load
                product_cards = browser.find_elements(By.CLASS_NAME, 'fy23-search-card')
                for product_elem in product_cards:
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
                            if product_url:
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
                    if product_json_data["url"] in scraped_urls:
                        continue

                    # Extracting product currency and price
                    try:
                        product_currency_price_element = retry_extraction(
                            lambda: product.select_one('.search-card-e-price-main')
                        )
                        if product_currency_price_element:
                            product_currency_price = product_currency_price_element.get_text(strip=True)
                            if product_currency_price:
                                currency = ''.join([c for c in product_currency_price if not c.isdigit() and c not in ['.', '-', ' ']]).strip()
                                fixed_currency = currency[0]
                                product_json_data["currency"] = fixed_currency
                                product_json_data["price"] = product_currency_price.replace(fixed_currency, '').strip()
                    except Exception as e:
                        print("Error extracting product currency and price:", e)
                    
                    # Extracting product min order
                    try:
                        product_min_order_element = retry_extraction(
                            lambda: product.select_one('.search-card-m-sale-features__item')
                        )
                        if product_min_order_element:
                            product_min_order = product_min_order_element.get_text(strip=True)
                            if product_min_order.startswith('Min. order:'):
                                product_json_data["min_order"] = product_min_order.replace('Min. order:', '').strip()
                    except Exception as e:
                        print("Error extracting product min order:", e)
                    
                    # Extracting product supplier
                    try:
                        supplier_name_element = product.select_one('.search-card-e-company')
                        if supplier_name_element:
                            supplier_name = supplier_name_element.get_text(strip=True)
                            if supplier_name:
                                product_json_data["supplier"] = supplier_name
                    except Exception as e:
                        print("Error extracting product supplier:", e)

                    # Extracting product feedback: ratings and reviews
                    try:
                        feedback_element = product.select_one('.search-card-e-review')
                        if feedback_element:
                            rating = feedback_element.find("strong").get_text(strip=True)
                            product_json_data["feedback"]["rating"] = rating
                            review_text = feedback_element.find("span").get_text(strip=True)
                            review = review_text.split()[0]
                            product_json_data["feedback"]["review"] = review
                    except Exception as e:
                        print("Error extracting product ratings and reviews:", e)
                    
                    # Open product page to extract additional details
                    if product_json_data["url"]:
                        try:
                            browser.execute_script("window.open('');")
                            browser.switch_to.window(browser.window_handles[-1])
                            browser.get(product_json_data["url"])
                            time.sleep(2)

                            # Extracting product images
                            # try:
                            #     # Locate the thumbnails container
                            #     thumbs_container = browser.find_element(
                            #         By.CSS_SELECTOR,
                            #         '[data-submodule="ProductImageThumbsList"]'
                            #     )
                            #     # Find each thumbnail element (they have inline background‑image styles)
                            #     thumb_elements = thumbs_container.find_elements(
                            #         By.CSS_SELECTOR,
                            #         '[style*="background-image"]'
                            #     )
                            #     image_urls = set()
                            
                            #     for thumb in thumb_elements:
                                    
                            #             # Scroll thumbnail into view & click it
                                        
                            #         browser.execute_script("arguments[0].scrollIntoView(true);", thumb)
                                        
                            #         thumb.click()
                                        
                            #         time.sleep(2)
                            #         product_image_view = browser.find_element(By.CSS_SELECTOR, '[data-testid="product-image-view"]')
                            #         product_image_link = product_image_view.get_attribute('src')
                            #         if product_image_link.startswith('//'):
                            #             product_image_link = 'https:' + product_image_link
                            #         image_urls.add(product_image_link)
                            #         # style = element.get('style', '')
                            #         # if 'background-image' in style:
                            #         #     start_index = style.find('url("') + 5
                            #         #     end_index = style.find('")', start_index)
                            #         #     if start_index != -1 and end_index != -1:
                            #         #         image_url = style[start_index:end_index]
                            #         #         if image_url.startswith('//'):
                            #         #             image_url = 'https:' + image_url
                            #         #         image_urls.add(image_url)
                            #     product_json_data["images"] = list(image_urls)
                            #     # Download each image immediately
                            #     for img_url in image_urls:
                            #         download_image(img_url, search_keyword, product_json_data["url"])
                            # except Exception as e:
                            #     print("Error extracting product images", e)

                            # Extracting product videos
                            try:
                                video_urls = set()
                                video_elements = browser.find_elements(By.TAG_NAME, 'video')
                                if video_elements:
                                    for element in video_elements:
                                        video_url = element.get_attribute('src')
                                        if '?' in video_url:
                                            video_url = video_url.split('?')[0]
                                        elif 'blob' in video_url:
                                            video_url = video_url.split('blob')[1]
                                            if not video_url.startswith('https://'):
                                                video_url = 'https://' + video_url.split('://')[1]
                                        video_urls.add(video_url)
                                    product_json_data["videos"] = list(video_urls)
                            except Exception as e:
                                print("Error extracting product videos", e)

                            # Extracting product origin
                            try:
                                other_attributes_body = browser.find_element(By.CLASS_NAME, 'attribute-info').get_attribute('outerHTML')
                                other_attributes_soup = BeautifulSoup(other_attributes_body, 'html.parser')
                                attribute_items = other_attributes_soup.find_all('div', class_='attribute-item')
                                for item in attribute_items:
                                    left_div = item.find('div', class_='left')
                                    if left_div and left_div.text.strip() == 'Place of Origin':
                                        right_div = item.find('div', class_='right')
                                        if right_div:
                                            origin_value = right_div.text.strip()
                                            break
                                product_json_data["origin"] = origin_value
                            except Exception as e:
                                print("Error extracting product origin", e)

                        except Exception as e:
                            print("Error processing product page:", e)
                        finally:
                            browser.close()
                            browser.switch_to.window(browser.window_handles[0])
                    
                    # Save product one by one instead of storing all in memory
                    if product_json_data["url"] not in scraped_urls:
                        save_product(product_json_data, first_product)
                        scraped_urls.add(product_json_data["url"])
                        if first_product:
                            first_product = False
                
                # Break out of the retry loop for the page if successful
                break
            except Exception as e:
                print(f"Attempt {attempt+1}/{retries}: Error scraping products from page {page}: {e}")
                time.sleep(1)
        else:
            print(f"Failed to scrape products from page {page} after {retries} attempts.")
    
    finalize_json_file()
    browser.quit()
    print("Scraping completed and saved to products.json")

scrape_alibaba_products()
