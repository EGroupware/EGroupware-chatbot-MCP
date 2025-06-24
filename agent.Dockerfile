# agent.tool.Dockerfile

# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Prevent Python from writing .pyc files to disc
ENV PYTHONDONTWRITEBYTECODE 1
# Ensure Python output is sent straight to the terminal
ENV PYTHONUNBUFFERED 1

# Install system dependencies if any (none needed for now)
# RUN apt-get update && apt-get install -y ...

# Copy the requirements file into the container
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code into the container
# This includes the agent_service and the static files
COPY ./agent_service ./agent_service
COPY ./static ./static


# Expose the port the app runs on
EXPOSE 8000

# The command to run the application
# Note: We don't use --reload in production.
CMD ["uvicorn", "agent_service.main:app", "--host", "0.0.0.0", "--port", "8000"]