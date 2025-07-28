import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ValidationError
from typing import Any, Dict, Optional , List

from .tools import addressbook, egw_calendar, infolog, knowledge, mail
# We still load env variables as fallback
from dotenv import load_dotenv
load_dotenv()

app = FastAPI(
    title="EGroupware Tool Server",
    description="An MCP-compliant server that exposes EGroupware tools.",
    version="1.0.0",
)


EGROUPWARE_BASE_URL = os.getenv("EGROUPWARE_BASE_URL")


class AuthPayload(BaseModel):
    username: str
    password: str
    egw_url: Optional[str] = None


class CreateContactArgs(BaseModel):
    full_name: str
    email: str
    phone: Optional[str] = None
    company: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None


class SearchContactsArgs(BaseModel):
    query: str


class GetAllContactsArgs(BaseModel):
    limit: Optional[int] = 50  # Default 50 contacts per page
    offset: Optional[int] = 0  # Start from beginning


class CreateEventArgs(BaseModel):
    title: str
    start_datetime: str # e.g., "2024-09-15T14:00:00"
    duration_minutes: Optional[int] = 60
    time_zone: Optional[str] = "UTC" # IANA Time Zone (e.g., "Europe/Berlin")
    description: Optional[str] = None
    location: Optional[str] = None
    attendee_emails: Optional[List[str]] = None # A list of email addresses
    priority: Optional[int] = 5

class ListEventsArgs(BaseModel):
    start_date: str
    end_date: str


class CreateTaskArgs(BaseModel):
    title: str
    due_date: Optional[str] = None
    description: Optional[str] = None

class SendEmailArgs(BaseModel):
    to: List[str]
    subject: str
    body: Optional[str] = None
    cc: Optional[List[str]] = None
    bcc: Optional[List[str]] = None

class ListEmailsArgs(BaseModel):
    query: Optional[str] = None
    limit: Optional[int] = 10

class ExecuteToolRequest(BaseModel):
    auth: AuthPayload
    args: Dict[str, Any]


tool_registry = {
    "create_contact": (addressbook.create_contact, CreateContactArgs),
    "search_contacts": (addressbook.search_contacts, SearchContactsArgs),
    "get_all_contacts": (addressbook.get_all_contacts, GetAllContactsArgs),
    "create_event": (egw_calendar.create_event, CreateEventArgs),
    "list_events": (egw_calendar.list_events, ListEventsArgs),
    "create_task": (infolog.create_task, CreateTaskArgs),
    "send_email": (mail.send_email, SendEmailArgs),
    "get_company_info": (knowledge.get_company_info, None),
}


@app.post("/execute/{tool_name}")
def execute_tool(tool_name: str, request: ExecuteToolRequest):
    # Use the URL provided in the auth payload if available, otherwise fall back to env variable
    base_url = request.auth.egw_url if hasattr(request.auth, "egw_url") and request.auth.egw_url else EGROUPWARE_BASE_URL

    if not base_url:
        raise HTTPException(status_code=500, detail="EGROUPWARE_BASE_URL not configured on the Tool Server or in the request.")

    if tool_name not in tool_registry:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found.")

    tool_function, args_model = tool_registry[tool_name]

    try:
        if args_model:
            validated_args = args_model(**request.args)
            args_dict = validated_args.dict(exclude_unset=True)
        else:
            args_dict = {}
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=f"Invalid arguments for {tool_name}: {e}")

    try:
        user_auth = (request.auth.username, request.auth.password)
        if tool_name == "get_company_info":
            result = tool_function()
        else:
            result = tool_function(base_url=base_url, auth=user_auth, **args_dict)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500,
                            detail=f"An unexpected error occurred executing tool '{tool_name}': {str(e)}")


@app.get("/", summary="Health Check")
def read_root():
    return {"status": "EGroupware Tool Server is running", "available_tools": list(tool_registry.keys())}