import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def setup_browser():
    """Set up Selenium Chrome WebDriver."""
    options = webdriver.ChromeOptions()
    # Uncomment the following line to run in headless mode:
    # options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

def search_flipkart(query):
    """Open Flipkart, close the login popup, and perform a search."""
    driver = setup_browser()
    driver.get("https://www.flipkart.com")

    # Close login popup if it appears
    try:
        close_popup = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'✕')]"))
        )
        close_popup.click()
        print("Closed popup.")
    except Exception as e:
        print("Popup not found or already closed.", e)

    # Locate the search box, enter the query, and submit
    try:
        search_box = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "q"))
        )
        search_box.clear()
        search_box.send_keys(query)
        search_box.send_keys(Keys.RETURN)
        print(f"Search performed for: {query}")
        time.sleep(2)  # Allow search results to load
    except Exception as e:
        print("Error during search:", e)
    
    return driver

def scrape_products(driver):
    """Scrape product elements after performing a search."""
    # Additional wait to ensure all results are loaded
    WebDriverWait(driver, 10).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )
    
    # Store the handle for the original window
    original_window = driver.current_window_handle
    
    try:
        product_elements = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.tUxRFH a"))
        )
        if product_elements:
            print(f"This is the length of the product elements: {len(product_elements)}")

            for product in product_elements:
                try:
                    product.click()
                    time.sleep(3)
                    WebDriverWait(driver, 10).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )
                    WebDriverWait(driver, 10).until(lambda d: len(d.window_handles) > 1)
                    
                    # Switch to the new window
                    new_window = [handle for handle in driver.window_handles if handle != original_window][0]
                    driver.switch_to.window(new_window)
                    print("Switched to new window.")
                    time.sleep(5)
                    
                    # (Process the new window if needed)
                    # For example, scrape additional details here.

                    try:

                        product_element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "span.VU-ZEz")))
                        product_text = product_element.text
                        print(product_text)



                    

                    except Exception as e : 
                        print("Product name could not be found")
                    try : 
                        image_div = WebDriverWait(driver, 10).until(EC.visibility_of_element_located(((By.CSS_SELECTOR, "div.j9BzIm"))))
                        image_elements = image_div.find_elements(By.CSS_SELECTOR, "li.YGoYIP.Ueh1GZ")
                        if image_elements :
                         print(f"this is the length of the all the li tag {len(image_elements)}")
                         for img in image_elements: 
                             driver.execute_script("arguments[0].click();", img)

                             time.sleep(1)
                             img.click()
                             time.sleep(1)
                             try : 
                                product_image_element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div._4WELSP._6lpKCl img")))
                                driver.execute_script("arguments[0].scrollIntoView(true);", product_image_element)
                                time.sleep(1)
                                product_image_source = product_image_element.get_attribute("src")
                                print("image source is this :", product_image_source)
                             except Exception as e : 
                                 print("Product image not found :",e)
                            


                        else : 
                            print("no li tag found")
                    except Exception as e : 
                        print("No div or element found",e)
                        


                    
                    # Close the new window and switch back
                    driver.close()
                    print("Closed new window.")
                    driver.switch_to.window(original_window)
                    print("Switched back to original window.")
                    time.sleep(2)
                except Exception as e:
                    print("Error processing a product:", e)
        else:
            print("No product elements found.")
    except Exception as e:
        print("Error finding product elements:", e)

def main():
    query = "laptop"  # Change this to any search term
    driver = search_flipkart(query)
    scrape_products(driver)
    driver.quit()

if __name__ == "__main__":
    main()
