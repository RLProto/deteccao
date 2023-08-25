# Use an official Python runtime as a parent image
FROM python:3.11.4-slim

# Create and set the working directory
WORKDIR /app

# Create a volume and specify its mount point
VOLUME /app/data

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install -r requirements.txt

# Define the command to run the application with uvicorn
CMD ["uvicorn", "send_frame:app", "--host", "0.0.0.0", "--port", "3001"]
