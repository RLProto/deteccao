import cv2
import threading
import numpy as np
import logging
from aiohttp import web
import json
import time
from opcua import Client

# Global variables

# For left stream
detections_left = []
last_detection_time_left = None
last_data_received_time_left = None  # Initialize this variable
frame_left = np.zeros((480, 640, 3), dtype=np.uint8)
frame_available_left = threading.Event()
camera_disconnected_left = threading.Event()

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

interlock_signals_left = {
    'enable': False,
    'detection': False,
    'emergency_button': False,
    'light_curtain': False,
    'emergency_cord': False
}

interlock_signals_right = {
    'enable': False,
    'detection': False,
    'emergency_button': False,
    'light_curtain': False,
    'emergency_cord': False
}

async def handle_person_detected(request):
    global detections_left, last_detection_time_left, last_data_received_time_left
    global detections_right, last_detection_time_right, last_data_received_time_right

    side = request.match_info['side']
    try:
        current_time = time.time()
        if side == 'left':
            last_data_received_time_left = current_time
            detections_left = True
            last_detection_time_left = current_time
        elif side == 'right':
            last_data_received_time_right = current_time
            detections_right = True
            last_detection_time_right = current_time

        return web.Response(text=f"{side.capitalize()} person_detected processed", status=200)
    except Exception as e:
        return web.Response(text=str(e), status=500)

async def handle_generic(request):
    side = request.match_info['side']
    operation = request.match_info['operation']

    try:
        data = await request.json()
        value = data.get('value', False)  # Default to False if not provided

        if side == 'left':
            interlock_signals_left[operation] = value
        elif side == 'right':
            interlock_signals_right[operation] = value

        return web.Response(text=f"{side.capitalize()} {operation} set to {value}", status=200)
    except json.JSONDecodeError:
        return web.Response(text="Invalid JSON data", status=400)
    except Exception as e:
        return web.Response(text=str(e), status=500)

def start_api(port=80):
    app = web.Application()
    app.add_routes([
        web.post('/{side}/person_detected', handle_person_detected),
        web.post('/{side}/{operation}', handle_generic)
    ])
    web.run_app(app, port=port)

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

    if detections_left:
        # Update last detection time for valuable detections
        last_detection_time_left = current_time

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

    # Update blink state based on the dedicated timer
    update_blink_state()

    if detections_right:
        # Update last detection time for valuable detections
        last_detection_time_right = current_time

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

def display_interlock_status(frame, side):
    # Choose the correct dictionary based on 'side'
    if side == 'left':
        interlock_signals = interlock_signals_left
    else:
        interlock_signals = interlock_signals_right

    # Exit if interlock is not enabled
    if not interlock_signals['enable']:
        return

    # Determine active signals excluding 'enable'
    active_signals = [signal for signal, active in interlock_signals.items() if active and signal != 'enable']

    # Display additional active signals
    translations = {
        'detection': 'Pessoa Detectada',
        'emergency_button': 'Botao de Emergencia Pressionado',
        'light_curtain': 'Cortina de Luz Acionada',
        'emergency_cord': 'Corda de Emergencia Acionada'
    }

    # Exit if no signals are active
    if not active_signals:
        return

    current_time = int(time.time())
    blink_on = current_time % 2 == 0  # Blink every second

    # Main interlock status
    text = "Intertravamento Ativado"
    color = (0, 0, 255)  # Red color for text
    background_color = (245, 245, 225)  # Light white background for main sign
    text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 3, 6)[0]
    text_x = 390 if side == 'left' else 2320
    text_y = 850

    for i, signal in enumerate(active_signals):
        signal_text = translations[signal]
        signal_text_size = cv2.getTextSize(signal_text, cv2.FONT_HERSHEY_SIMPLEX, 1, 2)[0]
        signal_y = text_y + (i + 1) * 40
        signal_color = (0, 255, 255)  # Yellow text
        signal_background_color = (127, 127, 127)  # Gray background
        # Adjust the rectangle width based on the text size
        cv2.rectangle(frame, (text_x, signal_y - 30), (text_x + signal_text_size[0] + 10, signal_y + 1), signal_background_color, -1)
        cv2.putText(frame, signal_text, (text_x + 3, signal_y - 3), cv2.FONT_HERSHEY_SIMPLEX, 1, signal_color, 2)

    if not blink_on:
        return  # Skip drawing if it's an "off" second for blinking

    # Draw the main interlock status
    cv2.rectangle(frame, (text_x, text_y - text_size[1] - 30), (text_x + text_size[0] + 20, text_y - 10), background_color, -1)
    cv2.putText(frame, text, (text_x + 10, text_y - 20), cv2.FONT_HERSHEY_SIMPLEX, 3, color, 8)

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

        # Display interlock status for left and right cameras
        #display_interlock_status(combined_frame, 'left')
        display_interlock_status(combined_frame, 'right')

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
    rtsp_url_left = "rtsp://admin:Ambev123@192.168.0.53:554/profile1"

    # RTSP URL for the right camera (subtype=0)
    rtsp_url_right = "rtsp://admin:Ambev123@192.168.0.50:554/profile1"

    # Start the API server in a separate thread
    api_thread = threading.Thread(target=start_api, args=(80,), daemon=True)
    api_thread.start()
    
    # Start video stream threads for the left and right cameras
    left_camera_thread = threading.Thread(target=read_camera_left, args=(rtsp_url_left,), daemon=True)
    right_camera_thread = threading.Thread(target=read_camera_right, args=(rtsp_url_right,), daemon=True)
    left_camera_thread.start()
    right_camera_thread.start()

    # Start the video stream loop in the main thread
    video_stream_loop()