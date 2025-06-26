
import requests
import json
from typing import Optional, List
from datetime import datetime, timezone
import uuid


def create_event(
        base_url: str,
        auth: tuple,
        title: str,
        start_datetime: str,
        duration_minutes: int = 60,
        time_zone: str = "UTC",
        description: Optional[str] = None,
        location: Optional[str] = None,
        attendee_emails: Optional[List[str]] = None,
        priority: int = 5
):
    """
    Schedules a new event in the EGroupware calendar using the JSCalendar format.
    """
    url = f"{base_url}/calendar"
    now_utc = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    # Construct the base JSCalendar payload
    payload = {
        "@type": "Event",
        "prodId": "EGroupware AI-Bot v1.0",
        "uid": f"urn:uuid:{uuid.uuid4()}",
        "created": now_utc,
        "updated": now_utc,
        "title": title,
        "start": start_datetime,
        "timeZone": time_zone,
        "duration": f"PT{duration_minutes}M",  # ISO 8601 duration format
        "status": "confirmed",
        "priority": priority,
        "privacy": "public"
    }

    # Add optional fields if they exist
    if description:
        payload["description"] = description
    if location:
        payload["locations"] = {"loc-1": {"@type": "Location", "name": location}}

    # --- Handle Participants ---
    # The owner of the event is the person making the request.
    owner_username = auth[0]
    owner_email = "sysop@amir.egroupware.net"  # Placeholder email, adjust as needed
    participants = {
        "owner": {
            "@type": "Participant",
            "name": owner_username,  # We may not have full name, username is a safe fallback
            "email": owner_email,  # Assuming username might be an email, or a placeholder
            "roles": {"owner": True, "chair": True},
            "participationStatus": "accepted"
        }
    }
    # Add other attendees if provided
    if attendee_emails:
        for i, email in enumerate(attendee_emails):
            participants[f"attendee-{i + 1}"] = {
                "@type": "Participant",
                "email": email,
                "participationStatus": "needs-action"
            }
    payload["participants"] = participants

    try:
        response = requests.post(
            url, auth=auth, json=payload, headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()

        # Return a structured response for the LLM
        return json.dumps({
            "status": "success",
            "message": "Event created successfully in the calendar.",
            "event_details": {
                "title": title,
                "start": start_datetime,
                "timeZone": time_zone,
                "duration_minutes": duration_minutes,
                "attendees": list(p["email"] for p in participants.values())
            }
        })
    except requests.exceptions.HTTPError as e:
        return json.dumps({
            "status": "error",
            "message": f"Failed to create event. Server responded with: {e.response.text}"
        })



def list_events(base_url: str, auth: tuple, start_date: str, end_date: str):
    """
    Retrieves and lists upcoming events from the calendar within a date range.
    Required: start_date, end_date (format YYYY-MM-DD).
    """
    url = f"{base_url}/calendar"
    # EGroupware's API for filtering by date might require specific query params.
    # This is a simplified example. You might need to adjust based on EGroupware's CalDAV/GroupDAV specifics.
    # For this example, we'll fetch all and filter, which is inefficient but demonstrates the principle.
    params = {"props[]": "getetag", "limit": 100}  # Assuming we can fetch events

    try:
        response = requests.get(url, auth=auth, params=params, headers={"Accept": "application/json"})
        response.raise_for_status()
        data = response.json()

        if not data.get("results"):
            return "No events found in the calendar."

        events = data.get("result", [])
        # This is a placeholder for actual filtering logic.
        # A real implementation would need to parse event start/end times.
        event_titles = [event.get('title', 'Untitled Event') for event in events[:5]]

        if not event_titles:
            return f"No events found between {start_date} and {end_date}."

        return f"Found {len(events)} events. Here are the next few: {', '.join(event_titles)}."

    except requests.exceptions.HTTPError as e:
        return f"Error listing events: {e.response.status_code} - {e.response.text}"
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"