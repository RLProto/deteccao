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
from opcua import ua, Client
import random

app = FastAPI()  # Create an instance of the FastAPI class

# Define the Node-RED endpoint URL using an environment variable
node_red_endpoint = os.getenv('NODE_RED_ENDPOINT')
node_red_endpoint = 'http://192.168.137.1:1880/endpointG1'

# Define the heartbeat endpoint URL using an environment variable
heartbeat_endpoint = os.getenv('HEARTBEAT_ENDPOINT')
heartbeat_endpoint = 'http://192.168.137.1:1880/heartbeatG1'

# Define the save path using an environment variable
save_path = os.getenv('SAVE_PATH')

# Define the campera IP using an environment variable
camera_ip = os.getenv('CAMERA_ENDPOINT')
camera_ip = "rtsp://teste:Ambev123@192.168.137.109:554/cam/realmonitor?channel=1&subtype=0"

# Define the equipment name to put in the saved frame
equipment = os.getenv('EQUIPMENT')
equipment= 'G3'

# Configure the logging
logging.basicConfig(level=logging.INFO)  # You can adjust the logging level as needed

# Define constants for backoff and retries
#max_retries = int(os.getenv('MAX_RETRIES'))
max_retries = 5
#backoff_factor = float(os.getenv('BACKOFF_FACTOR'))
backoff_factor = 2

# URL of the API
api_url = 'http://process_frame:8000/process_frame'
api_url = 'http://192.168.137.1:8000/process_frame'

server_url = 'opc.tcp://10.18.12.185:49324'
tag_path = "ns=2;s=PROCESSO.PLC.GERMINACAO.CAM_DETECT_G4"
#tag_path = "ns=2;s=COLETA_DADOS.Device1.GERMINACAO.CAM_DETECT_TESTE"
last_true_write_time = 0

class OPCUAConnector:
    _instance = None  # This will hold the singleton instance

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(OPCUAConnector, cls).__new__(cls)
        return cls._instance

    def __init__(self, server_url, tag_path):
        if hasattr(self, 'initialized'):
            # Prevent reinitialization
            return
        self.server_url = server_url
        self.tag_path = tag_path
        self.client = Client(server_url)
        self.connected = False
        self.initialized = True  # Set an initialization flag
    
    def reconnect(self):
        if self.connected:
            self.disconnect()
        self.connect()
    
    def connect(self):
        try:
            self.client.connect()
            self.connected = True
            logging.info("Connected to OPC UA server.")
            return True
        except Exception as e:
            logging.error(f"Failed to connect to OPC UA server: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        try:
            self.client.disconnect()
            logging.info("Disconnected from OPC UA server.")
        except Exception as e:
            logging.error(f"Failed to disconnect properly: {e}")
        finally:
            self.connected = False
    
    def send_data(self, value):
        if not self.connected:
            logging.info("Not connected to OPC UA Server, attempting to reconnect...")
            self.reconnect()
            if not self.connected:
                logging.error("Failed to reconnect to OPC UA Server. Aborting write operation.")
                return
        
        try:
            opc_tag = self.client.get_node(tag_path)
            data_value = ua.DataValue(ua.Variant(value, ua.VariantType.Boolean))
            opc_tag.set_attribute(ua.AttributeIds.Value, data_value)
            
            logging.info(f"Successfully wrote {value} to OPC UA.")
        except Exception as e:
            logging.error(f"Error writing to OPC UA: {e}")
            self.connected = False  # Mark as disconnected to trigger a reconnect on next try

# Usage
connector = OPCUAConnector(server_url, tag_path)

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
        response = requests.post(node_red_endpoint, json={'detections': scores}, timeout=3)
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

# Function to send a frame to the API with retry and backoff mechanism
def send_frame_to_api(image_bytes, equipment, retries=max_retries):
    for attempt in range(retries):
        try:
            response = requests.post(api_url, data={'equipment': equipment}, files={'file': image_bytes}, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                logging.error(f"Failed with status code: {response.status_code}")
        except (requests.exceptions.RequestException) as e:
            if attempt < retries - 1:
                wait_time = exponential_backoff(attempt)
                logging.warning(f"API connection failed. Retrying in {wait_time:.2f} seconds...")
                time.sleep(wait_time)
                continue
            else:
                logging.error(f"Failed to connect to the API after {retries} attempts.")
                return None

# Function to perform exponential backoff
def exponential_backoff(attempt):
    return backoff_factor * (2 ** attempt) + random.uniform(0, 0.1 * (2 ** attempt))

# Define the process_frames function to process video frames
def process_frames():
    global cap,last_true_write_time

    while True:
        # Attempt to read a frame from the video source
        ret, frame = cap.read()
        current_time = time.time()
        if not ret:
            # If reading the frame fails, log an error and wait for 5 seconds before the next attempt
            logging.critical("Failed to read a frame. Skipping this iteration.")
            time.sleep(5)
            continue

        # Send a heartbeat signal to Node-RED to indicate the system is active
        send_heartbeat()

        # Convert the frame to JPEG format and get its bytes
        _, image_bytes = cv2.imencode('.jpg', frame)
        image_bytes = image_bytes.tobytes()

        # Send the frame to the API and handle the response
        result = send_frame_to_api(image_bytes, equipment)
        if result:
            # Check if there are detection scores in the response
            detection_scores = result.get('detection_scores', [])
            if detection_scores:
                # Log the detection scores
                logging.info(detection_scores)
                # Send the detection scores to Node-RED
                send_to_node_red(detection_scores)

                current_time = time.time()
                if any(d['score'] > 0.8 for d in detection_scores if 'score' in d) and current_time - last_true_write_time >= 10:
                    connector.send_data(True)
                    last_true_write_time = current_time
                    # Schedule writing False after 10 seconds without blocking the main thread
                    threading.Timer(10, lambda: connector.send_data(False)).start()

            else:
                # If there are no detection scores in the response, log it
                logging.info("No detection scores returned.")
        else:
            # If the frame processing fails, log an error
            logging.error("Failed to process frame data.")

        # Introduce a delay before reading the next frame
        time.sleep(2)

# Start processing frames in a separate thread
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
