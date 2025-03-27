import re  
import time
import json
import os 
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
search_scrolls = 5  # (Not used directly here; scroll limits are defined later)
search_keyword = "nike"
facebook_username = "vishesh@brancosoft.com"
facebook_password = "Brancosoft@1234"

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
    options.add_argument("--disable-notifications")
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
    try : 
        marketplace_url = f"https://www.facebook.com/marketplace/delhi/search/?query={search_keyword}"
        browser.get(marketplace_url)
        WebDriverWait(browser, 10).until(lambda d : d.execute_script("return document.readyState") == "complete")
        print("✅ Succesfully navigated to marketplace")
        return True
       
        
    except Exception as e: 
        print("⚠️ Error in reaching to marketplace")
        return False
    
import time

def scrape_products(browser, search_scrolls): 
    """
    Scrolls down the page multiple times to load more products.
    
    Parameters:
    - browser (WebDriver): Selenium WebDriver instance.
    - search_scrolls (int): Number of times to scroll down.
    
    Returns:
    - None (Modifies the browser state)
    """
    try:
        all_products=[]
        try : 
            last_height = browser.execute_script("return document.body.scrollHeight")  # Get initial scroll height

            for _ in range(search_scrolls):  
                browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")  
                time.sleep(5)  

                new_height = browser.execute_script("return document.body.scrollHeight")  # Get new scroll height

                if new_height == last_height:  # Stop scrolling if no more content loads
                    print("✅ No more content to load. Stopping scrolling.")
                    break  

                last_height = new_height  # Update height for next loop
        except Exception as e : 
            print(" Error in scrolling", e)


        html_content = browser.page_source

        soup = BeautifulSoup(html_content, "html.parser")
        file_path = "parsed_page.html"
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(str(soup))

            print(f"HTML saved to {file_path}")

        products = WebDriverWait(browser, 5).until(
                            EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".x3ct3a4"))
                        )

        # products = soup.find_all(class_="x3ct3a4")
       
        print(f"✅ Retrieved {len(products)} products from the marketplace.")

        # Click every element

        try : 
            for product in products: 
                actions = ActionChains(browser)
        
                # Scroll to the product element
                actions.move_to_element(product).perform()
                
                # Wait for the element to be visible/interactive
                WebDriverWait(browser, 10).until(EC.element_to_be_clickable(product))  # Add a small delay to make sure the element is properly loaded
                
                # Click on the product
                product.click()
                print("Clicked on he product")

                time.sleep(5)
                print("Scrapping completed")



                browser.back()
        except Exception as e : 
            print("Error in clicking the product", e)






    
    except Exception as e: 
        print("⚠️ Error in getting the products :", e)



    



def scrape_facebook_data():
    """
    Main function to run the Facebook Marketplace scraper.
    Logs in, navigates to the Marketplace, scrolls to load products,
    then iterates through each product to open and close it while extracting data.
    """
    browser = selenium_config()
    success = facebook_login(browser)
    if not success:
        print("❌ Stopping scraper due to login failure.")
        browser.quit()
        return
    
    if not navigate_to_marketplace(browser, search_keyword):
        print("❌ Stopping scraper due to navigation failure.")
        browser.quit()
        return
    
    scrape_products(browser, search_scrolls)
    
    

    browser.quit()

# Run the scraper
scrape_facebook_data()
import re  
import time
import json
import os 
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
search_scrolls = 5  # (Not used directly here; scroll limits are defined later)
search_keyword = "nike"
facebook_username = "vishesh@brancosoft.com"
facebook_password = "Brancosoft@1234"

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
    options.add_argument("--disable-notifications")
    options.add_argument("--headless")  # Run in headless mode
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
    try : 
        marketplace_url = f"https://www.facebook.com/marketplace/delhi/search/?query={search_keyword}"
        browser.get(marketplace_url)
        WebDriverWait(browser, 10).until(lambda d : d.execute_script("return document.readyState") == "complete")
        print("✅ Succesfully navigated to marketplace")
        return True
       
        
    except Exception as e: 
        print("⚠️ Error in reaching to marketplace")
        return False
    
import time

def scrape_products(browser, search_scrolls): 
    """
    Scrolls down the page multiple times to load more products.
    
    Parameters:
    - browser (WebDriver): Selenium WebDriver instance.
    - search_scrolls (int): Number of times to scroll down.
    
    Returns:
    - None (Modifies the browser state)
    """
    try:
        all_products=[]
        try : 
            last_height = browser.execute_script("return document.body.scrollHeight")  # Get initial scroll height

            for _ in range(search_scrolls):  
                browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")  
                time.sleep(5)  

                new_height = browser.execute_script("return document.body.scrollHeight")  # Get new scroll height

                if new_height == last_height:  # Stop scrolling if no more content loads
                    print("✅ No more content to load. Stopping scrolling.")
                    break  

                last_height = new_height  # Update height for next loop
        except Exception as e : 
            print(" Error in scrolling", e)


        html_content = browser.page_source

        soup = BeautifulSoup(html_content, "html.parser")
        file_path = "parsed_page.html"
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(str(soup))

            print(f"HTML saved to {file_path}")

        products = WebDriverWait(browser, 5).until(
                            EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".x3ct3a4"))
                        )

        # products = soup.find_all(class_="x3ct3a4")
       
        print(f"✅ Retrieved {len(products)} products from the marketplace.")

        # Click every element

        try : 
            for product in products: 
                actions = ActionChains(browser)
        
                # Scroll to the product element
                actions.move_to_element(product).perform()
                
                # Wait for the element to be visible/interactive
                WebDriverWait(browser, 10).until(EC.element_to_be_clickable(product))  # Add a small delay to make sure the element is properly loaded
                
                # Click on the product
                product.click()
                print("Clicked on he product")

                time.sleep(5)
                print("Scrapping completed")



                browser.back()
        except Exception as e : 
            print("Error in clicking the product", e)






    
    except Exception as e: 
        print("⚠️ Error in getting the products :", e)



    



def scrape_facebook_data():
    """
    Main function to run the Facebook Marketplace scraper.
    Logs in, navigates to the Marketplace, scrolls to load products,
    then iterates through each product to open and close it while extracting data.
    """
    browser = selenium_config()
    success = facebook_login(browser)
    if not success:
        print("❌ Stopping scraper due to login failure.")
        browser.quit()
        return
    
    if not navigate_to_marketplace(browser, search_keyword):
        print("❌ Stopping scraper due to navigation failure.")
        browser.quit()
        return
    
    scrape_products(browser, search_scrolls)
    
    

    browser.quit()

# Run the scraper
scrape_facebook_data()