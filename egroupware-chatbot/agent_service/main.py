import json
import os
from datetime import timedelta
from typing import AsyncGenerator
import requests

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles

from . import auth, llm_service, prompts, schemas

load_dotenv()

app = FastAPI(title="EGroupware Agent Service")
app.mount("/static", StaticFiles(directory="static"), name="static")

chat_histories = {}
TOOL_SERVER_URL = os.getenv("TOOL_SERVER_URL")


def call_tool_server(tool_name: str, args: dict, user_credentials: schemas.TokenData):
    if not TOOL_SERVER_URL:
        return "Error: Tool Server URL is not configured."

    url = f"{TOOL_SERVER_URL}/execute/{tool_name}"
    payload = {"auth": user_credentials.dict(), "args": args}

    try:
        response = requests.post(url, json=payload, timeout=20)
        response.raise_for_status()
        return response.json().get("result", "Tool executed but returned no result.")
    except requests.exceptions.HTTPError as e:
        try:
            error_detail = e.response.json().get("detail", e.response.text)
        except json.JSONDecodeError:
            error_detail = e.response.text
        return f"Error from Tool Server for '{tool_name}': {error_detail}"
    except requests.exceptions.RequestException as e:
        return f"Error connecting to the Tool Server: {e}"


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def read_login():
    with open("static/login.html") as f:
        return HTMLResponse(content=f.read())


@app.get("/chat-ui", response_class=HTMLResponse, include_in_schema=False)
async def read_chat_ui():
    with open("static/index.html") as f:
        return HTMLResponse(content=f.read())


@app.post("/token", response_model=schemas.Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    if not auth.verify_egroupware_credentials(form_data.username, form_data.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")

    token = auth.create_access_token(data={"sub": form_data.username, "pwd": form_data.password})
    return {"access_token": token, "token_type": "bearer"}


async def chat_stream_generator(message: str, current_user: schemas.TokenData) -> AsyncGenerator[str, None]:
    if current_user.username not in chat_histories:
        chat_histories[current_user.username] = [{"role": "system", "content": prompts.get_system_prompt()}]
    chat_histories[current_user.username].append({"role": "user", "content": message})

    tool_definitions = [
        {"type": "function",
         "function": {"name": "create_contact", "description": "Adds a new contact to the EGroupware address book.",
                      "parameters": {"type": "object",
                                     "properties": {"full_name": {"type": "string"}, "email": {"type": "string"},
                                                    "phone": {"type": "string"}, "company": {"type": "string"},
                                                    "address": {"type": "string"}, "notes": {"type": "string"}},
                                     "required": ["full_name", "email"]}}},
        {"type": "function",
         "function": {"name": "search_contacts", "description": "Searches for existing contacts by name or email.",
                      "parameters": {"type": "object", "properties": {"query": {"type": "string"}},
                                     "required": ["query"]}}},
        {"type": "function",
         "function": {"name": "create_event", "description": "Schedules a new event in the calendar.",
                      "parameters": {"type": "object", "properties": {"title": {"type": "string"},
                                                                      "start_datetime": {"type": "string",
                                                                                         "description": "ISO format like '2024-08-15T14:00:00'"},
                                                                      "duration_minutes": {"type": "integer"},
                                                                      "description": {"type": "string"},
                                                                      "location": {"type": "string"}},
                                     "required": ["title", "start_datetime"]}}},
        {"type": "function", "function": {"name": "list_events", "description": "Lists upcoming events.",
                                          "parameters": {"type": "object", "properties": {
                                              "start_date": {"type": "string", "description": "YYYY-MM-DD"},
                                              "end_date": {"type": "string", "description": "YYYY-MM-DD"}},
                                                         "required": ["start_date", "end_date"]}}},
        {"type": "function", "function": {"name": "create_task", "description": "Creates a new task in InfoLog.",
                                          "parameters": {"type": "object", "properties": {"title": {"type": "string"},
                                                                                          "due_date": {"type": "string",
                                                                                                       "description": "YYYY-MM-DD"},
                                                                                          "description": {
                                                                                              "type": "string"}},
                                                         "required": ["title"]}}},
        {"type": "function",
         "function": {"name": "get_about_us_info", "description": "Fetches company info from a document.",
                      "parameters": {"type": "object", "properties": {}}}},
    ]

    stream = llm_service.get_streaming_chat_response(chat_histories[current_user.username], tool_definitions)

    tool_calls, full_response = [], ""
    for chunk in stream:
        delta = chunk.choices[0].delta
        if delta and delta.content:
            full_response += delta.content
            yield f"data: {json.dumps({'type': 'token', 'content': delta.content})}\n\n"
        elif delta and delta.tool_calls:
            for tc_chunk in delta.tool_calls:
                if len(tool_calls) <= tc_chunk.index:
                    tool_calls.append({"id": "", "type": "function", "function": {"name": "", "arguments": ""}})
                tc = tool_calls[tc_chunk.index]
                if tc_chunk.id: tc["id"] = tc_chunk.id
                if tc_chunk.function.name: tc["function"]["name"] = tc_chunk.function.name
                if tc_chunk.function.arguments: tc["function"]["arguments"] += tc_chunk.function.arguments

    if full_response: chat_histories[current_user.username].append({"role": "assistant", "content": full_response})

    if tool_calls:
        chat_histories[current_user.username].append({"role": "assistant", "tool_calls": tool_calls})
        for tool_call in tool_calls:
            name, args = tool_call["function"]["name"], json.loads(tool_call["function"]["arguments"])
            yield f"data: {json.dumps({'type': 'tool_call', 'tool_name': name})}\n\n"
            response = call_tool_server(tool_name=name, args=args, user_credentials=current_user)
            yield f"data: {json.dumps({'type': 'tool_result', 'result': str(response)})}\n\n"
            chat_histories[current_user.username].append(
                {"tool_call_id": tool_call["id"], "role": "tool", "name": name, "content": str(response)})

        second_stream = llm_service.get_streaming_chat_response(chat_histories[current_user.username], tool_definitions)
        second_response = ""
        for chunk in second_stream:
            if chunk.choices[0].delta and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                second_response += content
                yield f"data: {json.dumps({'type': 'token', 'content': content})}\n\n"
        if second_response: chat_histories[current_user.username].append(
            {"role": "assistant", "content": second_response})

    yield "event: end\ndata: {}\n\n"


@app.get("/chat")
async def chat_endpoint(message: str, token: str):
    current_user = await auth.get_current_user(token)
    return StreamingResponse(chat_stream_generator(message, current_user), media_type="text/event-stream")