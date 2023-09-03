from fastapi import FastAPI, File, UploadFile
from starlette.responses import Response
from io import BytesIO
import cv2
import numpy as np
from ultralytics import YOLO  # Import the YOLO model

app = FastAPI(
    title="Image Processing API",
    description="An API for processing and displaying images.",
    version="1.0.0",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Load the YOLO model
model = YOLO(r'/app/best.pt')

@app.post("/process_frame", summary="Process and display an image")
async def process_frame(file: UploadFile):
    try:
        # Read the uploaded image file as bytes
        image_bytes = await file.read()

        # Decode the image
        image_np = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(image_np, cv2.IMREAD_COLOR)

        if image is not None:
            # Perform object detection using YOLO
            results = model(image)

            # Extract detection scores
            detection_scores = []

            for result in results:
                for r in result.boxes.data.tolist():
                    _, _, _, _, score, class_id = r
                    class_id = int(class_id)
                    score = float(score)

                    # Check if the class ID is 0.0 (your specific class of interest)
                    if class_id == 0.0:
                        detection_scores.append(score)

            # Return the detection scores as JSON
            return {"detection_scores": detection_scores}
        else:
            return {"status": "ERROR", "message": "Failed to decode the frame."}

    except Exception as e:
        return {"status": "ERROR", "message": str(e)}

if __name__ == "__main__":
    import uvicorn


