import cv2
import asyncio
import websockets
import json
import threading
import time
import numpy as np
import logging

# Global variables

# For left stream
detections_left = []
last_detection_time_left = None
last_data_received_time_left = None  # Initialize this variable
frame_left = np.zeros((480, 640, 3), dtype=np.uint8)
frame_available_left = threading.Event()
camera_disconnected_left = threading.Event()
score_threshold = 0.7

# For right stream
detections_right = []
last_detection_time_right = None
last_data_received_time_right = None  # Initialize this variable
frame_right = np.zeros((480, 640, 3), dtype=np.uint8)
frame_available_right = threading.Event()
camera_disconnected_right = threading.Event()

# Common variables for both streams
blink_duration = 30  # seconds, set your desired blink duration
detection_timeout = 5  # seconds, set your desired detection timeout

# Global variables for button appearance
button_position_x = 0  # Adjust this based on your combined frame width
button_position_y = 0
button_width = 150
button_height = 26
button_color = (100, 100, 200)  # A pleasant blue
button_hover_color = (150, 150, 250)  # A lighter blue for hover effect
button_text = "Full Screen"
mouse_is_over_button = False  # Tracks whether the mouse is over the button

# Set the logging level for websockets.server to WARNING or higher
logging.getLogger('websockets.server').setLevel(logging.WARNING)
logging.basicConfig(level=logging.INFO)

# At the global scope, initialize last_blink_toggle_time_left
last_blink_toggle_time_left = time.time()
blink_state_left = False  # Initialize the blinking state for the left camera

# At the global scope, initialize last_blink_toggle_time_right
last_blink_toggle_time_right = time.time()
blink_state_right = False  # Initialize the blinking state for the right camera

blink_timer_start = time.time()  # Start a timer for blink management

# Add threading lock for synchronization
frame_lock_left = threading.Lock()
frame_lock_right = threading.Lock()

# Global variable initialization
last_frame_time_left = time.time()  # Initialize with the current time
last_frame_time_right = time.time()  # Initialize with the current time


async def detection_server_left(websocket, path):
    global detections_left, last_detection_time_left, last_data_received_time_left

    async for message in websocket:
        data = json.loads(message)
        last_data_received_time_left = time.time()

        if 'detections' in data and data['detections']:
            # Apply a score filter; only keep detections with a score above a certain threshold
            filtered_detections = [detection for detection in data['detections'] if 'score' in detection and detection['score'] > score_threshold]
            
            if filtered_detections:  # Check if there are any detections left after filtering
                detections_left = filtered_detections
                last_detection_time_left = time.time()  # Update last detection time only for valuable detections
            else:
                detections_left = []
        else:
            detections_left = []

async def detection_server_right(websocket, path):
    global detections_right, last_detection_time_right, last_data_received_time_right

    async for message in websocket:
        data = json.loads(message)
        last_data_received_time_right = time.time()

        if 'detections' in data and data['detections']:
            # Apply a score filter; only keep detections with a score above a certain threshold
            filtered_detections = [detection for detection in data['detections'] if 'score' in detection and detection['score'] > score_threshold]
            
            if filtered_detections:  # Check if there are any detections right after filtering
                detections_right = filtered_detections
                last_detection_time_right = time.time()  # Update last detection time only for valuable detections
            else:
                detections_right = []
        else:
            detections_right = []

async def start_websocket_server_left():
    port_left = 80 # Example port for left camera WebSocket
    async with websockets.serve(detection_server_left, "192.168.137.1", port_left):
        await asyncio.Future()  # Run forever

async def start_websocket_server_right():
    port_right = 8080  # Different port for right camera WebSocket
    async with websockets.serve(detection_server_right, "192.168.137.1", port_right):
        await asyncio.Future()  # Run forever

def update_blink_state():
    global blink_timer_start, blink_state_left, blink_state_right
    current_time = time.time()
    if (current_time - blink_timer_start) >= 1:  # Every 1 second
        blink_state_left = not blink_state_left
        blink_state_right = not blink_state_right
        blink_timer_start = current_time  # Reset the timer

def draw_uniform_border_with_lines(frame, border_color, border_thickness):
    height, width = frame.shape[:2]
    # Top border
    cv2.line(frame, (0, 0), (width, 0), border_color, border_thickness)
    # Bottom border
    cv2.line(frame, (0, height), (width, height), border_color, border_thickness)
    # Left border
    cv2.line(frame, (0, 0), (0, height), border_color, 2*border_thickness)
    # Right border
    cv2.line(frame, (width, 0), (width, height), border_color, 2*border_thickness)

