import os
import time
import requests
from datetime import datetime, timezone

APP_ID  = os.getenv("ONESIGNAL_APP_ID")
API_KEY = os.getenv("ONESIGNAL_API_KEY")

def fetch_usage():
    """
    Paginates through all notifications sent this month and tallies
    deliveries by channel from the platform_delivery_stats field.
    """
    limit, offset = 50, 0
    usage = {"mobile_push": 0, "web_push": 0, "email": 0, "sms": 0}

    # compute UTC timestamp for the start of this month
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    while True:
        resp = requests.get(
            "https://onesignal.com/api/v1/notifications",
            params={"app_id": APP_ID, "limit": limit, "offset": offset},
            headers={"Authorization": f"Basic {API_KEY}"}
        )
        resp.raise_for_status()

        page = resp.json().get("notifications", [])
        if not page:
            break

        for msg in page:
            sent_ts = msg.get("completed_at", 0)
            sent_dt = datetime.fromtimestamp(sent_ts, timezone.utc)
            # stop paginating once you hit last month’s messages
            if sent_dt < month_start:
                return usage

            stats = msg.get("platform_delivery_stats", {})
            usage["mobile_push"] += stats.get("push", 0)
            usage["web_push"]    += stats.get("web_push", 0)
            usage["email"]       += stats.get("email", 0)
            usage["sms"]         += stats.get("sms", 0)

        offset += limit
        time.sleep(0.2)  # throttle to avoid rate limits

    return usage
