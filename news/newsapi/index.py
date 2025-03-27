import json
import requests

retries = 3
search_keyword = "Adani group"
api_key  = "d2bea0e9241e43a4917eddd7166e183f"
search_url = f"https://newsapi.org/v2/everything?q={search_keyword}&apiKey={api_key}"

def scrape_news_from_newsapi():
    for attempt in range(retries):
        try:
            response = requests.get(search_url)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "ok":
                    reordered_data = {
                        "status": data["status"],
                        "keyword": search_keyword,
                        **data
                    }
                with open("page.json", "w", encoding="utf-8") as file:
                    json.dump(reordered_data, file, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Failed to scrape news after {retries} attempts.")

scrape_news_from_newsapi()