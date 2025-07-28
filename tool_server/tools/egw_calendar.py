import requests
import json
from typing import Optional, List
from datetime import datetime, timezone
import uuid
import os
from dotenv import load_dotenv
from pathlib import Path



def create_event(
        base_url: str,
        auth: tuple,
        title: str,
        start_datetime: str,
        duration_minutes: int = 60,
        time_zone: str = "Europe/Berlin",
        description: Optional[str] = None,
        location: Optional[str] = None,
        attendee_emails: Optional[List[str]] = None,
        priority: int = 5
):
    """
    Schedules a new event in the user's personal EGroupware calendar,
    using the official EGroupware REST API format.
    """
    url = f"{base_url}/calendar/"

    # --- Participant Block Construction ---
    participants = {}
    participant_key_counter = 1

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

    # --- Payload Construction according to JSCalendar specification ---
    payload = {
        "title": title,
        "start": start_datetime,
        "timeZone": time_zone,
        "duration": f"PT{duration_minutes}M",
        "participants": participants,
        "status": "confirmed",
        "priority": priority,
        "privacy": "public"
    }

    # Add optional fields
    if description:
        payload["description"] = description
    if location:
        payload["locations"] = {"loc-1": {"@type": "Location", "name": location}}

    # --- API Call and Response Handling ---
    try:
        response = requests.post(
            url,
            auth=auth,
            json=payload,
            headers={"Content-Type": "application/json"}
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
    Retrieves and lists events from the calendar.
    Uses the official EGroupware REST API format.
    """
    url = f"{base_url}/calendar/"

    try:
        response = requests.get(
            url,
            auth=auth,
            headers={"Accept": "application/json"}
        )
        response.raise_for_status()
        data = response.json()

        # Parse the responses structure as per EGroupware API
        responses = data.get("responses", {})
        if not responses:
            return json.dumps([])

        processed_events = []
        for event_path, event_data in responses.items():
            if event_data and isinstance(event_data, dict):
                # Filter events by date range if needed
                event_start = event_data.get("start", "")
                if event_start:
                    # Simple date filtering - extract date part
                    event_date = event_start.split("T")[0] if "T" in event_start else event_start
                    if start_date <= event_date <= end_date:
                        # Extract location from locations object
                        location_name = None
                        locations = event_data.get("locations", {})
                        if locations:
                            first_location = next(iter(locations.values()), {})
                            location_name = first_location.get("name")

                        processed_events.append({
                            "uid": event_data.get("uid"),
                            "title": event_data.get("title"),
                            "start": event_data.get("start"),
                            "duration": event_data.get("duration"),
                            "description": event_data.get("description"),
                            "location": location_name,
                            "status": event_data.get("status"),
                            "priority": event_data.get("priority")
                        })

        return json.dumps(processed_events)

    except requests.exceptions.HTTPError as e:
        return json.dumps({
            "status": "error",
            "message": f"API Error: {e.response.status_code} - {e.response.text}"
        })
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"An unexpected error occurred: {str(e)}"
        })
