import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ValidationError
from typing import Any, Dict, Optional

from .tools import addressbook, calendar, infolog, knowledge
from dotenv import load_dotenv
load_dotenv()


import os
from fastapi import FastAPI, HTTPException

app = FastAPI(
    title="EGroupware Tool Server",
    description="An MCP-compliant server that exposes EGroupware tools.",
    version="1.0.0",
)

EGROUPWARE_BASE_URL = os.getenv("EGROUPWARE_BASE_URL")


class AuthPayload(BaseModel):
    username: str
    password: str


class CreateContactArgs(BaseModel):
    full_name: str
    email: str
    phone: Optional[str] = None
    company: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None


class SearchContactsArgs(BaseModel):
    query: str


class CreateEventArgs(BaseModel):
    title: str
    start_datetime: str
    duration_minutes: Optional[int] = 60
    description: Optional[str] = None
    location: Optional[str] = None


class ListEventsArgs(BaseModel):
    start_date: str
    end_date: str


class CreateTaskArgs(BaseModel):
    title: str
    due_date: Optional[str] = None
    description: Optional[str] = None


class ExecuteToolRequest(BaseModel):
    auth: AuthPayload
    args: Dict[str, Any]


tool_registry = {
    "create_contact": (addressbook.create_contact, CreateContactArgs),
    "search_contacts": (addressbook.search_contacts, SearchContactsArgs),
    "create_event": (calendar.create_event, CreateEventArgs),
    "list_events": (calendar.list_events, ListEventsArgs),
    "create_task": (infolog.create_task, CreateTaskArgs),
    "get_about_us_info": (knowledge.get_about_us_info, None),
}


@app.post("/execute/{tool_name}")
def execute_tool(tool_name: str, request: ExecuteToolRequest):
    if not EGROUPWARE_BASE_URL:
        raise HTTPException(status_code=500, detail="EGROUPWARE_BASE_URL not configured on the Tool Server.")

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
        if tool_name == "get_about_us_info":
            result = tool_function()
        else:
            result = tool_function(base_url=EGROUPWARE_BASE_URL, auth=user_auth, **args_dict)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500,
                            detail=f"An unexpected error occurred executing tool '{tool_name}': {str(e)}")


@app.get("/", summary="Health Check")
def read_root():
    return {"status": "EGroupware Tool Server is running", "available_tools": list(tool_registry.keys())}