def process_frame_left(frame_left_local):
    global detections_left, last_detection_time_left, last_data_received_time_left
    global blink_state_left, blink_timer_start, camera_disconnected_left
    current_time = time.time()

    if last_data_received_time_left is not None and (current_time - last_data_received_time_left) > detection_timeout:
        detections_left = []

    if camera_disconnected_left.is_set():
        # If the camera is disconnected, don't process or draw anything
        return

    # Update blink state based on the dedicated timer
    update_blink_state()

    # Filter detections based on score
    valuable_detections = [det for det in detections_left if det.get('score', 0) >= score_threshold]

    if valuable_detections:
        # Update last detection time for valuable detections
        last_detection_time_left = current_time

    # Draw detection rectangles
    for det in valuable_detections:
        x1, y1, x2, y2 = det['x'], det['y'], det['w'], det['h']
        cv2.rectangle(frame_left_local, (int(x1), int(y1)), (int(x2), int(y2)), (247, 75, 76), 6)

    # Manage the blink effect based on the last detection time
    if last_detection_time_left and (current_time - last_detection_time_left) < blink_duration:
        border_color = (0, 0, 255) if blink_state_left else (230, 235, 255)
        border_thickness = 20  # Adjust the thickness as needed
        draw_uniform_border_with_lines(frame_left_local, border_color, border_thickness)
    else:
        last_detection_time_left = None

def process_frame_right(frame_right_local):
    global detections_right, last_detection_time_right, last_data_received_time_right
    global blink_state_right, blink_timer_start, camera_disconnected_right
    current_time = time.time()

    if last_data_received_time_right is not None and (current_time - last_data_received_time_right) > detection_timeout:
        detections_right = []

    if camera_disconnected_right.is_set():
        # If the camera is disconnected, don't process or draw anything
        return
        
    # Ensure the blink state is updated based on the timer
    update_blink_state()

    # Filter detections with score threshold
    valuable_detections = [det for det in detections_right if det.get('score', 0) >= score_threshold]

    if valuable_detections:
        # Update the last detection time for valuable detections
        last_detection_time_right = current_time

    for det in valuable_detections:
        x1, y1, x2, y2 = det['x'], det['y'], det['w'], det['h']
        cv2.rectangle(frame_right_local, (int(x1), int(y1)), (int(x2), int(y2)), (217, 255, 76), 6)
        
    # Manage the blink effect based on the last detection time
    if last_detection_time_right and (current_time - last_detection_time_right) < blink_duration:
        border_color = (0, 0, 255) if blink_state_right else (230, 235, 255)
        border_thickness = 20  # Adjust the thickness as needed
        draw_uniform_border_with_lines(frame_right_local, border_color, border_thickness)
    else:
        last_detection_time_right = None

def read_camera_left(rtsp_stream_url_left):
    global frame_left, last_frame_time_left, camera_disconnected_left
    while True:
        cap_left = cv2.VideoCapture(rtsp_stream_url_left)
        while True:
            ret, read_frame_left = cap_left.read()
            if ret:
                frame_left = read_frame_left
                last_frame_time_left = time.time()  # Update with the current timestamp
                frame_available_left.set()  # Signal that a new frame is available
                camera_disconnected_left.clear()
            else:
                logging.warning("Left stream timeout or error. Attempting to reconnect...")
                camera_disconnected_left.set()
                break  # Exit this loop to attempt reconnection
        cap_left.release()
        # Introduce a short pause to avoid overwhelming the system in a tight loop
        time.sleep(1)

def read_camera_right(rtsp_stream_url_right):
    global frame_right, last_frame_time_right, camera_disconnected_right
    while True:
        cap_right = cv2.VideoCapture(rtsp_stream_url_right)
        while True:
            ret, read_frame_right = cap_right.read()
            if ret:
                frame_right = read_frame_right
                last_frame_time_right = time.time()  # Update with the current timestamp
                frame_available_right.set()  # Signal that a new frame is available
                camera_disconnected_right.clear()
            else:
                logging.warning("Right stream timeout or error. Attempting to reconnect...")
                camera_disconnected_right.set()
                break  # Exit this loop to attempt reconnection
        cap_right.release()
        # Introduce a short pause to avoid overwhelming the system in a tight loop
        time.sleep(1)

