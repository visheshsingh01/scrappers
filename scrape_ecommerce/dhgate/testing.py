import re
import time
import json

from tqdm import tqdm
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Global scraping configurations
retries = 2
search_page = 1  # Adjust to desired number of pages
search_keyword = "Rolex Watches"

# Setup Selenium configurations
options = webdriver.FirefoxOptions()
options.add_argument("--ignore-certificate-errors")
options.add_argument("--log-level=3")
options.add_argument("--headless")
browser = webdriver.Firefox(options=options)
browser.maximize_window()

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

def scrape_dhgate_products():
    scraped_products = {}  # Using URL as key to avoid duplicates

    # Outer progress bar for pages
    for page in tqdm(range(search_page), desc="Scraping pages", unit="page"):
        for attempt in range(retries):
            try:
                search_url = f'https://www.dhgate.com/wholesale/search.do?act=search&searchkey={search_keyword}&pageNum={page}'
                browser.get(search_url)
                WebDriverWait(browser, 10).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
                time.sleep(2)  # Allow dynamic content to load
                product_cards = browser.find_elements(By.CLASS_NAME, 'gallery-main')
                if not product_cards:
                    print(f"No products found on page {page}")
                    break

                # Nested progress bar for products on this page
                for product in tqdm(product_cards, desc=f"Scraping products on page {page+1}", leave=False):
                    product_json_data = {
                        "url": "",
                        "title": "",
                        "currency": "",
                        "price": "",
                        "min_order": "",
                        "origin": "",
                        "feedback": {
                            "rating": "",
                            "review": "",
                        },
                        "supplier": {
                            "name": "",
                            "status": ""
                        },
                        "images": [],
                        "videos": []
                    }
                    try:
                        product_html = BeautifulSoup(product.get_attribute('outerHTML'), "html.parser")
                    except Exception as e:
                        print("Error parsing product HTML:", e)
                        continue

                    # Price, currency, and min order extraction
                    try:
                        price_element = product_html.find("p", {"class": "current-price"})
                        if price_element:
                            price_text = price_element.get_text(strip=True)
                            if price_text:
                                currency = retry_extraction(
                                    lambda: re.match(r"([^\d\s]+(?:\s*[^\d\s])?)", price_text.strip()).group(0).strip(),
                                    attempts=3, delay=1, default=""
                                )
                                price_numbers = retry_extraction(
                                    lambda: re.findall(r"\d+(?:\.\d+)?", price_text),
                                    attempts=3, delay=1, default=[]
                                )
                                if price_numbers:
                                    price_range = f"{int(float(price_numbers[0]))}"
                                    if len(price_numbers) > 1:
                                        price_range += f" - {int(float(price_numbers[1]))}"
                                else:
                                    price_range = ""
                                min_order = retry_extraction(
                                    lambda: f"1 {re.search(r'/\s*(\w+)', price_text).group(1)}",
                                    attempts=3, delay=1, default="1 Unit"
                                )
                                product_json_data["currency"] = currency
                                product_json_data["price"] = price_range
                                product_json_data["min_order"] = min_order
                    except Exception as e:
                        print("Error extracting price details:", e)

                    # Supplier extraction
                    try:
                        supplier_name = retry_extraction(
                            lambda: product_html.find("div", {"class": "store-name"}).find("a").get_text(strip=True),
                            attempts=3, delay=1, default=""
                        )
                        product_json_data["supplier"]["name"] = supplier_name
                    except Exception as e:
                        print("Error extracting supplier details:", e)

                    # Product rating extraction
                    try:
                        rating = retry_extraction(
                            lambda: product_html.find("span", {"class": "reviews-info"}).get_text(strip=True),
                            attempts=3, delay=1, default=""
                        )
                        product_json_data["feedback"]["rating"] = rating
                    except Exception as e:
                        print("Error extracting product rating:", e)

                    # Product URL and title extraction
                    try:
                        title_div = retry_extraction(
                            lambda: product_html.find('div', {"class": "gallery-pro-name"}),
                            attempts=3, delay=1, default=None
                        )
                        if title_div:
                            a_tag = retry_extraction(
                                lambda: title_div.find("a"),
                                attempts=3, delay=1, default=None
                            )
                            if a_tag:
                                product_title = a_tag.get("title", "").strip()
                                product_url = a_tag.get("href", "").strip()
                                product_json_data["title"] = product_title
                                product_json_data["url"] = product_url
                    except Exception as e:
                        print("Error extracting product URL and title:", e)

                    # Avoid duplicate products by URL
                    if product_json_data["url"] in scraped_products:
                        continue

                    # Open product page to extract review and media details
                    if product_json_data["url"]:
                        try:
                            browser.execute_script("window.open('');")
                            browser.switch_to.window(browser.window_handles[-1])
                            browser.get(product_json_data["url"])
                            WebDriverWait(browser, 10).until(
                                lambda d: d.execute_script("return document.readyState") == "complete"
                            )
                            time.sleep(2)
                            product_page_html = BeautifulSoup(browser.page_source, "html.parser")
                            
                            # Review extraction
                            try:
                                review_text = retry_extraction(
                                    lambda: product_page_html.find("span", {"class": "productSellerMsg_reviewsCount__HJ3MJ"}).get_text(strip=True),
                                    attempts=3, delay=1, default=""
                                )
                                if review_text:
                                    review_match = re.search(r'\d+', review_text)
                                    if review_match:
                                        product_json_data["feedback"]["review"] = review_match.group(0)
                            except Exception as e:
                                print("Error extracting product review:", e)
                            
                            # Media extraction: images and videos via hovering thumbnails
                            try:
                                thumbnails = retry_extraction(
                                    lambda: browser.find_elements(By.CSS_SELECTOR, "ul.masterMap_smallMapList__JTkBX li"),
                                    attempts=3, delay=1, default=[]
                                )
                                media_images = set()
                                media_videos = set()
                                for thumb in thumbnails:
                                    try:
                                        ActionChains(browser).move_to_element(thumb).perform()
                                        time.sleep(1)
                                        media_soup = BeautifulSoup(browser.page_source, "html.parser")
                                        big_map_div = media_soup.find("div", {"class": "masterMap_bigMapWarp__2Jzw2"})
                                        if big_map_div:
                                            video_tag = big_map_div.find("video")
                                            if video_tag and video_tag.get("src"):
                                                media_videos.add(video_tag.get("src"))
                                            else:
                                                image_tag = big_map_div.find("img")
                                                if image_tag and image_tag.get("src"):
                                                    media_images.add(image_tag.get("src"))
                                    except Exception as e:
                                        print("Error extracting media for a thumbnail:", e)
                                product_json_data["images"] = list(media_images)
                                product_json_data["videos"] = list(media_videos)
                            except Exception as e:
                                print("Error extracting product images and videos:", e)
                        except Exception as e:
                            print("Error processing product page:", e)
                        finally:
                            browser.close()
                            browser.switch_to.window(browser.window_handles[0])
                    
                    # Save unique product
                    scraped_products[product_json_data["url"]] = product_json_data

                # Break out of the retry loop for the page if successful
                break
            except Exception as e:
                print(f"Attempt {attempt+1}/{retries}: Error scraping products from page {page}: {e}")
                time.sleep(2)
        else:
            print(f"Failed to scrape products from page {page} after {retries} attempts.")
    
    # Save all unique scraped products to a JSON file
    with open("products.json", "w", encoding="utf-8") as f:
        json.dump(list(scraped_products.values()), f, ensure_ascii=False, indent=4)
    browser.quit()
    print("Scraping completed and saved to products.json")

scrape_dhgate_products()
