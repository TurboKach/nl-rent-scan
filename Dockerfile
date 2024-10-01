# Use an official Python runtime as a base image
FROM python:3.12.7-slim

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy the requirements file into the container
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container
COPY . .

# Set environment variables (if any) through Docker CLI or docker-compose.yml
# Example: ENV TELEGRAM_BOT_TOKEN=<your-token>

# Command to run your app
CMD ["python", "main.py"]
