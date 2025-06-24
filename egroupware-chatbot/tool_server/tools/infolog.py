import requests
import json
from datetime import datetime
from typing import Optional

def create_task(base_url: str, auth: tuple, title: str,
                due_date: Optional[str] = None, description: Optional[str] = None):
    """
    Creates a new task in the EGroupware InfoLog.
    Required: title.
    Optional: due_date (YYYY-MM-DD), description.
    """
    url = f"{base_url}/infolog/"

    payload = {
        "@type": "Task",
        "title": title,
        "created": datetime.utcnow().isoformat() + "Z",
        "status": "confirmed",
        "progress": "needs-action",
        "egroupware.org:type": "task" # Custom field for EGroupware
    }
    if due_date:
        payload["due"] = f"{due_date}T23:59:59" # Assume end of day
    if description:
        payload["description"] = description

    try:
        response = requests.post(url, auth=auth, json=payload, headers={"Content-Type": "application/json"})
        response.raise_for_status()
        return f"Successfully created task: '{title}'."
    except requests.exceptions.HTTPError as e:
        return f"Error creating task: {e.response.status_code} - {e.response.text}"
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"