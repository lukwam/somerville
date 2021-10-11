# -*- coding: utf-8 -*-
"""Cloud Function to update the Somerville Meeting Calendar in Google Calendar."""
import random
from datetime import datetime
from datetime import timedelta
from time import mktime
from urllib.parse import urlparse

import dateparser
import feedparser
from google.cloud import firestore
from googleapiclient.discovery import build
from pytz import timezone
from pytz import utc

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
        "timeZone": "America/New_York",
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
    tz = timezone("America/New_York")
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
        meeting_date = tz.localize(dateparser.parse(date_string)).astimezone(utc)

        # parse published time struct
        published = tz.localize(datetime.fromtimestamp(mktime(published_time))).astimezone(utc)

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
                "meeting_id": mid,
                "date": entry["date"],
                "link": entry["link"],
                "name": entry["name"],
                "updates": [],
            }
        meetings[mid]["updates"].append(entry)
    return meetings


def prepare_rss_events(meetings):
    """Return a dict of RSS meetings in Google Calendar event format."""
    events = {}
    for meeting in meetings.values():
        event_id = meeting["id"]
        start = meeting["date"].astimezone(timezone("America/New_York"))
        end = start + timedelta(hours=1)
        description = f"Meeting Link: {meeting['link']}"
        event = {
            "id": event_id,
            "summary": meeting["name"],
            "description": description,
            "start": {"dateTime": start.isoformat(), "timeZone": "America/New_York"},
            "end": {"dateTime": end.isoformat(), "timeZone": "America/New_York"},

        }
        events[event_id] = event
    return events


def update_events(old_events, new_events):
    """Update events in Google Calendar."""
    added = []
    for eid, event in new_events.items():
        if eid not in old_events:
            added.append(eid)
            print(
                f" + {event['start']['dateTime']}: {event['summary']} [{eid}]",
            )
            add_event(event)
    print(f"Added: {len(added)}")

    deleted = []
    for eid, event in old_events.items():
        if eid not in new_events:
            deleted.append(eid)
            print(
                f" - {event['start']['dateTime']}: {event['summary']} [{eid}]",
            )
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


def update_firestore_meetings(meetings):
    """Update meetings in firestore and generate unique IDs."""
    client = firestore.Client()
    collection = "meetings"
    ref = client.collection(collection)

    current = {}
    for doc in ref.stream():
        meeting = doc.to_dict()
        meeting_id = meeting["meeting_id"]
        meeting["event_id"] = doc.id
        current[meeting_id] = meeting
    print(f"Current Firestore meetings: {len(current)}")

    add = []
    for meeting_id in meetings:
        if meeting_id not in current:
            add.append(meetings[meeting_id])
    print(f"Add to Firestore: {len(add)}")

    delete = []
    for meeting_id in current:
        if meeting_id not in meetings:
            delete.append(current[meeting_id])
    print(f"Delete from Firestore: {len(delete)}")

    # add new meetings to firestore and "current"
    for meeting in add:
        meeting_id = meeting["meeting_id"]
        doc_id = ''.join(random.choices("abcdefghijklmnopqrstuv0123456789", k=10))
        meeting["date"] = meeting["date"].replace(tzinfo=timezone("UTC"))
        meeting["event_id"] = doc_id
        ref.document(doc_id).set(meeting)
        current[meeting_id] = meeting

    # delete old meetings from firestore and "current"
    for meeting in delete:
        doc_id = meeting["event_id"]
        meeting_id = meeting["meeting_id"]
        ref.document(doc_id).delete()
        del current[meeting_id]

    # update meetings in firestore
    for meeting_id in meetings:
        meeting = meetings[meeting_id]
        if meeting_id not in current:
            continue
        doc_id = current[meeting_id]["event_id"]
        meeting["event_id"] = doc_id
        meeting["date"] = meeting["date"].replace(tzinfo=timezone("UTC"))
        ref.document(doc_id).set(meeting)

    firestore_meetings = {}
    for doc in ref.stream():
        doc_id = doc.id
        meeting = doc.to_dict()
        meeting_id = meeting["meeting_id"]
        meeting["id"] = doc_id
        firestore_meetings[meeting_id] = meeting
    return firestore_meetings


def update_meeting_calendar(request):
    """Get events from Somerville Meeting Calendar."""
    print(f"Getting RSS entries from {RSS_FEED}...")
    entries = get_rss_entries()
    print(f"RSS Entries: {len(entries)}")

    print("Getting meetings from RSS entries...")
    rss_meetings = get_rss_meetings(entries)
    print(f"RSS Meetings: {len(rss_meetings)}")

    print("Update meetings in Firestore...")
    meetings = update_firestore_meetings(rss_meetings)
    print(f"Firestore Meetings: {len(meetings)}")

    print("Preparing events for Google Calendar...")
    rss_events = prepare_rss_events(meetings)
    print(f"RSS Events: {len(rss_events)}")

    print("Getting events from Google Calendar...")
    google_events = get_google_calendar_events_dict()
    print(f"Events: {len(google_events)}")

    print("Updating events in Google calendar...")
    update_events(google_events, rss_events)
    print("Done.")

    return "ok"


if __name__ == "__main__":
    update_meeting_calendar(None)