def video_stream_loop():
    global frame_left, frame_right, frame_available_left, frame_available_right, last_frame_time_left, last_frame_time_right
    global detections_left, detections_right  # Ensure these are accessible

    cv2.namedWindow('Video Stream', cv2.WINDOW_NORMAL)
    full_screen = False
    mouse_is_over_button = False
    camera_timeout = 10

    # Initialize timestamps for connection checks
    last_frame_time_left = time.time()
    last_frame_time_right = time.time()

    def on_mouse(event, x, y, flags, param):
        nonlocal full_screen, mouse_is_over_button
        button_position_x, button_position_y = 2, 2  # Adjust as per your layout
        if button_position_x <= x <= button_position_x + button_width and button_position_y <= y <= button_position_y + button_height:
            mouse_is_over_button = True
            if event == cv2.EVENT_LBUTTONDOWN:
                full_screen = not full_screen
                cv2.setWindowProperty('Video Stream', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN if full_screen else cv2.WINDOW_NORMAL)
        else:
            mouse_is_over_button = False

    cv2.setMouseCallback('Video Stream', on_mouse)

    while True:
        current_time = time.time()

        # Create local copies of frames inside the loop
        with frame_lock_left:
            if frame_available_left.is_set() or (current_time - last_frame_time_left <= camera_timeout):
                frame_left_local = frame_left.copy()
                frame_available_left.clear()
                camera_disconnected_left.clear()
            else:
                frame_left_local = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(frame_left_local, "CAMERA OFFLINE", (200, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                detections_left = []  # Clear detections for left camera
                camera_disconnected_left.set()


        with frame_lock_right:
            if frame_available_right.is_set() or (current_time - last_frame_time_right <= camera_timeout):
                frame_right_local = frame_right.copy()
                frame_available_right.clear()
                camera_disconnected_right.clear()
            else:
                frame_right_local = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(frame_right_local, "CAMERA OFFLINE", (200, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                detections_right = []  # Clear detections for right camera
                camera_disconnected_right.set()

        # Process these local copies
        process_frame_left(frame_left_local)
        process_frame_right(frame_right_local)
    
        target_height = max(frame_left.shape[0], frame_right.shape[0])

        # Resize frames to have the same height (maintain aspect ratio)
        def resize_frame(frame, target_height):
            aspect_ratio = frame.shape[1] / frame.shape[0]
            target_width = int(target_height * aspect_ratio)
            return cv2.resize(frame, (target_width, target_height))

        resized_frame_left = resize_frame(frame_left_local, target_height)
        resized_frame_right = resize_frame(frame_right_local, target_height)

        # Combine and display the processed frames
        combined_frame = np.hstack((resized_frame_left, resized_frame_right))

        # UI for full-screen toggle
        if not full_screen:
            cv2.rectangle(combined_frame, (button_position_x, button_position_y), 
                          (button_position_x + button_width, button_position_y + button_height), 
                          button_hover_color if mouse_is_over_button else button_color, -1)
            cv2.putText(combined_frame, button_text, 
                        (button_position_x + 10, button_position_y + button_height - 6), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        cv2.imshow('Video Stream', combined_frame)

        # Check for user input
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or cv2.getWindowProperty('Video Stream', cv2.WND_PROP_VISIBLE) < 1:
            break
        elif key == ord('f'):
            full_screen = not full_screen
            cv2.setWindowProperty('Video Stream', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN if full_screen else cv2.WINDOW_NORMAL)
        elif key == 27:  # ESC key
            full_screen = False
            cv2.setWindowProperty('Video Stream', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_NORMAL)

    cv2.destroyAllWindows()

if __name__ == "__main__":
    # RTSP URL for the left camera (subtype=0)
    rtsp_url_left = "rtsp://teste:Ambev123@192.168.137.109:554/cam/realmonitor?channel=1&subtype=0"

    # RTSP URL for the right camera (subtype=0)
    rtsp_url_right = "rtsp://teste:Ambev123@192.168.137.109:554/cam/realmonitor?channel=1&subtype=0"

    # Start WebSocket servers for left and right streams
    threading.Thread(target=lambda: asyncio.run(start_websocket_server_left()), daemon=True).start()
    threading.Thread(target=lambda: asyncio.run(start_websocket_server_right()), daemon=True).start()

    # Start video stream threads for the left and right cameras
    threading.Thread(target=read_camera_left, args=(rtsp_url_left,), daemon=True).start()
    threading.Thread(target=read_camera_right, args=(rtsp_url_right,), daemon=True).start()

    # Start the video stream loop
    video_stream_loop()