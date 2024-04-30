# Use an official Python runtime as a parent image
FROM python:3.11.4-slim

# Create and set the working directory
WORKDIR /app

# Copy the current directory contents into the container at /usr/src/app
COPY . .

# Install any needed packages specified in requirements.txt
RUN pip install aiohttp

# Make port 5000 available to the world outside this container
EXPOSE 5000

# Define environment variable
ENV NAME Gateway

# Command to run the application
CMD ["python", "gateway.py"]
