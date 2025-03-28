import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Setup Selenium configurations
options = webdriver.ChromeOptions()
options.add_argument("--ignore-certificate-errors")
options.add_argument("--log-level=3")
# options.add_argument("--headless=new")  # Uncomment to run headless
browser = webdriver.Chrome(options=options)
browser.maximize_window()

# Configurable parameters
search_keyword = "laptops"
max_pages = 2  # Number of pages to navigate

def navigate_amazon_pages():
    """Navigates Amazon search pages and clicks each product one by one."""
    for page in range(1, max_pages + 1):
        try:
            search_url = f'https://www.amazon.in/s?k={search_keyword}&page={page}'
            browser.get(search_url)

            # Wait until results are loaded
            WebDriverWait(browser, 10).until(
                EC.presence_of_element_located((By.XPATH, '//span[@data-component-type="s-search-results"]'))
            )
            time.sleep(2)

            # Find all product links
            product_elements = browser.find_elements(By.XPATH, '//a[contains(@class, "a-link-normal s-no-outline")]')
            product_links = [elem.get_attribute("href") for elem in product_elements if elem.get_attribute("href")]

            if not product_links:
                print(f"No products found on page {page}. Moving to next page.")
                continue

            print(f"Found {len(product_links)} products on page {page}.")

            for product_url in product_links:
                try:
                    print(f"Clicking product: {product_url}")
                    browser.get(product_url)
                    
                    # Wait for product page to load
                    WebDriverWait(browser, 10).until(
                        lambda d: d.execute_script("return document.readyState") == "complete"
                    )
                    time.sleep(3)
                    
                    # Wait for all description elements to be present
                    description_elements = WebDriverWait(browser, 10).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#feature-bullets li.a-spacing-mini"))
                    )
                    
                    # Iterate over each element in the list and print its text
                    for element in description_elements: 
                        browser.execute_script("arguments[0].scrollIntoView(true);", element)
                        time.sleep(2)
                        print(element.text)


                    try:
                        # Wait for the detail container with the given ID.
                        detail_divs = WebDriverWait(browser, 10).until(
                            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div#detailBullets_feature_div"))
                        )
                        
                        if detail_divs:
                            detail_div = detail_divs[0]
                            # Find all <li> tags within the detail container.
                            li_elements = detail_div.find_elements(By.CSS_SELECTOR, "li")
                            
                            for li in li_elements:
                                if "ASIN" in li.text:
                                    # Scroll the matching <li> element into view.
                                    browser.execute_script("arguments[0].scrollIntoView(true);", li)
                                    asin_text = li.text
                                    print("ASIN label text:", asin_text)
                                    break
                        else:
                            print("Detail container not found.")
                            
                    except Exception as e:
                        print("Not found the ASIN number:", e)
                    




                    # Return to search results
                    browser.back()
                    time.sleep(2)
                except Exception as e:
                    print(f"Error opening product {product_url}: {e}")

        except Exception as e:
            print(f"Error on page {page}: {e}")

    print("Navigation completed.")
    browser.quit()

navigate_amazon_pages()
