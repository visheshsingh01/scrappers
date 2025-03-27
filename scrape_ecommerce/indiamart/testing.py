import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

# Selenium WebDriver setup
options = webdriver.ChromeOptions()
options.add_argument("--ignore-certificate-errors")
options.add_argument("--log-level=3")
# options.add_argument("--headless")  # Uncomment for headless mode
browser = webdriver.Chrome(options=options)

# Scraping configuration
search_keyword = "laptop"
max_pages = 1  # Number of pages to scrape
retries = 3    # Retry count

def scrape_indiamart_products():
    scraped_data = []
    
    for page in range(1, max_pages + 1):
        url = f"https://dir.indiamart.com/search.mp?ss={search_keyword}&page={page}"
        print(f"Scraping page: {url}")
        
        for attempt in range(retries):
            try:
                browser.get(url)
                WebDriverWait(browser, 10).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
                
                # Scroll until all products are loaded
                previous_product_count = 0
                max_scroll_attempts = 10
                scroll_attempts = 0
                while scroll_attempts < max_scroll_attempts:
                    soup = BeautifulSoup(browser.page_source, "html.parser")
                    products = soup.find_all("div", {"class": "card"})
                    if len(products) > previous_product_count:
                        previous_product_count = len(products)
                        browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(2)
                        scroll_attempts += 1
                    else:
                        break
                print(f"Final product count: {previous_product_count}")
                
                # Retrieve the Selenium WebElements for the product cards
                cards = browser.find_elements(By.CSS_SELECTOR, "div.card")
                
                for card_elem in cards:
                    product_json_data = {
                        "url": "",
                        "title": "",
                        "currency": "",
                        "price": "",
                        "min_order": "",
                        "origin": "",
                        "feedback": {"rating": "", "review": ""},
                        "supplier": {"name": "", "status": ""},
                        "images": [],
                        "videos": []
                    }
                    
                    # Get HTML of the card for parsing
                    card_html = card_elem.get_attribute("outerHTML")
                    card_soup = BeautifulSoup(card_html, "html.parser")
                    
                    # Extract product name
                    prod_name = card_soup.find("div", {"class": "producttitle"})
                    if prod_name:
                        product_json_data["title"] = prod_name.get_text(strip=True)
                    
                    # Extract product URL
                    prod_url_el = card_soup.find("div", {"class": "titleAskPriceImageNavigation"})
                    if prod_url_el:
                        a_tag = prod_url_el.find("a")
                        if a_tag and a_tag.has_attr("href"):
                            product_json_data["url"] = a_tag["href"]
                    
                    # Extract price & currency
                    try:
                        price_el = card_soup.find("p", {"class": "price"})
                        if price_el:
                            raw_price = price_el.get_text(strip=True)
                            if "Ask Price" in raw_price:
                                product_json_data["price"] = "Ask Price"
                                product_json_data["currency"] = None
                            else:
                                currency_symbol = raw_price[0] if (raw_price[0].isalpha() or raw_price[0] in "₹$€¥£") else None
                                product_json_data["currency"] = currency_symbol
                                price_values = ["".join(filter(str.isdigit, p)) for p in raw_price.split("-") if any(char.isdigit() for char in p)]
                                if len(price_values) == 2:
                                    product_json_data["price"] = f"{price_values[0]}-{price_values[1]}"
                                elif len(price_values) == 1:
                                    product_json_data["price"] = price_values[0]
                                else:
                                    product_json_data["price"] = "Unknown"
                    except Exception as e:
                        print("Error extracting price:", e)
                    
                    # Extract min order quantity
                    try:
                        min_order_el = card_soup.find("span", {"class": "unit"})
                        if min_order_el:
                            text = min_order_el.get_text(strip=True)
                            qty = "".join(filter(str.isdigit, text))
                            unit = "".join(filter(str.isalpha, text))
                            if not qty and "Piece" in text:
                                qty = "1"
                            product_json_data["min_order"] = f"{qty} {unit}".strip()
                        else:
                            product_json_data["min_order"] = "Not specified"
                    except Exception as e:
                        print("Error extracting min order:", e)
                    
                    # Extract supplier details
                    try:
                        supp_el = card_soup.find("div", {"class": "companyname"})
                        if supp_el:
                            a_tag = supp_el.find("a", {"class": "cardlinks"})
                            if a_tag:
                                product_json_data["supplier"]["name"] = a_tag.get_text(strip=True)
                            p_tag = supp_el.find("p", {"class": "dib"})
                            if p_tag and p_tag.has_attr("data-click"):
                                product_json_data["supplier"]["status"] = p_tag["data-click"].strip()
                    except Exception as e:
                        print("Error extracting supplier:", e)
                    
                    # --- Extract slider images ---
                    try:
                        # Find and click the image container to open the slider popup.
                        # The selector below targets the image container div that triggers the slider.
                        img_container = card_elem.find_element(By.CSS_SELECTOR, "div.imgcontainer[data-click='^Prod0Img']")
                        img_container.click()
                        time.sleep(3)  # Wait for the slider popup to fully load

                        # Wait for the slider container (which holds the images) to appear.
                        slider_container = WebDriverWait(browser, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "div.imgslide"))
                        )
                        slider_html = slider_container.get_attribute("innerHTML")
                        slider_soup = BeautifulSoup(slider_html, "html.parser")
                        slider_imgs = slider_soup.find_all("img")
                        image_urls = [img.get("src") for img in slider_imgs if img.get("src")]
                        product_json_data["images"] = image_urls

                        # Optionally, close the slider popup if a close button is available.
                        # Close the slider popup using the provided close button (with class "be-cls")
                        try:
                            close_button = WebDriverWait(browser, 10).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, "div.be-cls"))
                            )
                            close_button.click()
                            time.sleep(1)
                        except Exception as ce:
                            print("No close button found or error closing slider:", ce)
                    except Exception as e:
                        print("Error extracting slider images:", e)
                        product_json_data["images"] = []
                    
                    # Append product data
                    scraped_data.append(product_json_data)
                
                break  # Exit retry loop if successful
            except Exception as e:
                print(f"Attempt {attempt+1}/{retries} failed: {e}")
                time.sleep(2)
                
    browser.quit()
    with open("indiamart_products.json", "w", encoding="utf-8") as f:
        json.dump(scraped_data, f, ensure_ascii=False, indent=4)
    print("\n✅ Scraping complete! Data saved to 'indiamart_products.json'.")

scrape_indiamart_products()