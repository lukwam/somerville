"""Cloud Function to update the Somerville Meeting Calendar in Google Calendar."""
import datetime
import dateparser
import feedparser
import json
import os
from datetime import datetime
from time import mktime
from urllib.parse import urlparse



CALENDAR_ID = os.environ.get("CALENDAR_ID")
RSS_FEED = "http://somervillecityma.iqm2.com/Services/RSS.aspx?Feed=Calendar"


def get_rss_entries():
    """Return a list of entries from the Somerville Meeting Calendar RSS feed."""
    feed = feedparser.parse(RSS_FEED)
    items = []
    for entry in sorted(feed["entries"], key=lambda x: x["id"]):
        entry_id = entry["id"]
        link = entry["link"]
        published_time = entry["published_parsed"]
        summary = entry["summary"]
        tags = [x["term"] for x in entry["tags"]]
        title = entry["title"]

        # get meeting ID
        meeting_id = urlparse(link).query.split("=")[1]

        # get the meeting name, type and date
        meeting_name, meeting_type, date_string = title.split(" - ")

        # parse date string
        meeting_date = dateparser.parse(date_string)

        # parse published time struct
        published = datetime.fromtimestamp(mktime(published_time))

        item = {
            "id": meeting_id,
            "date": meeting_date,
            "link": link,
            "name": meeting_name,
            "published": published,
            "rss_id": entry_id,
            "summary": summary,
            "tags": tags,
            "title": title,
            "type": meeting_type,
        }
        items.append(item)
    return items

def get_rss_meetings(entries):
    """Return a dict of meetings from the RSS feed entries."""
    meetings = {}
    for entry in entries:
        mid = entry["id"]
        if mid not in meetings:
            meetings[mid] = {
                "id": mid,
                "date": entry["date"],
                "link": entry["link"],
                "name": entry["name"],
                "updates": [],
            }
        meetings[mid]["updates"].append(entry)
    return meetings

def update_meeting_calendar(request):
    """Get events from Somerville Meeting Calendar."""
    print(f"Getting RSS entries from {RSS_FEED}...")
    entries = get_rss_entries()
    print(f"RSS Entries: {len(entries)}")

    print("Getting meetings from RSS entries...")
    meetings = get_rss_meetings(entries)
    print(f"Meetings: {len(meetings)}")

    for mid in sorted(meetings, key=lambda x: meetings[x]["date"]):
        meeting = meetings[mid]
        print(f"\n{mid} {meeting['name']} - {meeting['date']}:")
        for u in meetings[mid]["updates"]:
            print(f"  * {u['type']}: {u['rss_id']}")

if __name__ == "__main__":
    update_meeting_calendar(None)
