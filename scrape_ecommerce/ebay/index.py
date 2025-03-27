import re
import time
import json

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Global scraping configurations
retries = 3
search_page = 1  # Adjust to desired number of pages
search_keyword = "Rolex watches"

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
            time.sleep(delay)
    return default

def scrape_ebay_products():
    scraped_products = {}  # Using URL as key to avoid duplicates

    for page in range(1, search_page+1):
        for attempt in range(retries):
            try:
                
                
                search_url = f'https://www.ebay.com/sch/i.html?_nkw={search_keyword}&_sacat=0&_from=R40&_pgn={page}'
                browser.get(search_url)
                WebDriverWait(browser, 10).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
                time.sleep(2)  # Allow dynamic content to load
                
                product_cards_container = browser.find_element(By.CSS_SELECTOR, '.srp-results.srp-list.clearfix')
                product_cards_container2 = browser.find_element(By.CSS_SELECTOR, 'srp-results.srp-grid.clearfix')
                # if not product_cards_container:
                #     print(f"No products found on page {page}")
                #     break
                if product_cards_container :
                    product_cards_html = BeautifulSoup(product_cards_container.get_attribute("outerHTML"), "html.parser")
                    product_cards = product_cards_html.find_all("div", {"class": "s-item__wrapper clearfix"})
                    for product in product_cards:
                        product_json_data = {
                            "url": "",
                            "title": "",
                            "currency": "",
                            "price": "",
                            "min_order": "",
                            "origin": "",
                            "supplier": "",
                            "feedback": {
                                "rating": "",
                                "review": "",
                            },
                            "images": [],
                            "videos": []
                        }

                        # Extracting url and title
                        try:
                            product_title_url_container = product.find("a", {"class": "s-item__link"})
                            if product_title_url_container:
                                product_title = retry_extraction(
                                    lambda: product_title_url_container.find("span", {"role": "heading"}).get_text(strip=True)
                                )
                                if product_title:
                                    product_json_data["title"] = product_title
                                product_url = product_title_url_container["href"]
                                if product_url:
                                    product_json_data["url"] = product_url.split('?')[0]
                                    print(product_json_data["url"])
                        except Exception as e:
                            print("Error extracting product title and url:", e)

                        # Avoid duplicate products by URL
                        if product_json_data["url"] in scraped_products:
                            continue
                        
                        # Extracting currency and price
                        try:
                            currency_price_element = product.find("span", {"class": "s-item__price"})
                            if currency_price_element:
                                currency_price_text = currency_price_element.get_text(strip=True)
                                if currency_price_text:
                                    currency = retry_extraction(
                                        lambda: re.match(r"([^\d\s]+(?:\s*[^\d\s])?)", currency_price_text.strip()).group(0).strip()
                                    )
                                    if currency:
                                        product_json_data["currency"] = currency
                                    price_numbers = re.findall(r'\d+(?:\.\d+)?', currency_price_text)
                                    if len(price_numbers) > 1:
                                        price_range = f"{float(price_numbers[0])} - {float(price_numbers[1])}"
                                    elif len(price_numbers) == 1:
                                        price_range = price_numbers[0]
                                    else:
                                        price_range = ""
                                    product_json_data["price"] = price_range
                        except Exception as e:
                            print("Error extracting product currency and price:", e)

                        # Extracting product origin
                        try:
                            product_origin_text = product.find("span", {"class": "s-item__location s-item__itemLocation"}).get_text(strip=True)
                            if product_origin_text:
                                if product_origin_text.startswith("from "):
                                    product_origin = product_origin_text[5:].strip()
                                else:
                                    product_origin = product_origin_text
                                product_json_data["origin"] = product_origin
                        except Exception as e:
                            print("Error extracting product origin:", e)

                        # Open product page to extract
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

                                # Extract supplier details: name
                                try:
                                    supplier_name_element = retry_extraction(
                                       lambda: product_page_html.find("h2", {"class": "x-store-information__store-name"}) 
                                    )
                                    supplier_name = supplier_name_element.get_text(strip=True)
                                    if supplier_name:
                                        product_json_data["supplier"] = supplier_name
                                except Exception as e:
                                    print("Error extracting product supplier name:", e)

                                # Extracting feedback details: rating and reviews
                                try:
                                    product_review_element_container = product_page_html.find("div", {"class": "fdbk-detail-list"})
                                    if product_review_element_container:
                                        product_review_text = product_review_element_container.find("div", {"class": "tabs__items"}).get_text(strip=True)
                                        product_review_text_match = re.search(r'\((\d+)\)', product_review_text)
                                        if product_review_text_match:
                                            product_json_data["feedback"]["review"] = product_review_text_match.group(1)
                                    product_postive_feedback_container = product_page_html.find("h4", {"class": "x-store-information__highlights"})
                                    product_postive_feedback_text = product_postive_feedback_container.find("span", {"class": "ux-textspans"}).get_text(strip=True)
                                    if product_postive_feedback_text:
                                        product_postive_feedback_match = re.search(r"(\d+(?:\.\d+)?)%", product_postive_feedback_text)
                                        if product_postive_feedback_match:
                                            positive_feedback = float(product_postive_feedback_match.group(1))
                                            raw_rating = 1 + 4 * (positive_feedback / 100)
                                            rating = round(raw_rating, 1)
                                            product_json_data["feedback"]["rating"] = rating
                                except Exception as e:
                                    print("Error extracting product ratings and reviews:", e)

                                # Media extraction: images and videos via hovering thumbnails
                                try:
                                    media_button = WebDriverWait(browser, 10).until(
                                        EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Opens image gallery']"))
                                    )
                                    media_button.click()
                                    WebDriverWait(browser, 10).until(
                                        EC.presence_of_element_located((By.CSS_SELECTOR, ".lightbox-dialog__window.lightbox-dialog__window--animate.keyboard-trap--active"))
                                    )
                                    time.sleep(1)
                                    media_container = browser.find_element(By.CSS_SELECTOR, ".lightbox-dialog__window.lightbox-dialog__window--animate.keyboard-trap--active")
                                    thumbnails_container = media_container.find_element(By.CSS_SELECTOR, "div.ux-image-grid-container.masonry-211.x-photos-max-view--show")
                                    thumbnails = thumbnails_container.find_elements(By.TAG_NAME, "button")
                                    for index, thumbnail in enumerate(thumbnails):
                                        browser.execute_script("arguments[0].scrollIntoView(true);", thumbnail)
                                        time.sleep(0.5)
                                        thumbnail.click()
                                        time.sleep(1)
                                        active_image_element = WebDriverWait(browser, 5).until(
                                            EC.presence_of_element_located((By.CSS_SELECTOR, "div.ux-image-carousel-item.image-treatment.active.image"))
                                        )
                                        media_container = browser.find_element(By.CSS_SELECTOR, ".lightbox-dialog__window.lightbox-dialog__window--animate.keyboard-trap--active")
                                        updated_html = media_container.get_attribute('outerHTML')
                                        media_soup = BeautifulSoup(updated_html, "html.parser")
                                        img_tag_container = media_soup.select_one("div.ux-image-carousel-item.image-treatment.active.image")
                                        if not img_tag_container:
                                            print(f"Active image container not found for thumbnail index {index}")
                                            continue
                                        img_tag = img_tag_container.find("img")
                                        img_src = img_tag.get("src")
                                        if img_src:
                                            product_json_data["images"].append(img_src)
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
                elif product_cards_container2 : 
                     
                    
                    product_cards_html = BeautifulSoup(product_cards_container2.get_attribute("outerHTML"), "html.parser")
                    product_cards = product_cards_html.find_all("div", {"class": "s-item__wrapper clearfix"})
                    for product in product_cards:
                        product_json_data = {
                            "url": "",
                            "title": "",
                            "currency": "",
                            "price": "",
                            "min_order": "",
                            "origin": "",
                            "supplier": "",
                            "feedback": {
                                "rating": "",
                                "review": "",
                            },
                            "images": [],
                            "videos": []
                        }

                        # Extracting url and title
                        try:
                            product_title_url_container = product.find("a", {"class": "s-item__link"})
                            if product_title_url_container:
                                product_title = retry_extraction(
                                    lambda: product_title_url_container.find("span", {"role": "heading"}).get_text(strip=True)
                                )
                                if product_title:
                                    product_json_data["title"] = product_title
                                product_url = product_title_url_container["href"]
                                if product_url:
                                    product_json_data["url"] = product_url.split('?')[0]
                                    print(product_json_data["url"])
                        except Exception as e:
                            print("Error extracting product title and url:", e)

                        # Avoid duplicate products by URL
                        if product_json_data["url"] in scraped_products:
                            continue
                        
                        # Extracting currency and price
                        try:
                            currency_price_element = product.find("span", {"class": "s-item__price"})
                            if currency_price_element:
                                currency_price_text = currency_price_element.get_text(strip=True)
                                if currency_price_text:
                                    currency = retry_extraction(
                                        lambda: re.match(r"([^\d\s]+(?:\s*[^\d\s])?)", currency_price_text.strip()).group(0).strip()
                                    )
                                    if currency:
                                        product_json_data["currency"] = currency
                                    price_numbers = re.findall(r'\d+(?:\.\d+)?', currency_price_text)
                                    if len(price_numbers) > 1:
                                        price_range = f"{float(price_numbers[0])} - {float(price_numbers[1])}"
                                    elif len(price_numbers) == 1:
                                        price_range = price_numbers[0]
                                    else:
                                        price_range = ""
                                    product_json_data["price"] = price_range
                        except Exception as e:
                            print("Error extracting product currency and price:", e)

                        # Extracting product origin
                        try:
                            product_origin_text = product.find("span", {"class": "s-item__location s-item__itemLocation"}).get_text(strip=True)
                            if product_origin_text:
                                if product_origin_text.startswith("from "):
                                    product_origin = product_origin_text[5:].strip()
                                else:
                                    product_origin = product_origin_text
                                product_json_data["origin"] = product_origin
                        except Exception as e:
                            print("Error extracting product origin:", e)

                        # Open product page to extract
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

                                # Extract supplier details: name
                                try:
                                    supplier_name_element = retry_extraction(
                                       lambda: product_page_html.find("h2", {"class": "x-store-information__store-name"}) 
                                    )
                                    supplier_name = supplier_name_element.get_text(strip=True)
                                    if supplier_name:
                                        product_json_data["supplier"] = supplier_name
                                except Exception as e:
                                    print("Error extracting product supplier name:", e)

                                # Extracting feedback details: rating and reviews
                                try:
                                    product_review_element_container = product_page_html.find("div", {"class": "fdbk-detail-list"})
                                    if product_review_element_container:
                                        product_review_text = product_review_element_container.find("div", {"class": "tabs__items"}).get_text(strip=True)
                                        product_review_text_match = re.search(r'\((\d+)\)', product_review_text)
                                        if product_review_text_match:
                                            product_json_data["feedback"]["review"] = product_review_text_match.group(1)
                                    product_postive_feedback_container = product_page_html.find("h4", {"class": "x-store-information__highlights"})
                                    product_postive_feedback_text = product_postive_feedback_container.find("span", {"class": "ux-textspans"}).get_text(strip=True)
                                    if product_postive_feedback_text:
                                        product_postive_feedback_match = re.search(r"(\d+(?:\.\d+)?)%", product_postive_feedback_text)
                                        if product_postive_feedback_match:
                                            positive_feedback = float(product_postive_feedback_match.group(1))
                                            raw_rating = 1 + 4 * (positive_feedback / 100)
                                            rating = round(raw_rating, 1)
                                            product_json_data["feedback"]["rating"] = rating
                                except Exception as e:
                                    print("Error extracting product ratings and reviews:", e)

                                # Media extraction: images and videos via hovering thumbnails
                                try:
                                    media_button = WebDriverWait(browser, 10).until(
                                        EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Opens image gallery']"))
                                    )
                                    media_button.click()
                                    WebDriverWait(browser, 10).until(
                                        EC.presence_of_element_located((By.CSS_SELECTOR, ".lightbox-dialog__window.lightbox-dialog__window--animate.keyboard-trap--active"))
                                    )
                                    time.sleep(1)
                                    media_container = browser.find_element(By.CSS_SELECTOR, ".lightbox-dialog__window.lightbox-dialog__window--animate.keyboard-trap--active")
                                    thumbnails_container = media_container.find_element(By.CSS_SELECTOR, "div.ux-image-grid-container.masonry-211.x-photos-max-view--show")
                                    thumbnails = thumbnails_container.find_elements(By.TAG_NAME, "button")
                                    for index, thumbnail in enumerate(thumbnails):
                                        browser.execute_script("arguments[0].scrollIntoView(true);", thumbnail)
                                        time.sleep(0.5)
                                        thumbnail.click()
                                        time.sleep(1)
                                        active_image_element = WebDriverWait(browser, 5).until(
                                            EC.presence_of_element_located((By.CSS_SELECTOR, "div.ux-image-carousel-item.image-treatment.active.image"))
                                        )
                                        media_container = browser.find_element(By.CSS_SELECTOR, ".lightbox-dialog__window.lightbox-dialog__window--animate.keyboard-trap--active")
                                        updated_html = media_container.get_attribute('outerHTML')
                                        media_soup = BeautifulSoup(updated_html, "html.parser")
                                        img_tag_container = media_soup.select_one("div.ux-image-carousel-item.image-treatment.active.image")
                                        if not img_tag_container:
                                            print(f"Active image container not found for thumbnail index {index}")
                                            continue
                                        img_tag = img_tag_container.find("img")
                                        img_src = img_tag.get("src")
                                        if img_src:
                                            product_json_data["images"].append(img_src)
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
                else: 
                    if not product_cards_container2: 
                        print(f"No products found on page {page}")
                        break
                    


                
            
            except Exception as e:
                print(f"Attempt {attempt+1}/{retries}: Error scraping products from page {page}: {e}")
                time.sleep(2)
        else:
            print(f"Failed to scrape products from page {page} after {retries} attempts.")

    # Save all unique scraped products to a JSON file
    with open("rolex_watch.json", "w", encoding="utf-8") as f:
        json.dump(list(scraped_products.values()), f, ensure_ascii=False, indent=4)
    browser.quit()
    print("Scraping completed and saved to rolex_watch.json")

scrape_ebay_products()