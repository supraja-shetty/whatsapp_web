import os
import json
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME", "whatsapp")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "http://localhost:5000/webhook")
LOCAL_PAYLOAD_FOLDER = "./payloads"

if not MONGO_URI:
    raise Exception("MONGO_URI env variable not set")

try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    client.admin.command('ping')
    db = client[DB_NAME]
    print("Connected to MongoDB")
except Exception as e:
    print("MongoDB connection error:", e)
    exit(1)

def post_to_webhook(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        payload = json.load(f)
    try:
        r = requests.post(WEBHOOK_URL, json=payload, timeout=10)
        print(f"{os.path.basename(filepath)} -> {r.status_code}, {r.text}")
    except Exception as e:
        print("Failed to post:", e)

def insert_directly(filepath):
    col = db.processed_messages
    with open(filepath, "r", encoding="utf-8") as f:
        payload = json.load(f)
    col.insert_one({"raw_payload": payload, "imported_at": __import__("time").time()})
    print("Inserted raw payload:", filepath)

if __name__ == "__main__":
    for fname in os.listdir(LOCAL_PAYLOAD_FOLDER):
        if fname.lower().endswith(".json"):
            path = os.path.join(LOCAL_PAYLOAD_FOLDER, fname)
            post_to_webhook(path)

