# tool_server/tools/infolog.py

import requests
import json
from typing import Optional
import re


def create_task(
        base_url: str,
        auth: tuple,
        title: str,
        due_date: Optional[str] = None,  # Expects YYYY-MM-DD format from the user
        description: Optional[str] = None
):
    """
    Creates a new task in the user's personal InfoLog using the EGroupware REST API.
    """
    username = auth[0]
    # Dynamically construct the correct URL for the authenticated user's InfoLog
    user_specific_base_url = re.sub(r'/(sysop|[^/]+)$', f'/{username}', base_url.rstrip('/'))
    url = f"{user_specific_base_url}/infolog/"

    # --- Construct the payload based STRICTLY on the REST API documentation ---
    payload = {
        "title": title,
        "status": "needs-action"  # Set a sensible default for all new tasks
    }

    # Add optional fields only if they have values
    if description:
        payload["description"] = description

    if due_date:
        # The API expects a 'due' field with a date and time.
        # If the user only provides a date, we'll default to the end of that day.
        payload["due"] = f"{due_date} 23:59:59"

    try:
        response = requests.post(
            url, auth=auth, json=payload, headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()

        # Construct a clear success message for the LLM
        success_message = f"Task '{title}' was created successfully in your InfoLog."
        if due_date:
            success_message += f" It is due on {due_date}."

        return json.dumps({
            "status": "success",
            "message": success_message,
            "created_task_details": payload
        })
    except requests.exceptions.HTTPError as e:
        error_text = e.response.text
        return json.dumps({
            "status": "error",
            "message": f"Failed to create the task. The server responded with an error: {error_text}"
        })