from flask import Flask, render_template
from pymongo import MongoClient
from collections import defaultdict, Counter
from datetime import datetime, date, timedelta
import json
import os
app = Flask(__name__)

# ---- MongoDB Connection ----
MONGO_URI = os.getenv("MONGO_URI")   # change if using Atlas
client = MongoClient(MONGO_URI)
db = client["air_quality"]
collection = db["readings"]


@app.route("/")
def index():
    # Get all readings, sorted by timestamp string
    docs = list(collection.find().sort("timestamp", 1))

    if not docs:
        return render_template("index.html", no_data=True)

    # ---- Build time-series arrays ----
    timestamps = [d.get("timestamp", "") for d in docs]
    mq_values  = [d.get("mq", 0) for d in docs]
    temp_values = [d.get("temp", 0) for d in docs]
    hum_values  = [d.get("hum", 0) for d in docs]
    quality_list = [d.get("quality", "Unknown") for d in docs]

    # ---- Current (latest) values ----
    latest = docs[-1]
    current_time = latest.get("timestamp", "")
    current_mq = latest.get("mq", None)
    current_temp = latest.get("temp", None)
    current_hum = latest.get("hum", None)
    current_quality = latest.get("quality", "Unknown")

    # ---- Overall averages ----
    def safe_avg(vals):
        vals = [v for v in vals if isinstance(v, (int, float))]
        return round(sum(vals) / len(vals), 2) if vals else None

    avg_mq = safe_avg(mq_values)
    avg_temp = safe_avg(temp_values)
    avg_hum = safe_avg(hum_values)

    # ---- Daily average MQ (for bar chart) ----
    day_to_mq = defaultdict(list)
    for d in docs:
        ts = d.get("timestamp")
        mq = d.get("mq")
        if ts and isinstance(mq, (int, float)):
            day = ts[:10]  # "YYYY-MM-DD"
            day_to_mq[day].append(mq)

    day_labels = sorted(day_to_mq.keys())
    day_avg_mq = [safe_avg(day_to_mq[day]) for day in day_labels]

    # ---- Today vs Yesterday comparison ----
    today = date.today()
    yesterday = today - timedelta(days=1)
    today_str = today.isoformat()
    yesterday_str = yesterday.isoformat()

    today_avg = safe_avg(day_to_mq.get(today_str, []))
    yesterday_avg = safe_avg(day_to_mq.get(yesterday_str, []))

    # ---- Quality distribution ----
    q_counts = Counter(quality_list)
    quality_labels = list(q_counts.keys())
    quality_counts = list(q_counts.values())

    # Prepare data as JSON for Chart.js
    context = {
        "no_data": False,
        "timestamps": json.dumps(timestamps),
        "mq_values": json.dumps(mq_values),
        "temp_values": json.dumps(temp_values),
        "hum_values": json.dumps(hum_values),

        "day_labels": json.dumps(day_labels),
        "day_avg_mq": json.dumps(day_avg_mq),

        "quality_labels": json.dumps(quality_labels),
        "quality_counts": json.dumps(quality_counts),

        "current_time": current_time,
        "current_mq": current_mq,
        "current_temp": current_temp,
        "current_hum": current_hum,
        "current_quality": current_quality,

        "avg_mq": avg_mq,
        "avg_temp": avg_temp,
        "avg_hum": avg_hum,

        "today_str": today_str,
        "yesterday_str": yesterday_str,
        "today_avg": today_avg,
        "yesterday_avg": yesterday_avg,
    }

    return render_template("index.html", **context)


if __name__ == "__main__":
    # host="0.0.0.0" -> access from phone on same Wi-Fi
    app.run(debug=True, host="0.0.0.0", port=5000)
