import re
import time
import json

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
                # Try multiple selectors since Flipkart may use different layouts
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
                    print(f"Found {len(product_cards)} products on page {page}")
                    for product_card in product_cards:
                        product_json_data = {
                            "url": "",
                            "title": "",
                            "currency": "",
                            "price": "",
                            "description": "",
                            "images": [],
                            # Extra details from the product page:
                            "details": "",
                            "rating": "",
                            "review": "",
                            "seller_info": "",
                            "color_info": "",
                            "manufacturer_info": "",
                            "in_the_box": "",
                            "bestseller_info": "",
                            "model_number": "",
                            "discount_info": "",
                            "MRP_info": "",
                            "price_after_discount": "",
                            "delivery_details": "",
                            "display_size": ""
                        }
                        # Extracting product url from the card
                        try:
                            product_url_tag = product_card.find_element(By.TAG_NAME, "a")
                            product_url = product_url_tag.get_attribute("href")
                            product_json_data["url"] = product_url
                        except Exception as e:
                            continue

                        # Open product in new tab and extract details
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
                                try:
                                    product_title_elem = browser.find_element(By.CSS_SELECTOR, "span.VU-ZEz")
                                    product_title = product_title_elem.text.strip()
                                    product_json_data["title"] = product_title
                                    print("Title:", product_title)
                                except Exception as e:
                                    pass

                                # Extracting product price and currency
                                try:
                                    product_price_currency_elem = browser.find_element(By.CSS_SELECTOR, "div.Nx9bqj.CxhGGd")
                                    product_price_currency = product_price_currency_elem.text.strip()
                                    product_price_currency_match = re.match(r'([^0-9]+)([0-9,]+)', product_price_currency)
                                    if product_price_currency_match:
                                        product_json_data["currency"] = product_price_currency_match.group(1)
                                        product_json_data["price"] = product_price_currency_match.group(2)
                                except Exception as e:
                                    pass

                                # Extracting product images
                                try:
                                    product_images_main_elem = browser.find_element(By.CSS_SELECTOR, "div.qOPjUY")
                                    imgButtons = product_images_main_elem.find_elements(By.CSS_SELECTOR, "li.YGoYIP")
                                    for imgButton in imgButtons:
                                        try:
                                            time.sleep(1)
                                            browser.execute_script("arguments[0].scrollIntoView(true);", imgButton)
                                            imgButton.click()
                                            time.sleep(1)
                                            try:
                                                product_image_wrapper = product_images_main_elem.find_element(By.CSS_SELECTOR, "div.vU5WPQ")
                                                product_image_elem = product_image_wrapper.find_element(By.TAG_NAME, "img")
                                                product_image = product_image_elem.get_attribute("src")
                                                product_json_data["images"].append(product_image)
                                            except Exception as img_err:
                                                continue
                                        except Exception as e:
                                            continue
                                except Exception as e:
                                    print("No product images element found.")

                                # Extracting product description
                                try:
                                    product_description_main_elem = browser.find_elements(By.CSS_SELECTOR, "div.pqHCzB")
                                    product_description = " ".join(
                                        elem.text.strip() for elem in product_description_main_elem if elem.text.strip()
                                    )
                                    product_json_data["description"] = product_description
                                except Exception as e:
                                    pass

                                # --- Additional details extraction ---
                                try:
                                    product_details_elem = browser.find_element(By.CLASS_NAME, "Xbd0Sd")
                                    product_json_data["details"] = product_details_elem.text.strip()
                                except Exception as e:
                                    product_json_data["details"] = ""
                                
                                try:
                                    product_rating_elem = browser.find_element(By.CLASS_NAME, "XQDdHH")
                                    product_json_data["rating"] = product_rating_elem.text.strip()
                                except Exception as e:
                                    product_json_data["rating"] = ""
                                
                                try:
                                    product_review_elem = browser.find_element(By.CLASS_NAME, "Wphh3N")
                                    product_json_data["review"] = product_review_elem.text.strip()
                                except Exception as e:
                                    product_json_data["review"] = ""
                                
                                try:
                                    seller_info_elem = browser.find_element(By.CLASS_NAME, "cvCpHS")
                                    product_json_data["seller_info"] = seller_info_elem.text.strip()
                                except Exception as e:
                                    product_json_data["seller_info"] = ""
                                
                                try:
                                    color_info_elem = browser.find_element(By.CLASS_NAME, "hSEbzK")
                                    product_json_data["color_info"] = color_info_elem.text.strip()
                                except Exception as e:
                                    product_json_data["color_info"] = ""
                                
                                try:
                                    manufacturer_info_elems = browser.find_elements(By.CSS_SELECTOR, "div.col.afKZtL li.H+ugqS")
                                    manufacturer_info = " | ".join([elem.text.strip() for elem in manufacturer_info_elems if elem.text.strip()])
                                    product_json_data["manufacturer_info"] = manufacturer_info
                                except Exception as e:
                                    product_json_data["manufacturer_info"] = ""
                                
                                try:
                                    inthebox_elem = browser.find_element(By.XPATH, "//tr[contains(@class, 'WJdYP6 row')]//li[contains(@class, 'HPETK2')]")
                                    product_json_data["in_the_box"] = inthebox_elem.text.strip()
                                except Exception as e:
                                    product_json_data["in_the_box"] = ""
                                
                                try:
                                    bestseller_elem = browser.find_element(By.CSS_SELECTOR, ".UzRoYO.CmflSf")
                                    product_json_data["bestseller_info"] = bestseller_elem.text.strip()
                                except Exception as e:
                                    product_json_data["bestseller_info"] = ""
                                
                                try:
                                    model_number_elem = browser.find_element(By.XPATH, "//tr[td[contains(., 'Model Number')]]//li[contains(@class, 'HPETK2')]")
                                    product_json_data["model_number"] = model_number_elem.text.strip()
                                except Exception as e:
                                    product_json_data["model_number"] = ""
                                
                                try:
                                    discount_elem = browser.find_element(By.CLASS_NAME, "UkUFwK")
                                    product_json_data["discount_info"] = discount_elem.text.strip()
                                except Exception as e:
                                    product_json_data["discount_info"] = ""
                                
                                try:
                                    mrp_elem = browser.find_element(By.CSS_SELECTOR, "div.yRaY8j.A6\\+E6v")
                                    product_json_data["MRP_info"] = mrp_elem.text.strip()
                                except Exception as e:
                                    product_json_data["MRP_info"] = ""
                                
                                try:
                                    afterdis_elem = browser.find_element(By.CSS_SELECTOR, ".Nx9bqj.CxhGGd")
                                    product_json_data["price_after_discount"] = afterdis_elem.text.strip()
                                except Exception as e:
                                    product_json_data["price_after_discount"] = ""
                                
                                try:
                                    delivery_elem = browser.find_element(By.CSS_SELECTOR, ".nRBH83")
                                    product_json_data["delivery_details"] = delivery_elem.text.strip()
                                except Exception as e:
                                    product_json_data["delivery_details"] = ""
                                
                                
                                # --- End additional details extraction ---
                                
                            except Exception as e:
                                print("Error processing product page:", e)
                            finally:
                                browser.close()
                                browser.switch_to.window(browser.window_handles[0])
                        # Save unique product by URL
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
retry_extraction(lambda: scrape_flipkart_products(browser))
browser.quit()
