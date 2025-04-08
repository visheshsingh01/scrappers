import time
import urllib.parse

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# 1) Global settings
RETRIES   = 3
DELAY     = 2
MAX_PAGES = 5
KEYWORD   = "christian dior perfumes"

# 2) Build search URL
def build_search_url(keyword, page):
    q = urllib.parse.quote_plus(keyword)
    return (
        "https://www.alibaba.com/trade/search"
        f"?tab=all&SearchText={q}"
        f"&page={page}"
        "&spm=a2700.product_home_newuser.home_new_user_first_screen_fy23_pc_search_bar.keydown__Enter"
    )

# 3) Spinner killer + waiters
def kill_spinner():
    browser.execute_script("""
      const css = document.createElement('style');
      css.innerText = `
        .next-loading, .loading-spinner { display: none !important; }
      `;
      document.head.appendChild(css);
    """)

def wait_for_page():
    WebDriverWait(browser, 20).until(
        EC.invisibility_of_element_located((By.CSS_SELECTOR, ".next-loading"))
    )
    WebDriverWait(browser, 30).until(
        EC.presence_of_all_elements_located((By.CLASS_NAME, "fy23-search-card"))
    )

# 4) Selenium setup
options = webdriver.ChromeOptions()
options.add_argument("--headless=new")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1920,1080")
options.add_argument("--ignore-certificate-errors")
options.add_argument("--ignore-ssl-errors")
options.add_argument("--log-level=3")
options.add_argument(
    "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/117.0.0.0 Safari/537.36"
)
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)
options.add_argument("--disable-blink-features=AutomationControlled")

# Use webdriver-manager so you don't have to manually install ChromeDriver
browser = webdriver.Chrome(
    ChromeDriverManager().install(),
    options=options
)

# Mask navigator.webdriver
browser.execute_cdp_cmd(
    "Page.addScriptToEvaluateOnNewDocument",
    {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"}
)

# 5) Main scraper
def scrape_alibaba(keyword, max_pages):
    for page in range(1, max_pages + 1):
        url = build_search_url(keyword, page)
        print(f"\nLoading page {page}: {url}")
        for i in range(RETRIES):
            try:
                browser.get(url)
                kill_spinner()
                wait_for_page()
                break
            except Exception as e:
                print(f"  → Retry {i+1}/{RETRIES} failed: {e}")
                time.sleep(DELAY)
        else:
            print(f"✖ Couldn’t load page {page}, skipping.")
            continue

        # → your scraping logic here
        cards = browser.find_elements(By.CLASS_NAME, "fy23-search-card")
        print(f"  • Found {len(cards)} cards on page {page}")

    browser.quit()

if __name__ == "__main__":
    scrape_alibaba(KEYWORD, MAX_PAGES)
