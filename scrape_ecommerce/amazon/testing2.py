import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

# Setup Selenium configurations
options = webdriver.ChromeOptions()
options.add_argument("--ignore-certificate-errors")
options.add_argument("--log-level=3")
# options.add_argument("--headless=new")  # Uncomment to run headless
browser = webdriver.Chrome(options=options)
browser.maximize_window()

# Configurable parameters
search_keyword = "laptops"
max_pages = 1  # Number of pages to navigate

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

            # Find all product links
            product_elements = browser.find_elements(By.XPATH, '//a[contains(@class, "a-link-normal s-no-outline")]')
            product_links = [elem.get_attribute("href") for elem in product_elements if elem.get_attribute("href")]

            if not product_links:
                print(f"No products found on page {page}. Moving to next page.")
                continue

            print(f"Found {len(product_links)} products on page {page}.")

            for product_url in product_links:
                try:
                    print(f"Navigating to product: {product_url}")
                    browser.get(product_url)
                    
                    # Wait for product page to load
                    WebDriverWait(browser, 10).until(
                        EC.presence_of_element_located((By.ID, "productTitle"))
                    )
                    
                    # Wait for all description elements to be present
                    description_elements = WebDriverWait(browser, 10).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#feature-bullets li.a-spacing-mini"))
                    )
                    
                    # Iterate over each element in the list and print its text
                    for element in description_elements:
                        browser.execute_script("arguments[0].scrollIntoView(true);", element)
                        print(element.text)

                    # Locate the detail container and save its HTML with BeautifulSoup
                    detail_container = WebDriverWait(browser, 10).until(
                        EC.visibility_of_element_located((By.ID, "detailBullets_feature_div"))
                    )
                    html_content = detail_container.get_attribute('outerHTML')
                    soup = BeautifulSoup(html_content, 'html.parser')
                    with open('detail_container.html', 'w', encoding='utf-8') as file:
                        file.write(soup.prettify())
                    print("The HTML content has been saved to detail_container.html")
                    
                    # Return to search results
                    browser.back()
                except Exception as e:
                    print(f"Error processing product {product_url}: {e}")

        except Exception as e:
            print(f"Error on page {page}: {e}")

    print("Navigation completed.")
    browser.quit()

navigate_amazon_pages()
