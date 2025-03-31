import re
import time
import json

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# Global scraping configurations
retries = 2
search_page = 1  # Adjust to desired number of pages
search_keyword = "nike shoes"

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
                                print("this is the product currency: ",product_currency)
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
                                print("this is the product price :", product_price)
                                product_json_data["price"] = product_price
                    except Exception as e:
                        print("Error extracting product currency:", e)
                        
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
                            
                            try:
                                # Primary selector: Wait until all description elements are present.
                                description_elements = WebDriverWait(browser, 10).until(
                                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#feature-bullets li.a-spacing-mini"))
                                )

                                if description_elements:
                                        for element in description_elements:
                                            browser.execute_script("arguments[0].scrollIntoView(true);", element)
                                            time.sleep(0.5)
                                            print(element.text)
                            except TimeoutException:
                                print("Primary selector elements not found, trying alternative selector...")
                                try:
                                    # Alternative selector: Wait for the container element that holds the list items.
                                    container_element = WebDriverWait(browser, 10).until(
                                        EC.presence_of_element_located((By.CSS_SELECTOR, "ul.a-unordered-list.a-vertical.a-spacing-small"))
                                    )
                                    # Now find all the <li> elements within the container.
                                    description_elements = container_element.find_elements(By.CSS_SELECTOR, "li")

                                    if description_elements:
                                        for element in description_elements:
                                            browser.execute_script("arguments[0].scrollIntoView(true);", element)
                                            time.sleep(0.5)
                                            print(element.text)

                                except TimeoutException as e:
                                    print("Alternative selector elements not found either:", e)
                                    description_elements = []

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
                                            print("this is the numeric_value :", numeric_value)
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
                                # 🔹 Primary Selector: Find the product supplier element
                                product_supplier_element = product_page_html.find("a", {"id": "sellerProfileTriggerId"})

                                if not product_supplier_element:
                                    print("Primary selector not found, trying alternative selector...")

                                    try:
                                        # 🔹 Alternative Selector: Find using a different approach
                                        product_supplier_element = product_page_html.find("span", {"class": "tabular-buybox-text"})

                                    except Exception as e:
                                        print("Alternative selector failed:", e)
                                        product_supplier_element = None  # Ensure it's set to None if not found

                                # ✅ Extract text if an element is found
                                if product_supplier_element:
                                    product_supplier = product_supplier_element.get_text(strip=True)
                                    if product_supplier:
                                        print("product supplier found :", product_supplier)
                                        product_json_data["supplier"] = product_supplier

                            except Exception as e:
                                print("Error extracting product supplier:", e)
                            
                            # Extacting product images
                            try:
                                altImages = WebDriverWait(browser, 10).until(
                                    EC.element_to_be_clickable((By.ID, "altImages"))
                                )
                                if altImages:
                                    imgButtons = altImages.find_elements(By.CSS_SELECTOR, "li.imageThumbnail")
                                    for imgButton in imgButtons:
                                        time.sleep(1)
                                        imgButton.click()
                                        time.sleep(1)
                                        product_image_wrapper = WebDriverWait(browser, 10).until(
                                            EC.element_to_be_clickable((By.CSS_SELECTOR, "ul.a-unordered-list.a-nostyle.a-horizontal.list.maintain-height"))
                                        )
                                        if product_image_wrapper:
                                            product_image_list = product_image_wrapper.find_element(By.CSS_SELECTOR, "li.selected")
                                            if product_image_list:
                                                product_image = product_image_list.find_element(By.CSS_SELECTOR, "img.a-dynamic-image")
                                                if product_image:
                                                    product_json_data['images'].append(product_image.get_attribute('src'))
                                                    print(product_json_data['images'])
                            except Exception as e:
                                print("Error extracting product images")
                        
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