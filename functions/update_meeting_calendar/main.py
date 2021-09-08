"""Cloud Function to update the Somerville Meeting Calendar in Google Calendar."""
import dateparser
import feedparser
import json
from datetime import datetime
from datetime import timedelta
from googleapiclient.discovery import build
from pytz import timezone
from time import mktime
from urllib.parse import urlparse


CALENDAR_ID = "rfkur2e12ehe3kcd712b28kgpo@group.calendar.google.com"
RSS_FEED = "http://somervillecityma.iqm2.com/Services/RSS.aspx?Feed=Calendar"


def add_event(event):
    """Add an event to Google Calendar."""
    service = build('calendar', 'v3', cache_discovery=False)
    return service.events().insert(calendarId=CALENDAR_ID, body=event).execute()

def delete_event(event_id):
    """Delete an event from Google Calendar."""
    service = build('calendar', 'v3', cache_discovery=False)
    return service.events().delete(calendarId=CALENDAR_ID, eventId=event_id).execute()

def update_event(event_id, event):
    """Update an event from Google Calendar."""
    service = build('calendar', 'v3', cache_discovery=False)
    return service.events().patch(calendarId=CALENDAR_ID, eventId=event_id, body=event).execute()


def get_google_calendar_events():
    """Return a list of events from Google Calendar."""
    service = build('calendar', 'v3', cache_discovery=False)
    params = {
        "calendarId": CALENDAR_ID,
    }
    events = service.events()
    request = events.list(**params)

    items = []
    while request is not None:
        response = request.execute()
        items += response.get("items", [])
        request = events.list_next(request, response)
    return items


def get_google_calendar_events_dict():
    """Reeturn a dict of events from Google Calendar."""
    events = {}
    for event in get_google_calendar_events():
        eid = event["id"]
        events[eid] = event
    return events


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


def prepare_rss_events(meetings):
    """Return a dict of RSS meetings in Google Calendar event format."""
    tz = timezone('America/New_York')
    events = {}
    for mid, meeting in meetings.items():
        event_id = f"somerville{mid}"
        start = tz.localize(meeting["date"])
        end = start + timedelta(hours=1)
        description = (
            f"Meeting Link: {meeting['link']}"
        )
        event = {
            "id": event_id,
            "summary": meeting["name"],
            "description": description,
            "start": {"dateTime": start.isoformat()},
            "end": {"dateTime": end.isoformat()}
        }
        events[event_id] = event
    return events


def update_events(old_events, new_events):
    """Update events in Google Calendar."""
    added = []
    for eid, event in new_events.items():
        if eid not in old_events:
            added.append(eid)
            print(f" + {event['start']['dateTime']}: {event['summary']} [{eid}]")
            add_event(event)
    print(f"Added: {len(added)}")

    deleted = []
    for eid, event in old_events.items():
        if eid not in new_events:
            deleted.append(eid)
            print(f" - {event['start']['dateTime']}: {event['summary']} [{eid}]")
            delete_event(eid)
    print(f"Deleted: {len(deleted)}")

    updated = []
    for eid, old in old_events.items():
        if eid not in new_events:
            continue
        new = new_events[eid]
        output = []
        for key in sorted(new):
            n = new[key]
            o = old.get(key)
            if o != n:
                output.append(f"  {key}: {o} -> {n}")
        if output:
            updated.append(new)
            print(f"\nUpdating {eid}:")
            print("\n".join(output))
            update_event(eid, new)
    print(f"Updated: {len(updated)}")


def update_meeting_calendar(request):
    """Get events from Somerville Meeting Calendar."""
    print(f"Getting RSS entries from {RSS_FEED}...")
    entries = get_rss_entries()
    print(f"RSS Entries: {len(entries)}")

    print("Getting meetings from RSS entries...")
    meetings = get_rss_meetings(entries)
    print(f"Meetings: {len(meetings)}")

    print("Preparing events for Google Calendar...")
    rss_events = prepare_rss_events(meetings)
    print(f"RSS Events: {len(rss_events)}")

    print("Getting events from Google Calendar...")
    google_events = get_google_calendar_events_dict()
    print(f"Events: {len(google_events)}")

    print(f"Updating events in Google calendar...")
    update_events(google_events, rss_events)
    print(f"Done.")

if __name__ == "__main__":
    update_meeting_calendar(None)
