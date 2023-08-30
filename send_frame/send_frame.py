import cv2
import requests
import numpy as np
import queue
import threading
import time
import datetime
import logging
import os
from fastapi import FastAPI, File, UploadFile, HTTPException

app = FastAPI()  # Create an instance of the FastAPI class

# Define the Node-RED endpoint URL using an environment variable
node_red_endpoint = os.getenv('NODE_RED_ENDPOINT')

# Define the heartbeat endpoint URL using an environment variable
heartbeat_endpoint = os.getenv('HEARTBEAT_ENDPOINT')

# Define the save path using an environment variable
save_path = os.getenv('SAVE_PATH')

# Define the campera IP using an environment variable
camera_ip = os.getenv('CAMERA_ENDPOINT')

# Define the equipment name to put in the saved frame
equipment = os.getenv('EQUIPMENT')

# Configure the logging
logging.basicConfig(level=logging.INFO)  # You can adjust the logging level as needed

# URL of the API
api_url = 'http://process_frame:8000/process_frame'

class VideoCapture:
    def __init__(self, url):
        self.url = url
        self.connect()
        self.q = queue.Queue(maxsize=10)
        t = threading.Thread(target=self._reader)
        t.daemon = True
        t.start()

    def connect(self):
        self.cap = cv2.VideoCapture(self.url)
        if not self.cap.isOpened():
            logging.error("Failed to connect to the camera.")

    def reconnect(self):
        self.cap.release()
        self.connect()
        if self.cap.isOpened():
            logging.info("Successfully reconnected to the camera.")
        else:
            logging.error("Failed to reconnect to the camera.")

    def release(self):
        if self.cap is not None:
            self.cap.release()

    def _reader(self):
        while True:
            ret, frame = self.cap.read()
            if not ret:
                logging.critical("Camera disconnected. Attempting to reconnect.")
                self.reconnect()
                time.sleep(5)  # Wait for 5 seconds before attempting to read again
                continue  # Skips the rest of the loop and jumps to the next iteration
            if not self.q.empty():
                try:
                    self.q.get_nowait()   # discard previous (unprocessed) frame
                except queue.Empty:
                    pass
            self.q.put((ret, frame))

    def read(self):
        return self.q.get()
    
cap = VideoCapture(camera_ip)

def send_to_node_red(scores):

    # Send the scores to Node-RED
    try:
        response = requests.post(node_red_endpoint, json={'scores': scores}, timeout=3)
        response.close()  # make sure to close the connection after the request is made
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to send data to Node-RED: {e}")

# Function to send heartbeat to Node-RED
def send_heartbeat_to_node_red(heartbeat):

    # Send the heartbeat to Node-RED
    try:
        response = requests.post(heartbeat_endpoint, json={'heartbeat': heartbeat}, timeout=3)
        response.close()  # make sure to close the connection after the request is made
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to send heartbeat to Node-RED: {e}")

# Define the heartbeat interval in seconds
heartbeat_interval = 60

# Initialize the heartbeat variables
last_heartbeat_time = time.time()

# Function to send heartbeat to Node-RED
def send_heartbeat():
    global last_heartbeat_time
    # Check if it's time to send a heartbeat
    current_time = time.time()
    if current_time - last_heartbeat_time >= heartbeat_interval:
        # Send the heartbeat to Node-RED
        send_heartbeat_to_node_red(1)
        last_heartbeat_time = current_time

def process_frames():
    global cap
    while True:
        ret, frame = cap.read()
        if not ret:
            logging.critical("Failed to read a frame. Skipping this iteration.")
            time.sleep(5)
            continue

        # Send heartbeat to Node-RED
        send_heartbeat()

        # Convert the frame to bytes
        _, image_bytes = cv2.imencode('.jpg', frame)
        image_bytes = image_bytes.tobytes()

        # Send the image as a POST request
        response = requests.post(api_url, files={'file': image_bytes})

        # Check the response
        if response.status_code == 200:
            result = response.json()

            # Check if detection scores are present in the response
            if 'detection_scores' in result:
                detection_scores = result['detection_scores']
                if detection_scores:
                    logging.info("Detection Scores:")
                    logging.info(detection_scores)  # Log all detection scores as an array
                    # Send results to Node-RED as a single array
                    send_to_node_red(detection_scores)
                else:
                    logging.info("No detection scores returned.")
            else:
                logging.critical("No detection scores in the response.")
        else:
            logging.error(f"Failed with status code: {response.status_code}")

        # Introduce a 1-second delay before reading the next frame
        time.sleep(1)

# Start processing frames
threading.Thread(target=process_frames).start()


# Define an endpoint to save the current frame
@app.post('/save_current_frame', response_model=dict)
async def save_current_frame():
    try:
        current_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{save_path}{equipment}_{current_time}.jpg"  # Use the mounted volume path

        ret, frame = cap.read()
        cv2.imwrite(filename, frame)

        return {'status': 'success'}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
