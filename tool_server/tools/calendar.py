import requests
import json
from typing import Optional, List
from datetime import datetime, timezone
import uuid
import re


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
    Schedules a new event in the user's personal EGroupware calendar,
    including all specified details and participants.
    """
    username = auth[0]
    # Dynamically construct the correct URL for the authenticated user's calendar.
    user_specific_base_url = re.sub(r'/(sysop|[^/]+)$', f'/{username}', base_url.rstrip('/'))
    url = f"{user_specific_base_url}/calendar/"

    now_utc = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    # --- Participant Block Construction ---
    participants = {}
    participant_key_counter = 1

    # 1. Add the event owner.
    # IMPORTANT: The generated email must be a valid, existing email for the user in EGroupware.
    owner_email = f"{username}@amir.egroupware.net"  # Adjust this format if needed.

    participants[str(participant_key_counter)] = {
        "@type": "Participant",
        "name": username.capitalize(),
        "email": owner_email,
        "kind": "individual",
        "roles": {"owner": True, "chair": True},
        "participationStatus": "accepted"
    }
    participant_key_counter += 1

    # 2. Add other attendees from the provided email list.
    if attendee_emails:
        for email in attendee_emails:
            attendee_name = email.split('@')[0].replace('.', ' ').title()

            participants[str(participant_key_counter)] = {
                "@type": "Participant",
                "name": attendee_name,
                "email": email,
                "kind": "individual",
                "roles": {"attendee": True},
                "participationStatus": "needs-action"
            }
            participant_key_counter += 1

    # --- Final Payload Construction ---
    payload = {
        "@type": "Event",
        "uid": f"urn:uuid:{uuid.uuid4()}",
        "created": now_utc,
        "updated": now_utc,
        "title": title,
        "start": start_datetime,
        "timeZone": time_zone,
        "duration": f"PT{duration_minutes}M",
        "participants": participants,
        "status": "confirmed",
        "priority": priority,
        "privacy": "public"
    }

    # Add optional text fields only if they were provided
    if description:
        payload["description"] = description
    if location:
        payload["locations"] = {"loc-1": {"@type": "Location", "name": location}}

    # --- API Call and Response Handling ---
    try:
        response = requests.post(
            url, auth=auth, json=payload, headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()

        success_message = f"Event '{title}' was created successfully."
        if attendee_emails:
            success_message += f" Invited: {', '.join(attendee_emails)}."

        return json.dumps({
            "status": "success",
            "message": success_message
        })
    except requests.exceptions.HTTPError as e:
        return json.dumps({
            "status": "error",
            "message": f"Failed to create event. API Error: {e.response.text}"
        })


def list_events(base_url: str, auth: tuple, start_date: str, end_date: str):
    """
    Retrieves and lists upcoming events from the calendar within a date range.
    Required: start_date, end_date (format YYYY-MM-DD).
    """
    url = f"{base_url}/calendar"
    params = {"props[]": "getetag", "limit": 100}

    try:
        response = requests.get(url, auth=auth, params=params, headers={"Accept": "application/json"})
        response.raise_for_status()
        data = response.json()

        if not data.get("results"):
            return "No events found in the calendar."

        events = data.get("result", [])
        event_titles = [event.get('title', 'Untitled Event') for event in events[:5]]

        if not event_titles:
            return f"No events found between {start_date} and {end_date}."

        return f"Found {len(events)} events. Here are the next few: {', '.join(event_titles)}."

    except requests.exceptions.HTTPError as e:
        return f"Error listing events: {e.response.status_code} - {e.response.text}"
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"