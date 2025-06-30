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

## Prerequisites

- Docker and Docker Compose
- An EGroupware instance with valid credentials
- IONOS API key for AI services
- OpenAI API key (optional, for fallback)

## Quick Start with Docker

1. Clone the repository:
```bash
git clone https://github.com/amirdhs/EGroupware-chatbot-MCP.git
cd egroupware-chatbot-MCP
```

2. Set up environment variables:
```bash
cp .env.example .env
```
Edit the `.env` file and fill in your credentials:
- `IONOS_API_KEY`: Your IONOS API key
- `OPENAI_API_KEY`: Your OpenAI API key (optional)
- `EGROUPWARE_BASE_URL`: Your EGroupware instance URL
- `JWT_SECRET_KEY`: Generate using `openssl rand -hex 32`

3. Build and start the Docker containers:
```bash
docker-compose up --build
```

The services will be available at:
- Web Interface: http://localhost:8000
- Tool Server API: http://localhost:8001

## Architecture Overview

```
┌─────────────────┐      ┌──────────────┐
│   Web Client    │──────▶  Agent Service│
└─────────────────┘      │   (Port 8000)│
                         └───────┬───────┘
                                 │
                                 ▼
                         ┌──────────────┐
                         │ Tool Server  │
                         │  (Port 8001) │
                         └──────────────┘
```

## Usage

1. Access the web interface at http://localhost:8000
2. Log in with your EGroupware credentials
3. Start chatting! The bot can help with:
   - Managing contacts in the address book
   - Creating and viewing calendar events
   - Creating tasks
   - Accessing company knowledge base

## Available Commands

The chatbot understands natural language requests such as:
- "Create a new contact for John Doe"
- "Schedule a meeting tomorrow at 2 PM"
- "Create a task for the marketing team"
- "What is EGroupware's mission?"

## Development

### Local Development Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run services separately:
```bash
# Terminal 1: Run Agent Service
python -m agent_service.main

# Terminal 2: Run Tool Server
python -m tool_server.main
```

### Project Structure

- `agent_service/`: Main chatbot service with LLM integration
- `tool_server/`: EGroupware integration API
- `static/`: Web interface files
- `docker-compose.yml`: Docker services configuration
- `.env`: Environment configuration

## Troubleshooting

1. **Connection Issues**
   - Verify your EGroupware instance is accessible
   - Check if your API keys are valid
   - Ensure all environment variables are properly set

2. **Authentication Problems**
   - Confirm your EGroupware credentials
   - Check if JWT_SECRET_KEY is properly set
   - Verify the EGROUPWARE_BASE_URL format

3. **Docker Issues**
   - Run `docker-compose down -v` to clean up
   - Check Docker logs: `docker-compose logs`
   - Ensure ports 8000 and 8001 are available

## Security Notes

- All sensitive data should be stored in the `.env` file
- Never commit the `.env` file to version control
- Regularly rotate the JWT_SECRET_KEY
- Keep your API keys secure

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

[Insert License Information]
