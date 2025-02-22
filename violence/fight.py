from ultralytics import YOLO
import cv2

# Load YOLOv8 Pretrained Model
model = YOLO("aloo.pt")  # Using the standard model

# Run detection on an image
image_path = "/content/images (1).jpeg"
results = model(image_path)

# Show results
for result in results:
    print("Detected Objects:", result.names)  # Print detected classes
    for box in result.boxes:
        print(f"Object: {result.names[int(box.cls)]}, Confidence: {box.conf.item():.2f}")
