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
facebook_username = "yagya.suri@brancosoft.com"
facebook_password = "brancosoft@12345"


def selenium_config():
    """
    Setup Selenium with Chrome using specific options.
    """
    options = webdriver.ChromeOptions()
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--log-level=3")
    options.add_argument("--disable-notifications")
    # Uncomment if you want to run headless:
    # options.add_argument("--headless")
    browser = webdriver.Chrome(options=options)
    browser.maximize_window()
    return browser

def facebook_login(browser):
    """
    Log into Facebook using the provided credentials.
    """
    try:
        browser.get("https://www.facebook.com/")
        # Wait for page to load fully using document.readyState
        WebDriverWait(browser, 20).until(lambda d: d.execute_script("return document.readyState") == "complete")
        # Locate email and password fields
        username = WebDriverWait(browser, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "input[name='email']"))
        )
        password = WebDriverWait(browser, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "input[name='pass']"))
        )
        username.clear()
        username.send_keys(facebook_username)
        password.clear()
        password.send_keys(facebook_password)
        # Click the login button
        WebDriverWait(browser, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))
        ).click()
        # Wait for post-login page to load completely
        WebDriverWait(browser, 15).until(lambda d: d.execute_script("return document.readyState") == "complete")
        print("✅ Login successful!")
        # Extra wait for any additional verifications (e.g., captcha)
        time.sleep(10)
        return True
    except Exception as e:
        print("❌ Login failed:", e)
        logging.error("Login failed: %s", e)
        return False

def navigate_to_profile(browser, username):
    """
    Navigate to the specified user profile page.
    """
    try:
        # Construct search URL – adjust accordingly if you want to search profiles
        profile_url = f"https://www.facebook.com/search/top/?q={username.replace(' ', '%20')}"
        browser.get(profile_url)
        WebDriverWait(browser, 10).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        print("✅ Successfully navigated to profile search results.")
        return True
    except Exception as e:
        print("⚠️ Error in reaching the profile page:", e)
        logging.error("Error navigating to profile: %s", e)
        return False

def scrape_individual_profile(browser):
    """
    Scrapes individual profile information from an open profile tab.
    Customize this function to extract the desired data.
    """
    try:
        # Example: Extract profile name
        profile_name_element = WebDriverWait(browser, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "div.x78zum5.xdt5ytf.x1wsgfga.x9otpla"))
        )
        profile_name = profile_name_element.text
        print("✅ Profile Name:", profile_name)
    except Exception as e:
        print("⚠️ Error finding profile name:", e)

    try:
        # Example: Extract profile image URL if present
        profile_img_container = WebDriverWait(browser, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "div.x1jx94hy.x14yjl9h.xudhj91.x18nykt9.xww2gxu.x1iorvi4.x150jy0e.xjkvuk6.x1e558r4"))
        )
        profile_img = profile_img_container.find_element(By.CSS_SELECTOR, "image")
        browser.execute_script("arguments[0].scrollIntoView({ behavior: 'smooth', block: 'center' });", profile_img)
        profile_img_url = profile_img.get_attribute("xlink:href")
        print("✅ Profile Image URL:", profile_img_url)
    except Exception as e:
        print("⚠️ Error finding profile image:", e)

    try:
        # Example: Extract intro text
        intro_element = WebDriverWait(browser, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "div.x2b8uid.x80vd3b.x1q0q8m5.xso031l.x1l90r2v span"))
        )
        intro_text = intro_element.text
        print("✅ Intro Text:", intro_text)
    except Exception as e:
        print("⚠️ Error finding intro element:", e)

    # Add more scraping logic as needed...

    # Example: Extracting about texts 

    try : 
        try :
            tabs = WebDriverWait(browser, 10).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "div.x9f619.x1ja2u2z.x78zum5.x1n2onr6.xl56j7k.x1qjc9v5.xozqiw3.x1q0g3np.x1ve1bff.xvo6coq.x2lah0s")))
            if tabs: 
                print("✅ Tabs found.")
            about_tab = tabs.find_element(By.XPATH, ".//span[contains(text(), 'About')]")
            browser.execute_script("arguments[0].scrollIntoView();", about_tab)
            browser.execute_script("arguments[0].click();", about_tab)
            print("✅About tab clicked.")
            WebDriverWait(browser, 15).until(lambda d: d.execute_script("return document.readyState") == "complete")
            time.sleep(3)

        except Exception as e : 
            print( "⚠️ Error clicking 'About' tab:", e)

        try : 
            about_text_element = WebDriverWait(browser, 10).until(EC.visibility_of_all_elements_located((By.CSS_SELECTOR, "div.xyamay9.xqmdsaz.x1gan7if.x1swvt13 span")))
            about_text = [text.text for text in about_text_element if text.text]
            print("✅ About Text:", about_text)
        except Exception as e :
            print("⚠️ Error finding about text:", e)
            

    except Exception as e : 
        print("⚠️ Error getting about text:", e)


