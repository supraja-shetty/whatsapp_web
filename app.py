import os
import json
import time
from datetime import datetime
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from pymongo import MongoClient, ASCENDING, DESCENDING
from bson.objectid import ObjectId
from dotenv import load_dotenv

# Optional socketio
ENABLE_SOCKETIO = os.getenv("ENABLE_SOCKETIO", "true").lower() == "true"
try:
    from flask_socketio import SocketIO, emit
except Exception:
    SocketIO = None

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("DB_NAME", "whatsapp")
PORT = int(os.getenv("PORT", 5000))
ENABLE_SOCKETIO = os.getenv("ENABLE_SOCKETIO", "true").lower() == "true"

app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
messages_col = db.processed_messages

# create index for faster queries
messages_col.create_index([("wa_id", ASCENDING), ("timestamp", DESCENDING)])
messages_col.create_index([("msg_id", ASCENDING)], unique=False)
messages_col.create_index([("meta_msg_id", ASCENDING)], unique=False)

socketio = None
if ENABLE_SOCKETIO and SocketIO:
    socketio = SocketIO(app, cors_allowed_origins="*")
else:
    socketio = None

def now_ts():
    return int(time.time())

def parse_whatsapp_payload(payload: dict):
    out = []
    messages = payload.get("messages") or payload.get("message") or []
    if isinstance(messages, dict):
        messages = [messages]
    for m in messages:
        msg = {}
        msg_id = m.get("id") or m.get("msg_id") or m.get("message_id")
        msg["msg_id"] = msg_id
        msg["meta_msg_id"] = m.get("context", {}).get("id") or m.get("context_id") or m.get("meta_msg_id")
        wa_id = m.get("from") or m.get("wa_id") or m.get("sender", {}).get("wa_id") or m.get("author")
        msg["wa_id"] = wa_id
        msg["name"] = m.get("sender_name") or m.get("profile", {}).get("name") or m.get("contacts", [{}])[0].get("profile", {}).get("name")
        msg["number"] = m.get("from") or m.get("to") or m.get("recipient")
        text = None
        if "text" in m:
            if isinstance(m["text"], dict):
                text = m["text"].get("body")
            else:
                text = m["text"]
        elif "message" in m and isinstance(m["message"], dict) and "text" in m["message"]:
            text = m["message"]["text"].get("body")
        elif "body" in m:
            text = m["body"]
        msg["text"] = text or ""
        ts = m.get("timestamp") or m.get("ts") or m.get("t") or payload.get("timestamp")
        try:
            msg["timestamp"] = int(ts) if ts else now_ts()
        except:
            try:
                msg["timestamp"] = int(datetime.fromisoformat(ts).timestamp())
            except Exception:
                msg["timestamp"] = now_ts()
        msg["direction"] = m.get("direction") or ("in" if wa_id and not wa_id.endswith("@g.us") else "in")
        msg["status"] = "received"
        out.append(msg)

    statuses = payload.get("statuses") or payload.get("status") or payload.get("statuses_array") or []
    if isinstance(statuses, dict):
        statuses = [statuses]
    for s in statuses:
        status = s.get("status")
        meta_msg_id = s.get("id") or s.get("message_id") or s.get("meta_msg_id") or s.get("msg_id")
        msg_entry = {
            "update_status": True,
            "status": status,
            "meta_msg_id": meta_msg_id,
            "msg_id": s.get("recipient_message_id") or s.get("message_id") or None,
            "timestamp": int(s.get("timestamp") or now_ts())
        }
        out.append(msg_entry)

    return out

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/webhook", methods=["POST"])
def webhook_receiver():
    try:
        payload = request.get_json(force=True)
    except Exception as e:
        return jsonify({"error": "invalid json", "details": str(e)}), 400

    parsed = parse_whatsapp_payload(payload)
    results = []
    for item in parsed:
        if item.get("update_status"):
            meta = item.get("meta_msg_id") or item.get("msg_id")
            if not meta:
                continue
            q = {"$or": [{"meta_msg_id": meta}, {"msg_id": meta}]}
            res = messages_col.update_many(q, {"$set": {"status": item["status"], "status_updated_at": item.get("timestamp", now_ts())}})
            results.append({"updated_count": res.modified_count, "query_meta": meta})
            if socketio:
                socketio.emit("status_update", {"meta_msg_id": meta, "status": item["status"]}, broadcast=True)
        else:
            doc = {
                "msg_id": item.get("msg_id"),
                "meta_msg_id": item.get("meta_msg_id"),
                "wa_id": item.get("wa_id"),
                "name": item.get("name") or "",
                "number": item.get("number") or "",
                "text": item.get("text") or "",
                "timestamp": item.get("timestamp") or now_ts(),
                "direction": item.get("direction") or "in",
                "status": item.get("status") or "received",
                "created_at": now_ts()
            }
            q = {}
            if doc["msg_id"]:
                q["msg_id"] = doc["msg_id"]
            elif doc["meta_msg_id"]:
                q["meta_msg_id"] = doc["meta_msg_id"]
            if q:
                existing = messages_col.find_one(q)
            else:
                existing = None
            if existing:
                messages_col.update_one({"_id": existing["_id"]}, {"$set": doc})
                results.append({"action": "updated", "doc": doc})
            else:
                inserted = messages_col.insert_one(doc)
                results.append({"action": "inserted", "id": str(inserted.inserted_id)})
                if socketio:
                    socketio.emit("new_message", {
                        "id": str(inserted.inserted_id),
                        "wa_id": doc["wa_id"],
                        "text": doc["text"],
                        "timestamp": doc["timestamp"],
                        "direction": doc["direction"],
                        "status": doc["status"],
                        "name": doc["name"],
                        "number": doc["number"]
                    }, broadcast=True)
    return jsonify({"ok": True, "results": results}), 200

