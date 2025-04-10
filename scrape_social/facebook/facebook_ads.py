import time
import logging
import urllib.parse
import json
from flask import Flask, request, render_template_string, jsonify
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.keys import Keys

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class FacebookAdsScraper:
    def __init__(self, keyword: str, country: str = "IN"):
        self.keyword = keyword
        self.country = country
        self.url = self.get_ads_url()
        self.browser = None
        self.ads_data = []  # Structured object to store JSON data for each ad

    def setup_driver(self):
        options = webdriver.ChromeOptions()
        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--log-level=3")
        options.add_argument("--disable-notifications")
        options.add_argument("--start-maximized")
        self.browser = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=options
        )
        return self.browser

    def get_ads_url(self):
        encoded_keyword = urllib.parse.quote(self.keyword)
        url = (
            f"https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country={self.country}"
            f"&is_targeted_country=false&media_type=all&q={encoded_keyword}&search_type=keyword_unordered"
        )
        logging.info("Generated URL: %s", url)
        return url

    def scroll_page(self, scrolls=10):
        """Scroll to load more ads; uses scroll height comparison and explicit waits."""
        last_height = self.browser.execute_script("return document.body.scrollHeight")
        for i in range(scrolls):
            self.browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(10)  # reduced wait time; adjust as needed
            new_height = self.browser.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                logging.info("✅ No more content to load on scroll %s.", i)
                break
            last_height = new_height

    def extract_ads(self):
        """Extract ad details while handling delays and retrying close button clicks."""
        try:
            # Wait for page load
            WebDriverWait(self.browser, 20).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            logging.info("Page has fully loaded!")
            
            # Get list of ad elements
            ads_elements = self.browser.find_elements(
                By.CSS_SELECTOR,
                "div.x193iq5w.xxymvpz.xeuugli.x78zum5.x1iyjqo2.xs83m0k.x1d52u69.xktsk01.x1yztbdb.x1gslohp"
            )
            logging.info("Found %s ads on the page.", len(ads_elements))

            for idx, ad in enumerate(ads_elements, start=1):
                logging.info("Processing ad #%s", idx)
                # Initialize data variables for current ad
                ad_title = None
                library_id = None
                ad_link = None 
                started_info = None
                ad_text = None
                logo_url = None
                advertiser_info = None
                ad_link = None
                ad_images_url = []
                video_url = None

                # Click "See ad details"
                try:
                    WebDriverWait(self.browser, 10).until(
                        lambda d: d.execute_script("return document.readyState") == "complete"
                    )
                    see_details = ad.find_element(By.XPATH, ".//div[contains(text(), 'See ad details')]")
                    self.browser.execute_script("arguments[0].scrollIntoView(true);", see_details)
                    WebDriverWait(self.browser, 10).until(
                        EC.element_to_be_clickable((By.XPATH, ".//div[contains(text(), 'See ad details')]"))
                    )
                    self.browser.execute_script("arguments[0].click();", see_details)
                    logging.info("Ad #%s: 'See ad details' clicked.", idx)
                    time.sleep(2)  # brief pause for popover to open
                except Exception as click_exception:
                    logging.warning("Ad #%s: Unable to click 'See ad details': %s", idx, click_exception)
                    continue  # Skip to next ad if click fails

                # Extract title/status (with fallback if not found)
                try:
                    time.sleep(3)
                    status = WebDriverWait(self.browser, 20).until(EC.visibility_of_element_located((
                        By.CSS_SELECTOR,
                        "div.x2izyaf.x1lq5wgf.xgqcy7u.x30kzoy.x9jhf4c.xyamay9.x1pi30zi.x1l90r2v.x1swvt13.x1741yl6.x1xqjhkw span.x8t9es0.xw23nyj.x63nzvj.x1fp01tm.xq9mrsl.x1h4wwuj.x117nqv4.xeuugli.x1i64zmx"
                    )))
                    ad_title = status.text
                    logging.info("Ad #%s title: %s", idx, ad_title)
                except Exception:
                    logging.info("Ad #%s: No title found.", idx)

                # Extract Library ID
                # Extract Library ID and construct ad link
                try:
                    container = WebDriverWait(self.browser, 20).until(
                        EC.visibility_of_element_located((
                            By.CSS_SELECTOR,
                            "div.x2izyaf.x1lq5wgf.xgqcy7u.x30kzoy.x9jhf4c.xyamay9.x1pi30zi.x1l90r2v.x1swvt13.x1741yl6.x1xqjhkw"
                        ))
                    )
                    lib_id_element = WebDriverWait(container, 20).until(
                        EC.visibility_of_element_located((By.XPATH, ".//span[contains(text(), 'Library ID:')]"))
                    )
                    library_id_text = lib_id_element.text
                    # Remove "Library ID: " part if necessary
                    library_id = library_id_text.replace("Library ID: ", "").strip()
                    if library_id:
                        ad_link = f"https://www.facebook.com/ads/library/?id={library_id}"
                        logging.info("Ad #%s Library ID: %s", idx, library_id)
                        logging.info("Ad #%s Ad Link: %s", idx, ad_link)
                    else:
                        ad_link = None
                        logging.warning("Ad #%s: Library ID extraction returned empty string.", idx)
                except Exception as e:
                    logging.info("Ad #%s: No Library ID found. Error: %s", idx, e)
                    library_id = None
                    ad_link = None

                # Extract "Started running on" info
                try:
                    container = WebDriverWait(self.browser, 10).until(
                        EC.visibility_of_element_located(( 
                            By.CSS_SELECTOR,
                            "div.x2izyaf.x1lq5wgf.xgqcy7u.x30kzoy.x9jhf4c.xyamay9.x1pi30zi.x1l90r2v.x1swvt13.x1741yl6.x1xqjhkw"
                        ))
                    )
                    started = container.find_element(By.XPATH, ".//span[contains(text(), 'Started running on')]")
                    started_info = started.text
                    logging.info("Ad #%s started: %s", idx, started_info)
                except Exception:
                    logging.info("Ad #%s: No 'Started running on' info found.", idx)

                # Extract ad text
                try:
                    ad_text_elem = WebDriverWait(self.browser, 10).until(
                        EC.visibility_of_element_located(( 
                            By.CSS_SELECTOR,
                            'div.x178xt8z.xm81vs4.xso031l.xy80clv.x13fuv20.xu3j5b3.x1q0q8m5.x26u7qi.x15bcfbt.xolcy6v.x3ckiwt.xc2dlm9.x2izyaf.x1lq5wgf.xgqcy7u.x30kzoy.x9jhf4c.x1t2gpz5.x9f619.x6ikm8r.x10wlt62.x1n2onr6 div[style="white-space: pre-wrap;"] span'
                        ))
                    )
                    ad_text = ad_text_elem.text
                    logging.info("Ad #%s text: %s", idx, ad_text)
                except Exception:
                    logging.info("Ad #%s: No ad text found.", idx)

                # Extract ad logo URL
                try:
                    ad_logo = WebDriverWait(self.browser, 10).until(
                        EC.visibility_of_element_located(( 
                            By.CSS_SELECTOR, "div._7jyg._7jyi img._8nqq.img"
                        ))
                    )
                    logo_url = ad_logo.get_attribute("src")
                    logging.info("Ad #%s logo URL: %s", idx, logo_url)
                except Exception:
                    logging.info("Ad #%s: No image found.", idx)


                # Extract images and videos from the ads 
                try:
                    ad_media = WebDriverWait(self.browser, 10).until(
                        EC.visibility_of_element_located((
                            By.CSS_SELECTOR,
                            "div.x178xt8z.xm81vs4.xso031l.xy80clv.x13fuv20.xu3j5b3.x1q0q8m5.x26u7qi.x15bcfbt.xolcy6v.x3ckiwt.xc2dlm9.x2izyaf.x1lq5wgf.xgqcy7u.x30kzoy.x9jhf4c.x1t2gpz5.x9f619.x6ikm8r.x10wlt62.x1n2onr6 div.xb57i2i.x1q594ok.x5lxg6s.x78zum5.xdt5ytf.x10wlt62.x1n2onr6.x1ja2u2z.x1pq812k.xfk6m8.x1yqm8si.xjx87ck.xw2csxc.x7p5m3t.x9f619.xat24cr.xwib8y2.x1y1aw1k.x1rohswg.xhfbhpw"
                        ))
                    )
                    ad_images = ad_media.find_elements(By.TAG_NAME, "img")
                    print(f"The count of images is: {len(ad_images)}")
                    if ad_images:
                        for img in ad_images:
                            self.browser.execute_script("arguments[0].scrollIntoView(true);", img)
                            time.sleep(1)
                            img_url = img.get_attribute("src")
                            if img_url and "https://" in img_url:
                                print(f"Ad #{idx} image URL: {img_url}")
                                logging.info("Ad #%s image URL: %s", idx, img_url)
                                ad_images_url.append(img_url)
                    else:
                        logging.info("Ad #%s: No images found in media.", idx)
                except Exception as e:
                    try: 
                        ad_video_element = WebDriverWait(self.browser, 10).until(
                            EC.visibility_of_element_located((
                                By.CSS_SELECTOR, "div.x2izyaf.x1lq5wgf.xgqcy7u.x30kzoy.x9jhf4c.xyamay9.x1pi30zi.x1l90r2v.x1swvt13.x1741yl6.x1xqjhkw"
                            ))
                        )
                        ad_video = ad_video_element.find_element(By.CSS_SELECTOR, "video.x1lliihq.x5yr21d.xh8yej3")
                        if ad_video: 
                            self.browser.execute_script("arguments[0].scrollIntoView(true);", ad_video)
                            time.sleep(2)
                            video_url = ad_video.get_attribute("src")
                            print(f"Ad #{idx} video URL: {video_url}")
                            logging.info("Ad #%s video URL: %s", idx, video_url)
                    except Exception as video_e: 
                        print("No video found for this ad")
                        video_url = None
                    print(f"Ad #{idx}: No image and video found. Error: {e}")
                    logging.error("Ad #%s: No image found. Error: %s", idx, e)


                # Click to show "about" info and extract advertiser info
                try:
                    about_ad = WebDriverWait(self.browser, 10).until(
                    EC.element_to_be_clickable((
                        By.XPATH,
                        ".//div[contains(text(), 'About the advertiser')]"
                    ))
                   )
                    self.browser.execute_script("arguments[0].scrollIntoView(true);", about_ad)
                    about_ad.click()
                    try:
                        about_advertiser = WebDriverWait(self.browser, 10).until(
                            EC.visibility_of_element_located(( 
                                By.CSS_SELECTOR,
                                "div.x78zum5.xwxc41k.x7a106z span.x8t9es0.x1uxerd5.xrohxju.x108nfp6.xq9mrsl.x1h4wwuj.x117nqv4.xeuugli"
                            ))
                        )
                        advertiser_info = about_advertiser.text
                        logging.info("Ad #%s advertiser info: %s", idx, advertiser_info)
                    except Exception:
                        logging.info("Ad #%s: About advertiser info not found.", idx)
                except Exception:
                    logging.info("Ad #%s: Dropdown for ad bio not found.", idx)
                    

                # Attempt to close the pop-up with retry logic
                retry = 0
                while retry < 3:
                    try:
                        close_button = WebDriverWait(self.browser, 10).until(
                            EC.element_to_be_clickable((
                                By.CSS_SELECTOR,
                                "div.x6s0dn4.x78zum5.x1q0g3np.xozqiw3.x2lwn1j.xeuugli.x1iyjqo2.x19lwn94.x2lah0s.x13a6bvl div.x3nfvp2.x193iq5w.xxymvpz.xeuugli.x2lah0s"
                            ))
                        )
                        if close_button:
                            self.browser.execute_script("arguments[0].scrollIntoView(true);", close_button)
                            logging.info("Ad #%s: Close button found; clicking to close pop-up.", idx)
                            # Replace the close_button.click() line with:
                            
                            self.browser.execute_script("arguments[0].click();", close_button)
                            time.sleep(2)
                            break
                    except Exception as e:
                        logging.info("Ad #%s: No close button found on attempt %s: %s", idx, retry+1, e)
                        retry += 1
                        time.sleep(3)
                else:  # Only executes if the loop completes without breaking (i.e., all retries failed)
                    try:
                        # Send ESC key as fallback
                        self.browser.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                        logging.info("Ad #%s: Sent ESC key to close pop-up as fallback.", idx)
                    except Exception as e:
                        logging.warning("Ad #%s: ESC key fallback failed: %s", idx, e)
                time.sleep(3)  # Short pause before processing next ad

                # Save the ad data into our structured JSON object
                ad_data = {
                    "ad_number": idx,
                    "title": ad_title,
                    "library_id": library_id,
                    "ad_link": ad_link,
                    "started_running": started_info,
                    "ad_text": ad_text,
                    "logo_url": logo_url,
                    "advertiser_info": advertiser_info,
                    "ad_images": ad_images_url,
                    "ad_video" : video_url
                    
                }
                self.ads_data.append(ad_data)
            
            # Save all ads data to a JSON file after processing is complete
            self.save_json_data()
        except Exception as e:
            logging.error("Error in extracting ads: %s", e)

    def save_json_data(self):
        """Saves the collected ads data to a JSON file."""
        try:
            with open("ads_data.json", "w") as f:
                json.dump(self.ads_data, f, indent=4)
            logging.info("Ads data successfully saved to ads_data.json")
        except Exception as e:
            logging.error("Failed to save JSON data: %s", e)

    def run(self):
        try:
            self.setup_driver()
            self.browser.get(self.url)
            # Wait briefly for initial load
            WebDriverWait(self.browser, 10).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            time.sleep(2)
            self.scroll_page(scrolls=2)
            self.extract_ads()
        finally:
            if self.browser:
                self.browser.quit()


# Flask app for input fields
app = Flask(__name__)

HTML_FORM = """
<!doctype html>
<html lang="en">
  <head>
    <title>Facebook Ads Scraper</title>
  </head>
  <body>
    <h2>Enter Keyword and Country Code</h2>
    <form method="post">
      <label for="keyword">Keyword:</label><br>
      <input type="text" id="keyword" name="keyword" value="caterpillar"><br>
      <label for="country">Country Code (e.g., IN, US):</label><br>
      <input type="text" id="country" name="country" value="IN"><br><br>
      <input type="submit" value="Scrape Ads">
    </form>
  </body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        keyword = request.form.get("keyword", "caterpillar")
        country = request.form.get("country", "IN")
        logging.info("Received input: keyword=%s, country=%s", keyword, country)
        scraper = FacebookAdsScraper(keyword, country)
        # Run scraper (this is blocking; for production consider asynchronous handling)
        scraper.run()
        return jsonify({"status": "Scraping completed. Check server logs for output."})
    return render_template_string(HTML_FORM)


if __name__ == "__main__":
    # To run as a standalone server, e.g., with Flask's built-in server.
    app.run(host="0.0.0.0", port=5000, debug=True)
