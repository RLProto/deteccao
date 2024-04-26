import cv2
import requests
import logging
import os
import random
import time
from fastapi import FastAPI, HTTPException

app = FastAPI()  # Create an instance of the FastAPI class

# Define the API URL and equipment name
api_url = 'http://100.100.210.80:8000/process_frame'
equipment = 'G3'

# Configure the logging
logging.basicConfig(level=logging.INFO)

# Constants for backoff and retries
max_retries = 5
backoff_factor = 2

# Function to perform exponential backoff
def exponential_backoff(attempt):
    return backoff_factor * (2 ** attempt) + random.uniform(0, 0.1 * (2 ** attempt))

# Function to send a frame to the API with retry and backoff mechanism
def send_frame_to_api(image_bytes, equipment, retries=max_retries):
    for attempt in range(retries):
        try:
            response = requests.post(api_url, data={'equipment': equipment}, files={'file': image_bytes}, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                logging.error(f"Failed with status code: {response.status_code}")
        except requests.exceptions.RequestException as e:
            if attempt < retries - 1:
                wait_time = exponential_backoff(attempt)
                logging.warning(f"API connection failed. Retrying in {wait_time:.2f} seconds...")
                time.sleep(wait_time)
                continue
            else:
                logging.error(f"Failed to connect to the API after {retries} attempts.")
                return None

# Function to send a single frame from a file to the API
def send_frame_from_file(filepath):
    try:
        # Read the image from file
        frame = cv2.imread(filepath)
        if frame is not None:
            # Convert the frame to JPEG format and get its bytes
            _, image_bytes = cv2.imencode('.jpg', frame)
            image_bytes = image_bytes.tobytes()

            # Send the frame to the API and handle the response
            result = send_frame_to_api(image_bytes, equipment)
            if result:
                logging.info("Frame successfully processed by API.")
                return result
            else:
                logging.error("Failed to process frame data.")
        else:
            logging.error("Failed to read image from file.")
    except Exception as e:
        logging.error(f"An error occurred: {e}")

# Example usage, modify the filepath as needed
result = send_frame_from_file("C:\\Users\\Proto\\Desktop\\g3.jpg")
if result:
    print("Result from API:", result)
