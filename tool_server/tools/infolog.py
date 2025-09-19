import requests
import json
from typing import Optional
import re


def list_tasks(base_url: str, auth: tuple, status: Optional[str] = None, limit: int = 50):
    """
    Retrieve a list of tasks from the user's InfoLog.
    """
    url = f"{base_url}/infolog/"
    try:
        params = {}
        if status:
            params['status'] = status
        response = requests.get(url, auth=auth, params=params, headers={"Accept": "application/json"})
        response.raise_for_status()
        data = response.json()

        # Extract items - EGroupware returns a 'responses' mapping similar to calendar
        responses = data.get('responses', {}) if isinstance(data, dict) else {}
        tasks = []
        for _, t in responses.items():
            if not t or not isinstance(t, dict):
                continue
            tasks.append({
                'id': t.get('id') or t.get('uid'),
                'title': t.get('title'),
                'description': t.get('description'),
                'due': t.get('due'),
                'status': t.get('status')
            })
            if len(tasks) >= limit:
                break
        return json.dumps(tasks)
    except requests.exceptions.HTTPError as e:
        return json.dumps({
            "status": "error",
            "message": f"API Error: {e.response.status_code} - {e.response.text}"
        })
    except Exception as e:
        return json.dumps({"status": "error", "message": f"Unexpected error: {str(e)}"})


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
    url = f"{base_url}/infolog/"

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