def scrape_profile_data(browser, search_scrolls=2):
    """
    Scrapes profiles from the search result page.
    Opens each profile in a new tab, scrapes data, then closes the tab.
    """
    # Click on the "People" section (if present)
    try:
        side_bar_element = WebDriverWait(browser, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.x1n2onr6.x1ja2u2z.x9f619.x78zum5.xdt5ytf.x2lah0s.x193iq5w.xx6bls6.x1jx94hy"))
        )
        people_section = side_bar_element.find_element(By.XPATH, "//span[contains(text(), 'People')]")
        browser.execute_script("arguments[0].scrollIntoView();", people_section)
        people_section.click()
    except Exception as e:
        print("⚠️ Error clicking 'People' section:", e)

    # Scroll to load more profiles (if needed)
    try:
        last_height = browser.execute_script("return document.body.scrollHeight")
        for _ in range(search_scrolls):
            browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(5)
            new_height = browser.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                print("✅ No more content to load. Stopping scrolling.")
                break
            last_height = new_height
    except Exception as e:
        print("⚠️ Error in scrolling:", e)

    # Get the list of profiles in the search results
    try:
        profiles = WebDriverWait(browser, 10).until(
            EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "div.x9f619.x1n2onr6.x1ja2u2z.xdt5ytf.x193iq5w.xeuugli.x1r8uery.x1iyjqo2.xs83m0k.x78zum5.x1t2pt76 div.x1n2onr6.x1ja2u2z.x1jx94hy.x1qpq9i9.xdney7k.xu5ydu1.xt3gfkd.x9f619.xh8yej3.x6ikm8r.x10wlt62.xquyuld")
            )
        )
        print(f"Profiles found: {len(profiles)}")
    except Exception as e:
        print("⚠️ Error finding profile elements:", e)
        return

    # Save the current window handle (original tab)
    original_window = browser.current_window_handle

    # Iterate over each profile element
    for profile in profiles:
        try:
            profile_link = profile.find_element(By.CSS_SELECTOR, "span.xjp7ctv a")
            profile_link_url = profile_link.get_attribute("href")
            print("Profile Link URL:", profile_link_url)
            # Scroll into view of the link
            browser.execute_script("arguments[0].scrollIntoView();", profile_link)

            # Open profile in a new tab
            browser.execute_script("window.open(arguments[0], '_blank');", profile_link_url)
            time.sleep(3)

            # Switch to the new tab
            new_window = [handle for handle in browser.window_handles if handle != original_window][0]
            browser.switch_to.window(new_window)
            WebDriverWait(browser, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")
            time.sleep(3)  # Extra wait for page elements to load

            # Scrape the data from the profile in the new tab
            scrape_individual_profile(browser)

        except Exception as e:
            print("Error in clicking or scraping the profile:", e)
            logging.error("Error processing profile %s", e)
        finally:
            # Close the current profile tab and switch back to the original tab
            if len(browser.window_handles) > 1:
                browser.close()
            browser.switch_to.window(original_window)
            time.sleep(3)


def scrape_facebook_profile():
    """
    Main function to run the Facebook profile scraper.
    Logs in, navigates to the specified profile search page, and executes the scraping logic.
    """
    browser = selenium_config()
    success = facebook_login(browser)
    if not success:
        print("❌ Stopping scraper due to login failure.")
        browser.quit()
        return

    username = input("Enter the Facebook username or profile link: ").strip()
    if not navigate_to_profile(browser, username):
        print("❌ Stopping scraper due to profile navigation failure.")
        browser.quit()
        return

    # Once at the profile search page, perform the scraping logic to iterate through found profiles
    scrape_profile_data(browser)
    browser.quit()


# Run the profile scraper
scrape_facebook_profile()
