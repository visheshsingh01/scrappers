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
search_keyword = "laptops"

# Setup Selenium configurations
options = webdriver.ChromeOptions()
options.add_argument("--ignore-certificate-errors")
options.add_argument("--log-level=3")
browser = webdriver.Chrome(options=options)
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

def scrape_amazon_products():
    scraped_products = {}  # Using URL as key to avoid duplicates
    for page in range(1, search_page+1):
        for attempt in range(retries):
            try:
                search_url = f'https://www.amazon.in/s?k={search_keyword}&page={page}&xpid=cmkUTDSjFdfFO'
                browser.get(search_url)
                WebDriverWait(browser, 10).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
                time.sleep(2)  # Allow dynamic content to load
                html_data = BeautifulSoup(browser.page_source, 'html.parser')
                # no_of_pages = html_data.find('span', {"class": "s-pagination-item s-pagination-disabled"}).get_text(strip=True)
                product_cards_container = browser.find_element(By.XPATH, '//span[@data-component-type="s-search-results"]')
                if not product_cards_container:
                    print(f"No products found on page {page}")
                    break
                product_cards_html = BeautifulSoup(product_cards_container.get_attribute("outerHTML"), "html.parser")
                product_cards = product_cards_html.find_all("div", {"role": "listitem"})
                for product in product_cards:
                    product_json_data = {
                        "url": "",
                        "title": "",
                        "currency": "",
                        "price": "",
                        "description" : "",
                        "min_order": "1 unit",
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
                        product_link = retry_extraction(
                            lambda: product.find("a", {"class": "a-link-normal s-line-clamp-2 s-link-style a-text-normal"})["href"]
                        )
                        if product_link:
                            if product_link.startswith("https://www.amazon.in"):
                                product_url = product_link
                            else:
                                product_url = f"https://www.amazon.in{product_link}"
                            if product_url:
                                product_json_data["url"] = product_url
                    except Exception as e:
                        print("Error extracting product url:", e)

                    # Extracting product title
                    try:
                        title_elem  = retry_extraction(
                            lambda: product.find("a", {"class": "a-link-normal s-line-clamp-2 s-link-style a-text-normal"})
                        )
                        if title_elem:
                            product_title = title_elem.get_text(strip=True)
                            product_json_data["title"] = product_title
                    except Exception as e:
                        print("Error extracting product title:", e)

                    # Avoid duplicate products by URL
                    if product_json_data["url"] in scraped_products:
                        continue

                    # Extracting product currency
                    try:
                        product_currency_element = retry_extraction(
                            lambda: product.find("span", {"class": "a-price-symbol"})
                        )
                        if product_currency_element:
                            product_currency = product_currency_element.get_text(strip=True)
                            if product_currency:
                                product_json_data["currency"] = product_currency
                    except Exception as e:
                        print("Error extracting product currency:", e)

                    # Extracting product price
                    try:
                        product_price_element = retry_extraction(
                            lambda: product.find("span", {"class": "a-price-whole"})
                        )
                        if product_price_element:
                            product_price = product_price_element.get_text(strip=True)
                            if product_price:
                                product_json_data["price"] = product_price
                    except Exception as e:
                        print("Error extracting product currency:", e)

                    #Extracting product description 

                    try : 
                        product_description_element = retry_extraction(
                            lambda : browser.find_elements(By.CSS_SELECTOR, "div.feature-bullets li")
                        )
                        if product_description_element : 
                            print("Product description is found")
                            product_description = product_description_element.get_text(strip=True)
                            product_json_data["description"] = product_description

                    except Exception as e : 
                        print("Product description is not found")

                    # Open product page to extract
                    if product_json_data["url"]:
                        try:
                            browser.execute_script("window.open('');")
                            browser.switch_to.window(browser.window_handles[-1])
                            browser.get(product_json_data["url"])
                            WebDriverWait(browser, 10).until(
                                lambda d: d.execute_script("return document.readyState") == "complete"
                            )
                            time.sleep(1)
                            product_page_html = BeautifulSoup(browser.page_source, "html.parser")

                            # Extracting product reviews
                            try:
                                product_review_element = retry_extraction(
                                    lambda: product_page_html.find("span", {"id": "acrCustomerReviewText"})
                                )
                                if product_review_element:
                                    product_review_text = product_review_element.get_text(strip=True)
                                    if product_review_text:
                                        numeric_match = re.search(r"(\d+)", product_review_text)
                                        if numeric_match:
                                            numeric_value = numeric_match.group(1)
                                            product_json_data["feedback"]["review"] = numeric_value
                            except Exception as e:
                                print("Error extracting product reviews:", e)

                            # Extracting product rating
                            try:
                                product_rating_element = retry_extraction(
                                    lambda: product_page_html.find(
                                        lambda tag: tag.name == "span" and tag.get("id") == "acrPopover" and "reviewCountTextLinkedHistogram" in tag.get("class", []) and tag.has_attr("title")
                                    )
                                )
                                if product_rating_element:
                                    rating_span = product_rating_element.find("span", {"class": "a-size-base a-color-base"})
                                    if rating_span:
                                        rating_value = rating_span.get_text(strip=True)
                                        product_json_data["feedback"]["rating"] = rating_value
                            except Exception as e:
                                print("Error extracting product reviews:", e)

                            # Extracting product supplier
                            try:
                                product_supplier_element = retry_extraction(
                                    lambda: product_page_html.find("a", {"id": "sellerProfileTriggerId"})
                                )
                                if product_supplier_element:
                                    product_supplier = product_supplier_element.get_text(strip=True)
                                    if product_supplier:
                                        product_json_data["supplier"] = product_supplier
                            except Exception as e:
                                print("Error extracting product supplier:", e)

                            # Extracting product media: images and videos
                            try:
                                media_btn = WebDriverWait(browser, 10).until(
                                    EC.element_to_be_clickable((By.ID, "imgTagWrapperId"))
                                )
                                if media_btn:
                                    media_btn.click()
                                    time.sleep(1)
                                # Extracting product images
                                try:
                                    product_images = browser.find_elements(
                                        By.CSS_SELECTOR,
                                        "div.ivThumb[data-csa-c-type='item'][data-csa-c-component='imageBlock'][data-csa-c-content-id='image-block-immersive-view-alt-image']"
                                    )
                                    if product_images:
                                        image_arr = set()
                                        for image_btn in product_images:
                                            image_btn.click()
                                            time.sleep(1)
                                            image_container = WebDriverWait(browser, 10).until(
                                                EC.presence_of_element_located((By.ID, "ivLargeImage"))
                                            )
                                            if image_container:
                                                image_html = BeautifulSoup(image_container.get_attribute("outerHTML"), "html.parser")
                                                image_tag = image_html.find("img")
                                                if image_tag and image_tag.has_attr("src"):
                                                    image_src = image_tag["src"]
                                                    image_arr.add(image_src)
                                        product_json_data["images"] = list(image_arr)
                                except Exception as e:
                                    print("Error extracting product images:", e)
                                
                                # Open video tab
                                video_btn = WebDriverWait(browser, 10).until(
                                    EC.element_to_be_clickable((By.ID, "ivVideosTabHeading"))
                                )
                                if video_btn:
                                    video_btn.click()
                                    time.sleep(1)
                                # Extracting product videos
                                try:
                                    product_videos_container = browser.find_element(By.CSS_SELECTOR, "div.div-relatedvideos" )
                                    if product_videos_container:
                                        product_videos = product_videos_container.find_elements(
                                            By.CSS_SELECTOR,
                                            "a.a-link-normal.vse-carousel-item[role='button']"
                                        )
                                        if product_videos:
                                            video_arr = set()
                                            for videos_element in product_videos:
                                                video = videos_element.get_attribute("href")
                                                if video:
                                                    if video.startswith("https://www.amazon.in"):
                                                        video_arr.add(video)
                                                    else:
                                                        video_url = f"https://www.amazon.in{video}"
                                                        video_arr.add(video_url)
                                            product_json_data["videos"] = list(video_arr)
                                except Exception as e:
                                    print("Error extracting product videos:", e)
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
                time.sleep(1)
        else:
            print(f"Failed to scrape products from page {page} after {retries} attempts.")

    # Save all unique scraped products to a JSON file
    with open("amazon_nike.json", "w", encoding="utf-8") as f:
        json.dump(list(scraped_products.values()), f, ensure_ascii=False, indent=4)
    browser.quit()
    print("Scraping completed and saved to products.json")

scrape_amazon_products()