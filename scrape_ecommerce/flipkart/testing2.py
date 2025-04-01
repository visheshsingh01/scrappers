from selenium import webdriver
from selenium.webdriver.common.by import By
import time
import json

# Start WebDriver
driver = webdriver.Chrome()

# Search query
query = "iphone"

# Data storage list
products = []
page_num = 1  # Start page

driver.get(f"https://www.flipkart.com/search?q={query}&page={page_num}")

# Wait for products to load
time.sleep(5)  # Can be replaced with WebDriverWait

try:
    # Get all product containers
    product_cards = driver.find_elements(By.CLASS_NAME, "tUxRFH")
    print(f"\n🔹 Found {len(product_cards)} items on page {page_num}\n")

    for index, product in enumerate(product_cards):
        try:
            # Extract product name
            name = product.find_element(By.CLASS_NAME, "KzDlHZ").text if product.find_elements(
                By.CLASS_NAME, "KzDlHZ") else "N/A"

            # Extract price
            price = product.find_element(By.CLASS_NAME, "hl05eU").text if product.find_elements(
                By.CLASS_NAME, "hl05eU") else "N/A"

            # Extract product link
            link_element = product.find_element(
                By.TAG_NAME, "a") if product.find_elements(By.TAG_NAME, "a") else None
            link = "https://www.flipkart.com" + \
                link_element.get_attribute("href") if link_element else "N/A"

            # Click on the product (new tab)
            if link_element:
                driver.execute_script("arguments[0].click();", link_element)
                time.sleep(3)  # Wait for new page to load
                driver.switch_to.window(driver.window_handles[1])

                # Extract product details
                product_details = driver.find_element(
                    By.CLASS_NAME, "Xbd0Sd").text if driver.find_elements(By.CLASS_NAME, "Xbd0Sd") else "N/A"

                # Extract product rating
                product_rating = driver.find_element(
                    By.CLASS_NAME, "XQDdHH").text if driver.find_elements(By.CLASS_NAME, "XQDdHH") else "N/A"

                # Extract product reviews
                product_review = driver.find_element(
                    By.CLASS_NAME, "Wphh3N").text if driver.find_elements(By.CLASS_NAME, "Wphh3N") else "N/A"

                # Extract seller info
                seller_info = driver.find_element(By.CLASS_NAME, "cvCpHS").text if driver.find_elements(
                    By.CLASS_NAME, "cvCpHS") else "N/A"

                # Extract color variants
                color_info = driver.find_element(By.CLASS_NAME, "hSEbzK").text if driver.find_elements(
                    By.CLASS_NAME, "hSEbzK") else "N/A"

                # Extract manufacturer info (Using CSS Selector)
                try:
                    manufacturer_info = driver.find_elements(
                        By.CSS_SELECTOR, "div.col.afKZtL li.H+ugqS")
                except:
                    manufacturer_info = "N/A"
               

                # Extract net weight
                try:
                    inthebox_info = driver.find_element(
                        By.XPATH, "//tr[contains(@class, 'WJdYP6 row')]//li[contains(@class, 'HPETK2')]").text
                except:
                    inthebox_info = "N/A"

                # extract best seller
                try:
                    bestseller_info = driver.find_element(By.CSS_SELECTOR, ".UzRoYO.CmflSf").text
                except:
                    bestseller_info = "N/A"

                # extract model number
                try:
                    model_number = driver.find_element(By.XPATH,"//tr[td[contains(., 'Model Number')]]//li[contains(@class, 'HPETK2')]").text
                    print("Model Number:", model_number)
                except Exception as e:
                    print("Error extracting model number:", e)
                    
                #discount percentage
                try:
                    discount_info=driver.find_element(By.CLASS_NAME, "UkUFwK").text
                except:
                    discount_info="N/A"
                
                     
                #MRP info
                try:
                    mrp_info=driver.find_element(By.CSS_SELECTOR,"div.yRaY8j.A6\\+E6v").text
                except:
                    mrp_info="N/A"
                    
                #Price after discount
                try:
                    afterdis_info=driver.find_element(By.CSS_SELECTOR, ".Nx9bqj.CxhGGd").text
                except:
                    afterdis_info="N/A"
                    
                #delivery details
                try:
                    deliv_info=driver.find_element(By.CSS_SELECTOR, ".nRBH83").text
                except:
                    deliv_info="N/A"
                #extract display size
                try:
                     display_size = driver.find_element(By.XPATH,"//tr[td[contains(text(), 'Display Size')]]//li[contains(@class, 'HPETK2')]").text
                     print("Display Size:", display_size)
                except Exception as e:
                     print("Error extracting display size:", e)
                     
                   
                     
                     
                     # Close the new tab and switch back
                driver.close()
                driver.switch_to.window(driver.window_handles[0])

            # Store product data
            product_data = {
                "Product Number": index + 1,
                "Product Name": name,
                "Price": price,
                "Link": link,
                "Details": product_details,
                "Rating": product_rating,
                "Review": product_review,
                "Seller Info": seller_info,
                "Color Info": color_info,
                "Manufacturer Info": manufacturer_info,
                "In the box": inthebox_info,
                "bestseller_info": bestseller_info,
                "modelno info": model_number,
                "discount info": discount_info,
                "MRP info": mrp_info,
                "Price after discount": afterdis_info,
                "Delivery details": deliv_info,
                "Display Size": display_size,
                }
            products.append(product_data)

            print(
                f"✅ Product {index + 1}: {name} | Price: {price} | Link: {link} | MRP info:{mrp_info}")

        except Exception as e:
            print(f"❌ Error extracting product {index + 1}: {e}")

except Exception as e:
    print(f"❌ Error loading page {page_num}: {e}")

# Save data to JSON file
json_filename = "flipkart_iphone_data.json"
with open(json_filename, "w", encoding="utf-8") as json_file:
    json.dump(products, json_file, ensure_ascii=False, indent=4)

# Close browser
time.sleep(5)
driver.quit()

print("\n✅ Data saved successfully to 'flipkart_iphone_data.json'")


# by.csss selector, "div.row Jd3sum li.H+ugqS"