@app.route("/api/conversations", methods=["GET"])
def get_conversations():
    pipeline = [
        {"$sort": {"timestamp": -1}},
        {
            "$group": {
                "_id": "$wa_id",
                "last_msg": {"$first": "$text"},
                "last_ts": {"$first": "$timestamp"},
                "name": {"$first": "$name"},
                "number": {"$first": "$number"},
                "last_status": {"$first": "$status"},
                "count": {"$sum": 1}
            }
        },
        {"$sort": {"last_ts": -1}}
    ]
    convs = list(messages_col.aggregate(pipeline))
    for c in convs:
        c["wa_id"] = c["_id"]
        c.pop("_id", None)
        c["unread"] = 0
    return jsonify(convs)

@app.route("/api/conversations/<wa_id>/messages", methods=["GET"])
def get_messages_for_conversation(wa_id):
    docs = list(messages_col.find({"wa_id": wa_id}).sort("timestamp", ASCENDING))
    out = []
    for d in docs:
        out.append({
            "id": str(d.get("_id")),
            "msg_id": d.get("msg_id"),
            "meta_msg_id": d.get("meta_msg_id"),
            "wa_id": d.get("wa_id"),
            "name": d.get("name"),
            "number": d.get("number"),
            "text": d.get("text"),
            "timestamp": d.get("timestamp"),
            "direction": d.get("direction"),
            "status": d.get("status")
        })
    return jsonify(out)

# NEW: get all messages without wa_id filter
@app.route("/api/messages/all", methods=["GET"])
def get_all_messages():
    docs = list(messages_col.find().sort("timestamp", ASCENDING))
    out = []
    for d in docs:
        out.append({
            "id": str(d.get("_id")),
            "msg_id": d.get("msg_id"),
            "meta_msg_id": d.get("meta_msg_id"),
            "wa_id": d.get("wa_id"),
            "name": d.get("name"),
            "number": d.get("number"),
            "text": d.get("text"),
            "timestamp": d.get("timestamp"),
            "direction": d.get("direction"),
            "status": d.get("status")
        })
    return jsonify(out)

@app.route("/api/messages/send", methods=["POST"])
def send_message_demo():
    data = request.get_json(force=True)
    wa_id = data.get("wa_id")
    text = data.get("text", "")
    if not wa_id or text is None:
        return jsonify({"error": "wa_id and text are required"}), 400
    doc = {
        "msg_id": data.get("msg_id") or f"local-{now_ts()}-{os.urandom(4).hex()}",
        "meta_msg_id": None,
        "wa_id": wa_id,
        "name": data.get("name", ""),
        "number": data.get("number", ""),
        "text": text,
        "timestamp": int(time.time()),
        "direction": "out",
        "status": "sent",
        "created_at": now_ts()
    }
    res = messages_col.insert_one(doc)
    payload = {
        "id": str(res.inserted_id),
        "wa_id": wa_id,
        "text": text,
        "timestamp": doc["timestamp"],
        "status": doc["status"],
        "direction": doc["direction"],
        "msg_id": doc["msg_id"]
    }
    if socketio:
        socketio.emit("new_message", payload, broadcast=True)
    return jsonify({"ok": True, "inserted_id": str(res.inserted_id), "message": payload}), 201

@app.route("/api/messages/update_status", methods=["POST"])
def api_update_status():
    data = request.get_json(force=True)
    ident = data.get("id")
    status = data.get("status")
    if not ident or not status:
        return jsonify({"error": "id and status required"}), 400
    q = {"$or": [{"msg_id": ident}, {"meta_msg_id": ident}, {"_id": ObjectId(ident) if ObjectId.is_valid(ident) else None}]}
    q = {"$or": [x for x in q["$or"] if x]}

    res = messages_col.update_many(q, {"$set": {"status": status, "status_updated_at": now_ts()}})
    if socketio:
        socketio.emit("status_update", {"id": ident, "status": status}, broadcast=True)
    return jsonify({"ok": True, "matched": res.matched_count, "modified": res.modified_count})

@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory(app.static_folder, filename)

if __name__ == "__main__":
    if socketio:
        socketio.run(app, host="0.0.0.0", port=PORT, debug=True)
    else:
        app.run(host="0.0.0.0", port=PORT, debug=True)
