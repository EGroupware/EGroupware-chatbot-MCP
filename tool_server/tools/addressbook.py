import requests
import json
from typing import Optional


def create_contact(base_url: str, auth: tuple, full_name: str, email: str,
                   phone: Optional[str] = None, company: Optional[str] = None,
                   address: Optional[str] = None, notes: Optional[str] = None):
    """
    CREATE CONTACT TOOL
    Adds a new contact to the EGroupware address book.
    """
    url = f"{base_url}/addressbook/"
    name_parts = full_name.split()
    first_name, last_name = (name_parts[0], " ".join(name_parts[1:])) if len(name_parts) > 1 else (full_name, "")

    payload = {"fullName": full_name, "name/given": first_name, "name/surname": last_name, "emails/work": email}
    if company: payload["organizations/org/name"] = company
    if phone: payload["phones/tel_work"] = phone
    if address: payload["addresses/work/street"] = address
    if notes: payload["notes/note"] = notes

    try:
        response = requests.post(url, auth=auth, json=payload, headers={"Content-Type": "application/json"})
        response.raise_for_status()
        # --- IMPROVED RETURN ---
        # Be very explicit about the outcome.
        return json.dumps(
            {"status": "success", "message": f"Contact for {full_name} with email {email} was created successfully."})
    except requests.exceptions.HTTPError as e:
        error_details = e.response.text
        # --- IMPROVED RETURN ---
        return json.dumps({"status": "error",
                           "message": f"Failed to create contact. The server responded with status {e.response.status_code} and details: {error_details}"})


def search_contacts(base_url: str, auth: tuple, query: str):
    """
    Searches for existing contacts by name or email.
    """
    url = f"{base_url}/addressbook/"
    params = {"filters[search]": query, "props[]": ["fullName", "email"]}  # Ask for more details
    try:
        response = requests.get(url, auth=auth, params=params, headers={"Accept": "application/json"})
        response.raise_for_status()
        data = response.json()

        results = data.get("result", [])
        if not results:
            # --- IMPROVED RETURN ---
            return json.dumps({"status": "success", "found": False, "message": "No contacts found matching the query."})

        # --- IMPROVED RETURN ---
        return json.dumps({
            "status": "success",
            "found": True,
            "count": len(results),
            "contacts": results[:5]  # Return a sample of the data
        })
    except requests.exceptions.HTTPError as e:
        return json.dumps({"status": "error",
                           "message": f"Failed to search contacts. Server responded with status {e.response.status_code}."})