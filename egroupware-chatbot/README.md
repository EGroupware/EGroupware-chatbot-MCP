# EGroupware AI Chatbot (MCP Architecture)

This project provides a self-hosted AI chatbot designed to interact with an EGroupware instance, refactored into a true Model-Context-Protocol (MCP) inspired architecture. It features two distinct microservices:

1.  **Agent Service**: The "brain" of the operation. It handles the user-facing chat interface, manages authentication, communicates with the Large Language Model (LLM), and orchestrates which tools to use.
2.  **Tool Server**: The "hands" of the operation. It's a dedicated, secure API server that exposes the EGroupware functions (like creating contacts or events) as tools. It knows nothing about AI and simply executes commands on behalf of the Agent.

This microservices architecture makes the system more robust, scalable, and easier to maintain.

## Features

- **Secure Authentication**: Users log in with their EGroupware username and password. Sessions are managed by the Agent Service using JWTs.
- **MCP-Style Architecture**: Clean separation between the AI agent and the tools it uses.
- **AI-Powered Agent**: Utilizes the `meta-llama/Llama-3.3-70B-Instruct` model via the IONOS API to understand user requests.
- **Dedicated Tool Server**: Exposes a clear, versionable API for EGroupware functions.
  - **Address Book**: Create/search contacts.
  - **Calendar**: Create/list events.
  - **Task Management (InfoLog)**: Create tasks.
  - **Knowledge Retrieval**: Fetches company info from a Google Doc.
- **Streaming Responses**: Chat responses are streamed in real-time for a smooth user experience.

## Setup and Installation

### 1. Prerequisites

- Python 3.9+
- An EGroupware instance with API access.
- An IONOS account with access to the AI API.
- A Google Cloud project with the Google Docs API enabled and a service account.

### 2. Clone & Setup

(Instructions for cloning, setting up Google credentials, and installing dependencies are the same as before.)

### 3. Configure Environment Variables

Create a `.env` file from the `.env.example` template. The `TOOL_SERVER_URL` is new and crucial for connecting the two services.

```ini
# .env
IONOS_API_KEY="your_ionos_api_key"
IONOS_API_BASE_URL="https://openai.inference.de-txl.ionos.com/v1"
EGROUPWARE_BASE_URL="https://amir.egroupware.net/egw/groupdav.php/sysop"
JWT_SECRET_KEY="a_very_secret_and_long_random_string"
GOOGLE_DOC_ID="your_google_doc_id"
TOOL_SERVER_URL="http://127.0.0.1:8001"