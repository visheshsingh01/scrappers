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
from selenium.webdriver.common.action_chains import ActionChains

# Enhanced anti-detection configurations
user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36"
]

chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument(f"user-agent={random.choice(user_agents)}")
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_argument("--disable-application-cache")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-setuid-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--ignore-certificate-errors")
chrome_options.add_argument("--log-level=3")
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option("useAutomationExtension", False)

# Initialize browser with stealth settings
browser = webdriver.Chrome(options=chrome_options)
browser.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": random.choice(user_agents)})
browser.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
browser.execute_script("delete navigator.__proto__.webdriver;")
browser.maximize_window()

# Original configurations
retries = 2
search_page = 20
search_keyword = "Christian Dior Perfume"
output_file = "products.json"
images_folder = "images"

os.makedirs(images_folder, exist_ok=True)

def initialize_json_file():
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("[\n")

def finalize_json_file():
    with open(output_file, "a", encoding="utf-8") as f:
        f.write("\n]")

def save_product(product_data, first_product=False):
    with open(output_file, "a", encoding="utf-8") as f:
        if not first_product:
            f.write(",\n")
        json.dump(product_data, f, ensure_ascii=False, indent=4)

def retry_extraction(func, attempts=1, delay=1, default=""):
    for _ in range(attempts):
        try:
            result = func()
            if result:
                return result
        except Exception:
            time.sleep(delay)
    return default

def download_image(image_url, product_url):
    try:
        parsed_url = urlparse(product_url)
        website = parsed_url.netloc.replace("www.", "") if parsed_url.netloc else "unknown"
        filename = f"{website}-{search_keyword.replace(' ', '_')}-{random.randint(100000, 999999)}{os.path.splitext(urlparse(image_url).path)[1] or '.jpg'}"
        
        response = requests.get(image_url, timeout=10)
        if response.status_code == 200:
            with open(os.path.join(images_folder, filename), "wb") as f:
                f.write(response.content)
            print(f"Downloaded: {filename}")
    except Exception as e:
        print(f"Download failed: {e}")

def kill_spinner():
    browser.execute_script("""
        const style = document.createElement('style');
        style.textContent = '.next-loading, .loading-spinner { display: none !important; }';
        document.head.appendChild(style);
    """)

def wait_for_page():
    WebDriverWait(browser, 30).until(
        EC.invisibility_of_element_located((By.CSS_SELECTOR, ".next-loading"))
    )
    WebDriverWait(browser, 45).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".fy23-search-card"))
    )

def human_like_scroll():
    for _ in range(random.randint(2, 4)):
        browser.execute_script(f"window.scrollBy(0, {random.randint(300, 600)})")
        time.sleep(random.uniform(0.8, 1.5))

def human_like_mouse():
    actions = ActionChains(browser)
    for _ in range(random.randint(1, 3)):
        actions.move_by_offset(random.randint(-50, 50), random.randint(-50, 50)).perform()
        time.sleep(random.uniform(0.3, 0.7))

def scrape_alibaba_products():
    initialize_json_file()
    scraped_urls = set()
    first_product = True

    for page in range(1, search_page + 1):
        for attempt in range(retries):
            try:
                search_url = f'https://www.alibaba.com/trade/search?fsb=y&IndexArea=product_en&keywords={search_keyword}&originKeywords={search_keyword}&tab=all&page={page}&spm=a2700.galleryofferlist.pagination.0'
                
                # Human-like navigation
                browser.get("about:blank")
                time.sleep(random.uniform(0.5, 1.2))
                browser.get(search_url)
                
                kill_spinner()
                wait_for_page()
                human_like_scroll()
                human_like_mouse()

                # CAPTCHA check
                if "captcha" in browser.current_url:
                    print("CAPTCHA detected! Exiting...")
                    browser.quit()
                    return

                product_cards = browser.find_elements(By.CLASS_NAME, 'fy23-search-card')
                
                for product_elem in product_cards:
                    product_data = {
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

                    product_soup = BeautifulSoup(product_elem.get_attribute('outerHTML'), 'html.parser')

                    # URL extraction
                    product_link = retry_extraction(
                        lambda: product_soup.select_one('.search-card-e-slider__link')['href']
                    )
                    if product_link:
                        product_url = product_link if product_link.startswith('http') else f"https:{product_link}"
                        product_data["url"] = product_url

                    # Skip duplicates
                    if product_data["url"] in scraped_urls:
                        continue

                    # Title extraction
                    product_data["title"] = retry_extraction(
                        lambda: product_soup.select_one('.search-card-e-title span').get_text(strip=True)
                    )

                    # Price and currency
                    price_element = retry_extraction(
                        lambda: product_soup.select_one('.search-card-e-price-main').get_text(strip=True)
                    )
                    if price_element:
                        currency = re.sub(r'[\d.,-]', '', price_element).strip()[:1]
                        product_data["currency"] = currency
                        product_data["price"] = price_element.replace(currency, '').strip()

                    # Min order
                    product_data["min_order"] = retry_extraction(
                        lambda: product_soup.select_one('.search-card-m-sale-features__item').get_text(strip=True, separator=' ').replace('Min. order:', '').strip()
                    )

                    # Supplier
                    product_data["supplier"] = retry_extraction(
                        lambda: product_soup.select_one('.search-card-e-company').get_text(strip=True)
                    )

                    # Feedback
                    feedback = product_soup.select_one('.search-card-e-review')
                    if feedback:
                        product_data["feedback"]["rating"] = feedback.strong.get_text(strip=True) if feedback.strong else ""
                        product_data["feedback"]["review"] = feedback.span.get_text(strip=True).split()[0] if feedback.span else ""

                    # Product details page
                    if product_data["url"]:
                        try:
                            browser.execute_script("window.open('');")
                            browser.switch_to.window(browser.window_handles[-1])
                            browser.get(product_data["url"])
                            
                            # Wait for product details
                            WebDriverWait(browser, 15).until(
                                EC.presence_of_element_located((By.CLASS_NAME, "attribute-info"))
                            )

                            # Extract origin
                            attribute_info = browser.find_element(By.CLASS_NAME, 'attribute-info').get_attribute('outerHTML')
                            attribute_soup = BeautifulSoup(attribute_info, 'html.parser')
                            for item in attribute_soup.select('.attribute-item'):
                                if item.select_one('.left').get_text(strip=True) == 'Place of Origin':
                                    product_data["origin"] = item.select_one('.right').get_text(strip=True)
                                    break

                            # Extract videos
                            video_urls = set()
                            for video in browser.find_elements(By.TAG_NAME, 'video'):
                                src = video.get_attribute('src')
                                if src:
                                    cleaned = src.split('?')[0].replace('blob:', '')
                                    video_urls.add(cleaned if cleaned.startswith('http') else f"https:{cleaned}")
                            product_data["videos"] = list(video_urls)

                        except Exception as e:
                            print(f"Product page error: {e}")
                        finally:
                            browser.close()
                            browser.switch_to.window(browser.window_handles[0])

                    # Save product
                    if product_data["url"]:
                        save_product(product_data, first_product)
                        scraped_urls.add(product_data["url"])
                        if first_product:
                            first_product = False

                break  # Success, exit retry loop

            except Exception as e:
                print(f"Page {page} attempt {attempt+1} failed: {e}")
                time.sleep(random.uniform(1.5, 3.5))

        else:
            print(f"Failed to scrape page {page} after {retries} attempts")

    finalize_json_file()
    browser.quit()
    print("Scraping completed")

if __name__ == "__main__":
    scrape_alibaba_products()