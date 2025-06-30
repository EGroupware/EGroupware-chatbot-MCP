# tool.Dockerfile

# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Prevent Python from writing .pyc files to disc
ENV PYTHONDONTWRITEBYTECODE 1
# Ensure Python output is sent straight to the terminal
ENV PYTHONUNBUFFERED 1

# Copy the requirements file into the container
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code for the tool server
COPY ./tool_server ./tool_server


# Expose the port the app runs on
EXPOSE 8001

# The command to run the application
CMD ["uvicorn", "tool_server.main:app", "--host", "0.0.0.0", "--port", "8001"]