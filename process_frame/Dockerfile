# Use an official Python runtime as a parent image
FROM python:3.11.4-slim

# Install system dependencies, including required libraries
RUN apt-get update && apt-get install -y libgl1-mesa-glx libglib2.0-0

# Set the working directory to /app
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt /app/

# Install any needed packages specified in requirements.txt
RUN pip install --trusted-host pypi.python.org -r requirements.txt

# Copy the entire contents of the current directory into the container at /app
COPY . /app/

# Expose port 8000 for the FastAPI application
EXPOSE 8000

# Define the command to run the application
CMD ["uvicorn", "process_frame:app", "--host", "0.0.0.0", "--port", "8000"]
