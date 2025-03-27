import re
import time
import json
import concurrent.futures
from urllib.parse import quote_plus
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Global scraping configurations
RETRIES = 2
SEARCH_PAGE = 1  # Adjust to desired number of pages
SEARCH_KEYWORD = "laptops"

# Setup main Selenium configurations (for search results)
main_options = webdriver.ChromeOptions()
main_options.add_argument("--headless")
main_options.add_argument("--disable-gpu")
main_options.add_argument("--ignore-certificate-errors")
main_options.add_argument("--log-level=3")
main_browser = webdriver.Chrome(options=main_options)
main_browser.set_window_size(1920, 1080)

def retry_extraction(func, attempts=2, delay=0.5, default=""):
    for i in range(attempts):
        try:
            result = func()
            if result:
                return result
        except Exception:
            time.sleep(delay)
    return default

def scrape_product_page(product_url):
    """
    Opens a new headless browser instance to scrape product details from a given product URL.
    Returns a dictionary with extra details (reviews, rating, supplier, images, videos, origin).
    """
    details = {}
    # Create a new WebDriver instance for this product page
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--log-level=3")
    driver = webdriver.Chrome(options=options)
    driver.set_window_size(1920, 1080)
    try:
        driver.get(product_url)
        WebDriverWait(driver, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")
        time.sleep(1)
        page_html = BeautifulSoup(driver.page_source, "html.parser")
        # Reviews
        try:
            review_elem = retry_extraction(lambda: page_html.find("span", {"id": "acrCustomerReviewText"}))
            if review_elem:
                review_text = review_elem.get_text(strip=True)
                m = re.search(r"(\d+)", review_text)
                if m:
                    details["review"] = m.group(1)
        except Exception as e:
            print("Error extracting reviews for", product_url, e)
        # Rating
        try:
            rating_elem = retry_extraction(
                lambda: page_html.find(
                    lambda tag: tag.name=="span" and tag.get("id")=="acrPopover" and
                                "reviewCountTextLinkedHistogram" in tag.get("class", []) and tag.has_attr("title")
                )
            )
            if rating_elem:
                inner_span = rating_elem.find("span", {"class": "a-size-base a-color-base"})
                if inner_span:
                    details["rating"] = inner_span.get_text(strip=True)
        except Exception as e:
            print("Error extracting rating for", product_url, e)
        # Supplier
        try:
            supp_elem = retry_extraction(lambda: page_html.find("a", {"id": "sellerProfileTriggerId"}))
            if supp_elem:
                details["supplier"] = supp_elem.get_text(strip=True)
        except Exception as e:
            print("Error extracting supplier for", product_url, e)
        # Images
        try:
            media_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "imgTagWrapperId")))
            if media_btn:
                media_btn.click()
                time.sleep(1)
            media_body = driver.find_element(By.CSS_SELECTOR, '[data-submodule="ProductImageThumbsList"]').get_attribute("outerHTML")
            media_soup = BeautifulSoup(media_body, "html.parser")
            image_elements = media_soup.select('[style*="background-image"]')
            img_urls = { re.search(r'url\("?(.*?)"?\)', el.get("style", "")).group(1)
                         for el in image_elements if re.search(r'url\("?(.*?)"?\)', el.get("style", "")) }
            details["images"] = [("https:" + url) if url.startswith("//") else url for url in img_urls]
        except Exception as e:
            print("Error extracting images for", product_url, e)
        # Videos
        try:
            video_urls = set()
            video_elements = driver.find_elements(By.TAG_NAME, "video")
            for v in video_elements:
                v_url = v.get_attribute("src")
                if v_url:
                    if "?" in v_url:
                        v_url = v_url.split('?')[0]
                    video_urls.add(v_url)
            details["videos"] = list(video_urls)
        except Exception as e:
            print("Error extracting videos for", product_url, e)
        # Origin
        try:
            attr_elem = driver.find_element(By.CLASS_NAME, "attribute-info").get_attribute("outerHTML")
            attr_soup = BeautifulSoup(attr_elem, "html.parser")
            for item in attr_soup.find_all("div", class_="attribute-item"):
                left_div = item.find("div", class_="left")
                if left_div and left_div.text.strip().lower() == "place of origin":
                    right_div = item.find("div", class_="right")
                    if right_div:
                        details["origin"] = right_div.text.strip()
                        break
        except Exception as e:
            print("Error extracting origin for", product_url, e)
    except Exception as e:
        print("Error processing product page", product_url, e)
    finally:
        driver.quit()
    return details

def scrape_amazon_products():
    scraped_products = {}
    product_list = []
    encoded_keyword = quote_plus(SEARCH_KEYWORD)
    search_url = f'https://www.amazon.in/s?k={encoded_keyword}&page=1&xpid=cmkUTDSjFdfFO'
    main_browser.get(search_url)
    WebDriverWait(main_browser, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")
    time.sleep(3)
    html_data = BeautifulSoup(main_browser.page_source, 'html.parser')
    product_cards_container = main_browser.find_element(By.XPATH, '//span[@data-component-type="s-search-results"]')
    product_cards_html = BeautifulSoup(product_cards_container.get_attribute("outerHTML"), "html.parser")
    product_cards = product_cards_html.find_all("div", {"role": "listitem"})
    for product in product_cards:
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
        try:
            product_link = retry_extraction(lambda: product.find("a", {"class": "a-link-normal s-line-clamp-2 s-link-style a-text-normal"})["href"])
            if product_link:
                if product_link.startswith("https://www.amazon.in"):
                    product_url = product_link
                else:
                    product_url = f"https://www.amazon.in{product_link}"
                product_json_data["url"] = product_url
        except Exception as e:
            print("Error extracting product url:", e)
        try:
            title_elem = retry_extraction(lambda: product.find("h2", {"class": "a-size-medium a-spacing-none a-color-base a-text-normal"}))
            if title_elem:
                product_json_data["title"] = title_elem.get_text(strip=True)
        except Exception as e:
            print("Error extracting product title:", e)
        if product_json_data["url"] == "":
            continue
        try:
            currency_elem = retry_extraction(lambda: product.find("span", {"class": "a-price-symbol"}))
            if currency_elem:
                product_json_data["currency"] = currency_elem.get_text(strip=True)
        except Exception as e:
            print("Error extracting product currency:", e)
        try:
            price_elem = retry_extraction(lambda: product.find("span", {"class": "a-price-whole"}))
            if price_elem:
                product_json_data["price"] = price_elem.get_text(strip=True)
        except Exception as e:
            print("Error extracting product price:", e)
        product_list.append(product_json_data)
        scraped_products[product_json_data["url"]] = product_json_data
    main_browser.quit()

    # Process product pages concurrently (max 10 parallel threads)
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_product = { executor.submit(scrape_product_page, prod["url"]): prod for prod in product_list if prod["url"] }
        for future in concurrent.futures.as_completed(future_to_product):
            prod = future_to_product[future]
            try:
                details = future.result()
                prod.update(details)
            except Exception as e:
                print("Error extracting product page details for", prod["url"], e)
    # Save scraped products
    with open("products.json", "w", encoding="utf-8") as f:
        json.dump(list(scraped_products.values()), f, ensure_ascii=False, indent=4)
    print("Scraping completed and saved to products.json")

if __name__ == '__main__':
    scrape_amazon_products()
