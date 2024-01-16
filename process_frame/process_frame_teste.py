from fastapi import FastAPI, File, UploadFile, Form
from starlette.responses import Response
import cv2
import numpy as np
from ultralytics import YOLO
import asyncio
import websockets
import json
import os
import threading

app = FastAPI(
    title="Image Processing API",
    description="An API for processing and displaying images.",
    version="1.0.0",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

model = YOLO(r'./yolov8s.pt')

g1_uri = os.getenv('G1_URI')
g2_uri = os.getenv('G2_URI')
g3_uri = os.getenv('G3_URI')
g4_uri = os.getenv('G4_URI')

g1_uri = "ws://192.168.137.1:8765"
g3_uri = "ws://192.168.137.1:8766"

source_to_uri = {
    "G1": g1_uri,
    "G2": g2_uri,
    "G3": g3_uri,
    "G4": g4_uri,
}

# Function to handle WebSocket connection
def send_detection_to_video_stream(detection_scores, source):
    uri = source_to_uri.get(source) 

    formatted_detections = [
        {'class_id': det['class_id'], 'score': round(det['score'], 2), 'x': det['x'], 'y': det['y'], 'w': det['w'], 'h': det['h']}
        for det in detection_scores['detections']
    ]

    data_to_send = {'detections': formatted_detections}

    try:
        async def async_send():
            async with websockets.connect(uri) as websocket:
                await websocket.send(json.dumps(data_to_send))

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(async_send())
    except asyncio.TimeoutError:
        print(f"WebSocket connection to {uri} timed out.")
    except Exception as e:
        print(f"WebSocket error: {e}")

@app.post("/process_frame", summary="Process and display an image")
async def process_frame(file: UploadFile, equipment: str = Form(...)):
    try:
        image_bytes = await file.read()
        print(equipment)

        image_np = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(image_np, cv2.IMREAD_COLOR)

        if image is not None:
            results = model(image)
            detection_scores = []

            for result in results:
                for r in result.boxes.data.tolist():
                    x, y, w, h, score, class_id = r
                    class_id = int(class_id)
                    score = float(score)
                    if class_id == 0.0:
                        detection_scores.append({
                            'class_id': class_id,
                            'score': round(score, 2),
                            'x': x,
                            'y': y,
                            'w': w,
                            'h': h
                        })

            # Use threading to run WebSocket connection in the background
            threading.Thread(target=send_detection_to_video_stream, args=({'detections': detection_scores}, equipment), daemon=True).start()

            return {"detection_scores": detection_scores}
        else:
            return {"status": "ERROR", "message": "Failed to decode the frame."}
    except Exception as e:
        return {"status": "ERROR", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
