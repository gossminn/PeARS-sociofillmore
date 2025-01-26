import time

import requests

import pandas as pd

from app import app, db
from app.api.models import Suggestions
from app.utils_db import create_suggestion_in_db


def suggest_femicides():
    r = requests.get(
        url="https://responsibility-framing-femicide-detector.hf.space/crawl",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {app.config['HF_TOKEN']}"}
    )
    thread_id = r.json()["thread_id"]
    print(f"Server started crawling, thread_id={thread_id}")

    crawl_complete = False
    while not crawl_complete:
        time.sleep(10)
        r = requests.get(
            url=f"https://responsibility-framing-femicide-detector.hf.space/progress/{thread_id}",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {app.config['HF_TOKEN']}"}            
        )
        status = r.json()
        if status["done"]:
            print(f"Crawling (thread_id={thread_id}) complete!")
            crawl_complete = True
        else:
            print(f"Crawling in progress (thread_id={thread_id}), found {status['progress']} new articles so far")

    r = requests.get(
        url=f"https://responsibility-framing-femicide-detector.hf.space/get_data/{thread_id}",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {app.config['HF_TOKEN']}"}            
    )

    scrape_file = f"scraping_records.{time.time_ns()}.jsonl"
    with open(scrape_file, "w", encoding="utf-8") as f:
        f.write(r.text)

    new_records = pd.read_json(scrape_file, orient="records", lines=True)
    new_records_femicides = new_records[new_records["detected_possible_femicide"]]
    for _, row in new_records_femicides.iterrows():
        if not db.session.query(Suggestions).filter_by(url=row["link"]).all():
            print("adding suggested possible femicide article to DB:", row["link"])
            create_suggestion_in_db(row["link"], "possible_femicides", f"auto-detected possible femicide, detector thread_id={thread_id}, keywords_matched={row['femicide_keywords_matched']}", "femicide_suggestor")
