import re  
import time
import json
import logging
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException

# Set up logging to file "error_log.txt" at ERROR level
logging.basicConfig(
    filename="error_log.txt",
    level=logging.ERROR,
    format='%(asctime)s %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Global scraping configurations
search_keyword = "caterpillar"
facebook_username = "diwakar.jha@brancosoft.com"
facebook_password = "Diwakar@1234;"

def selenium_config():
    """
    Setup Selenium with Chrome using specific options.
    - Ignores certificate errors.
    - Sets log level to suppress extra output.
    - Maximizes the browser window.
    """
    options = webdriver.ChromeOptions()
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--log-level=3")
    browser = webdriver.Chrome(options=options)
    browser.maximize_window()
    return browser

def facebook_login(browser):
    """
    Log into Facebook using the provided credentials.
    Waits for the page to load completely.
    """
    try:
        # Navigate to Facebook login page
        browser.get("https://www.facebook.com/")
        # Wait for page to fully load
        WebDriverWait(browser, 20).until(lambda d: d.execute_script("return document.readyState") == "complete")
        # Wait for and locate the email and password input fields
        username = WebDriverWait(browser, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[name='email']")))
        password = WebDriverWait(browser, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[name='pass']")))
        # Clear any pre-filled data and enter credentials
        username.clear()
        username.send_keys(facebook_username)
        password.clear()
        password.send_keys(facebook_password)
        # Click the login button
        WebDriverWait(browser, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))).click()
        # Wait for the page after login to load completely
        WebDriverWait(browser, 15).until(lambda d: d.execute_script("return document.readyState") == "complete")
        print("✅ Login successful!")
        time.sleep(20)  # Extra wait to allow manual captcha if necessary
        return True
    except Exception as e:
        print("❌ Login failed:", e)
        logging.error("Login failed: %s", e)
        return False

def navigate_to_marketplace(browser, search_keyword):
    """
    Navigate to the Facebook Marketplace URL based on the search keyword,
    wait for the marketplace items container to load,
    then call the scrape_items function to prepare for item processing.
    Returns the items container and the XPath expression for the product elements.
    """
    try:
        # Construct URL for Facebook Marketplace with the given search keyword
        marketplace_url = f"https://www.facebook.com/marketplace/delhi/search/?query={search_keyword.replace(' ', '%20')}"
        browser.get(marketplace_url)
        # Wait until the page is fully loaded
        WebDriverWait(browser, 15).until(lambda d: d.execute_script("return document.readyState") == "complete")
        print(f"🔍 Searching Marketplace for: {search_keyword}")
        time.sleep(5)
        # Wait for the Marketplace items container to appear
        items_container = WebDriverWait(browser, 15).until(
            EC.visibility_of_element_located((By.XPATH, "//div[@aria-label='Collection of Marketplace items']"))
        )
        # Prepare the items container and XPath expression without any scrolling logic
        return scrape_items(browser, items_container)
    except Exception as e:
        print("❌ Failed to navigate Marketplace:", e)
        logging.error("Navigate to Marketplace failed: %s", e)
        return None, None

def scrape_items(browser, items_container):
    """
    Constructs the XPath expression for identifying product elements
    and returns the items container along with that XPath.
    (Scrolling logic has been removed.)
    """
    try:
        # Define the complete unique product class list
        class_list = [
            'x9f619', 'x78zum5', 'x1r8uery', 'xdt5ytf', 'x1iyjqo2',
            'xs83m0k', 'x1e558r4', 'x150jy0e', 'x1iorvi4', 'xjkvuk6',
            'xnpuxes', 'x291uyu', 'x1uepa24'
        ]
        # Build an XPath that selects elements containing all these classes
        xpath_expression = ".//div[" + " and ".join([f"contains(@class, '{cls}')" for cls in class_list]) + "]"
        print("✅ Items container and XPath constructed.")
        return items_container, xpath_expression
    except Exception as e:
        print("❌ Error constructing XPath:", e)
        logging.error("Scrape items error: %s", e)
        return None, None

def open_and_close_products(browser, items_container, xpath_expression, scraped_products):
    """
    Iterate through each product element (located using the provided xpath_expression),
    find the clickable element by using the new unique class, click it to open the product detail page,
    wait for the detail page to load, extract data and store it in a predefined JSON structure,
    then close it by navigating back.
    The JSON structure is saved in the scraped_products list.
    """
    try:
        # Fetch all product elements using the provided xpath_expression.
        product_elements = items_container.find_elements(By.XPATH, xpath_expression)
        total_products = len(product_elements)
        print(f"✅ Preparing to process {total_products} products.")
        
        for index in range(total_products):
            try:
                # Re-fetch product elements to avoid stale references.
                product_elements = items_container.find_elements(By.XPATH, xpath_expression)
                if index >= len(product_elements):
                    print("Index out of range after refresh, breaking loop.")
                    break
                product = product_elements[index]
                
                # Find the clickable element using the new unique class.
                # The unique classes are: 
                # x9f619, x78zum5, x1iyjqo2, x5yr21d, x4p5aij, x19um543, x1j85h84, x1m6msm, x1n2onr6, xh8yej3
                # Using a CSS selector, the element must have all of these classes.
                try:
                    clickable_element = WebDriverWait(product, 10).until(
                        lambda d: product.find_element(By.CSS_SELECTOR, ".x9f619.x78zum5.x1iyjqo2.x5yr21d.x4p5aij.x19um543.x1j85h84.x1m6msm.x1n2onr6.xh8yej3")
                    )
                except Exception as e:
                    error_message = f"❌ Clickable element not found for product {index + 1}, skipping. Error: {e}"
                    print(error_message)
                    logging.error(error_message)
                    continue  # Skip this product if the clickable element is not found
                
                # Scroll the clickable element into view.
                browser.execute_script("arguments[0].scrollIntoView(true);", clickable_element)
                time.sleep(2)  # Wait to ensure the element is in view
                
                print(f"📌 Clicking product {index + 1}/{total_products}")
                # Click the element to open the product detail page.
                browser.execute_script("arguments[0].click();", clickable_element)
                
                # Wait for the product detail page to load by waiting for the <body> tag.
                WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                time.sleep(3)  # Extra wait to allow dynamic content to load
                
                # Extract product details from the detail page using BeautifulSoup.
                soup = BeautifulSoup(browser.page_source, "html.parser")
                title_element = soup.find("h1")
                title = title_element.text.strip() if title_element else "No title"
                price_element = soup.find("div", {"class": re.compile(r"^\$?\d+")})
                price = price_element.text.strip() if price_element else "No price"
                
                # Attempt to extract currency from price if available
                currency = ""
                if price != "No price" and price:
                    if price[0] in "₹$€£":
                        currency = price[0]
                
                # Create the predefined JSON structure for the product
                product_json_data = {
                    "url": browser.current_url,
                    "title": title,
                    "currency": currency,
                    "price": price,
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
                
                print(f"✅ Product {index + 1}: {title} - {price}")
                
                # Append the product data to scraped_products list
                scraped_products.append(product_json_data)
                
                # Close the product detail page by navigating back.
                browser.execute_script("window.history.go(-1)")
                time.sleep(5)  # Wait for the Marketplace page to reload
                
                # Re-wait for the items container on the Marketplace page.
                items_container = WebDriverWait(browser, 15).until(
                    EC.visibility_of_element_located((By.XPATH, "//div[@aria-label='Collection of Marketplace items']"))
                )
            except Exception as inner_e:
                error_message = f"❌ Error processing product {index + 1}: {inner_e}"
                print(error_message)
                logging.error(error_message)
    except Exception as e:
        error_message = f"❌ Failed to process products: {e}"
        print(error_message)
        logging.error(error_message)

def scrape_facebook_data():
    """
    Main function to run the Facebook Marketplace scraper.
    Logs in, navigates to the Marketplace, prepares the product elements,
    then iterates through each product to open and close it while extracting data.
    Saves the scraped data in a JSON file.
    """
    scraped_products = []  # List to store scraped product data
    browser = selenium_config()
    success = facebook_login(browser)
    if success:
        # Navigate to Marketplace and get the items container and XPath for products
        items_container, xpath_expression = navigate_to_marketplace(browser, search_keyword)
        if items_container and xpath_expression:
            # Process each product and store data in scraped_products
            open_and_close_products(browser, items_container, xpath_expression, scraped_products)
    # Save all scraped products to a JSON file
    with open("products.json", "w", encoding="utf-8") as f:
        json.dump(scraped_products, f, ensure_ascii=False, indent=4)
    print("Scraping completed and saved to products.json")
    browser.quit()

# Run the scraper
scrape_facebook_data()
