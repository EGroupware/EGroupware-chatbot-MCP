import requests
import json
from datetime import datetime, timedelta
from typing import Optional


def create_event(base_url: str, auth: tuple, title: str, start_datetime: str,
                 duration_minutes: Optional[int] = 60, description: Optional[str] = None,
                 location: Optional[str] = None):
    """
    Schedules a new event in the EGroupware calendar.
    Required: title, start_datetime (ISO format like '2024-08-15T14:00:00').
    Optional: duration_minutes (default 60), description, location.
    """
    url = f"{base_url}/calendar"

    # ISO 8601 duration format, e.g., PT60M for 60 minutes
    duration_iso = f"PT{duration_minutes}M"

    payload = {
        "@type": "Event",
        "title": title,
        "start": start_datetime,
        "duration": duration_iso,
        "status": "confirmed",
        "privacy": "public"
    }
    if description:
        payload["description"] = description
    if location:
        payload["locations"] = {"loc-1": {"@type": "Location", "name": location}}

    try:
        response = requests.post(url, auth=auth, json=payload, headers={"Content-Type": "application/json"})
        response.raise_for_status()
        return f"Successfully created event '{title}' for {start_datetime}."
    except requests.exceptions.HTTPError as e:
        return f"Error creating event: {e.response.status_code} - {e.response.text}"
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"


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