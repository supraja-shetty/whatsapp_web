import os
import json
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("DB_NAME", "whatsapp")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "http://localhost:5000/webhook")
LOCAL_PAYLOAD_FOLDER = "./payloads"  # put your extracted sample payload JSONs here

def post_to_webhook(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        payload = json.load(f)
    try:
        r = requests.post(WEBHOOK_URL, json=payload, timeout=10)
        print(f"{os.path.basename(filepath)} -> {r.status_code}, {r.text}")
    except Exception as e:
        print("Failed to post:", e)

def insert_directly(filepath):
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    col = db.processed_messages
    with open(filepath, "r", encoding="utf-8") as f:
        payload = json.load(f)
    # naive insert: store payload under a wrapper (not parsed)
    col.insert_one({"raw_payload": payload, "imported_at": __import__("time").time()})
    print("inserted raw payload:", filepath)

if __name__ == "__main__":
    for fname in os.listdir(LOCAL_PAYLOAD_FOLDER):
        if fname.lower().endswith(".json"):
            path = os.path.join(LOCAL_PAYLOAD_FOLDER, fname)
            post_to_webhook(path)
