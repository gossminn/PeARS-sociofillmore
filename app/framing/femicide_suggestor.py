import os
import datetime
import time
import json

import dateparser
import pandas as pd
import feedparser
from newsplease import NewsPlease, NewsArticle

from app.utils_db import create_suggestion_in_db


MAX_ARCHIVE_SIZE = 1_000_000

FEEDS_TO_WATCH = {
    "it": {
        "repubblica": "http://www.repubblica.it/rss/cronaca/rss2.0.xml",
        "corriere": "http://xml2.corriereobjects.it/rss/cronache.xml",
        "rainews": "https://www.rainews.it/rss/cronaca",
        "sky24": "https://tg24.sky.it/rss/tg24.xml",
        "tgcom": "http://www.tgcom24.mediaset.it/rss/cronaca.xml",
        "ansa": "https://www.ansa.it/sito/notizie/cronaca/cronaca_rss.xml",
        "open": "https://www.open.online/feed/"
    },
    "nl": {
        "ad": "COLLECTION::rss/ad.json",
        "nu.nl": "https://www.nu.nl/rss/Algemeen",
        "nos-algemeen": "https://feeds.nos.nl/nosnieuwsalgemeen",
        "nos-domestic": "https://feeds.nos.nl/nosnieuwsbinnenland",
        "nos-international": "https://feeds.nos.nl/nosnieuwsbuitenland",
        "nos-politics": "https://feeds.nos.nl/nosnieuwspolitiek",
        "nos-economy": "https://feeds.nos.nl/nosnieuwseconomie",
        "telegraaf": "https://www.telegraaf.nl/rss",
        "volkskrant-frontpage": "https://www.volkskrant.nl/voorpagina/rss.xml",
        "volkskrant-columns": "https://www.volkskrant.nl/columns-van-de-dag/rss.xml",
        "volkskrant-news-background": "https://www.volkskrant.nl/nieuws-achtergrond/rss.xml",
        "volkskrant-opinion": "https://www.volkskrant.nl/columns-opinie/rss.xml",
        "trouw-frontpage": "https://www.trouw.nl/voorpagina/rss.xml",
        "trouw-columns": "https://www.trouw.nl/columnisten/rss.xml",
        "trouw-verdieping": "https://www.trouw.nl/verdieping/rss.xml",
        "trouw-dossiers": "https://www.trouw.nl/dossiers/rss.xml",
        "trouw-politics": "https://www.trouw.nl/politiek/rss.xml",
        "trouw-opinion": "https://www.trouw.nl/opinie/rss.xml",
        "parool-frontpage": "https://www.parool.nl/voorpagina/rss.xml",
        "parool-uitgelicht": "https://www.parool.nl/topverhalen/rss.xml",
        "parool-amsterdam": "https://www.parool.nl/amsterdam/rss.xml",
        "parool-netherlands": "https://www.parool.nl/nederland/rss.xml",
        "parool-opinion": "https://www.parool.nl/columns-opinie/rss.xml"
    }
} 

with open("rss/femicide_keywords.json", encoding="utf-8") as f:
    FEMICIDE_KEYWORDS = json.load(f)

def is_possible_femicide(text):
    for kw in FEMICIDE_KEYWORDS:
        if all(phrase in text.lower() for phrase in kw.split("+")):
            return True
    return False


def crawl():
    for language in FEEDS_TO_WATCH.keys():
        records_file = f"rss/records/{language}.jsonl"
        if not os.path.isfile(records_file):
            existing_records = None
            known_urls = set()
        else:
            existing_records = pd.read_json(records_file, orient="records", lines=True)
            known_urls = set(existing_records["link"].to_list())
        new_records = get_new_records(known_urls, language)
        new_records_femicides = new_records[new_records["detected_possible_femicide"]]
        for _, row in new_records_femicides:
            print("possible femicide:", row["link"])
            create_suggestion_in_db(row["link"], "crawled_possible_femicides", "auto-detected based on keywords", "gossminn")

        final_records = pd.concat([existing_records, new_records], axis=0).reset_index(drop=True)
        final_records.to_json(records_file, orient="records", lines=True)
        with open(f"rss/database/logs_{language}.txt", "a", encoding="utf-8") as log_f:
            time_stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_f.write(f"[{time_stamp}] added {len(new_records)} records, new total: {len(final_records)}" + os.linesep)

        
def get_new_records(known_urls, language):
    new_records = []
    for feed_name, feed_link in FEEDS_TO_WATCH[language].items():
        if feed_link.startswith("COLLECTION::"):
            collection_file = feed_link.replace("COLLECTION::", "")
            with open(collection_file, "r") as f:
                subfeeds = json.load(f)
        else:
            subfeeds = {feed_name: feed_link}

        for sub_name, sub_link in subfeeds.items():
            if sub_name != feed_name:
                sub_name = f"{feed_name} ({sub_name})".lower()

            print(f"Crawling feed: {sub_name}")
            feed = feedparser.parse(sub_link)
            for entry in feed["entries"]:
                if entry["link"] in known_urls:
                    continue
                if len(new_records) + len(known_urls) >= MAX_ARCHIVE_SIZE:
                    print("\tMaximum archive limit reached, quitting...")
                    break
                article = NewsPlease.from_url(entry["link"])
                if isinstance(article, dict):
                    print("Something is wrong, article has the wrong class, details below:")
                    print(type(article))
                    print(article)
                    print()
                    continue
                if entry.get("published_parsed"):
                    time_stamp = pd.Timestamp(time.mktime(entry["published_parsed"]), unit="s")
                elif sub_name == "sky24":
                    time_stamp = pd.Timestamp(dateparser.parse(entry["published"], languages=["it"]))
                else:
                    time_stamp = None

                if language == "it":
                    all_txt = ""
                    if entry["title"]:
                        all_txt += entry["title"]
                    if article.description:
                        all_txt += "\n" + article.description
                    if article.maintext:
                        all_txt += "\n" + article.maintext
                    all_txt = all_txt.strip()                     

                    possible_femicide = is_possible_femicide(all_txt)
                else:
                    possible_femicide = False

                new_records.append({
                    "link": entry["link"],
                    "feed": sub_name,
                    "pubdate_timestamp": time_stamp,
                    "pubdate_string": entry.get("published"),
                    "title": entry["title"],
                    "description": article.description,
                    "body_text": article.maintext,
                    "detected_possible_femicide": possible_femicide
                })
    return pd.DataFrame(new_records)


if __name__ == "__main__":
    crawl()
