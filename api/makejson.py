import torch
import open_clip
import cv2
import numpy as np
from PIL import Image
from google.cloud import vision
from ultralytics import YOLO
from datetime import datetime, timedelta
import os

# System Configuration
SYSTEM_INFO = {
    "CURRENT_UTC": "2025-02-23 06:32:31",
    "CURRENT_USER": "alaotach",
    "VERSION": "1.0.0"
}

# Model Paths
MODEL_PATHS = {
    "YOLO_MODEL": "aloo.pt",
    "CLIP_MODEL": "ViT-B/32"
}

# Content Categories
TEXT_DESCRIPTIONS = [
    "explicit sexual content",
    "nudity",
    "violence and gore",
    "self harm or suicide",
    "hate speech or discrimination",
    "illegal substances",
    "gambling",
    "alcohol",
    "tobacco",
    "weapons with violence",
    "weapons without violence",
    "mild romantic content",
    "horror elements",
    "educational content",
    "sports and fitness",
    "safe and normal content",
    "minimal clothing",
    "suggestive dialogue",
    "crude humor",
    "mild profanity",
    "mature themes"
]

# Rating System Configuration
CONTENT_RATINGS = {
    "U": {
        "description": "Unrestricted public exhibition, suitable for all ages",
        "min_age": 0,
        "allowed_content": [
            "educational content",
            "sports and fitness",
            "safe and normal content",
            "mild profanity",
            "crude humor",
            "mild violence"
        ]
    },
    "U/A 7+": {
        "description": "Parental guidance for children below 7 years",
        "min_age": 7,
        "allowed_content": [
            "weapons without violence",
            "mild romantic content",
            "mild profanity"
        ]
    },
    "U/A 13+": {
        "description": "Parental guidance for children below 13 years",
        "min_age": 13,
        "allowed_content": [
            "horror elements",
            "moderate violence",
            "suggestive dialogue",
            "minimal clothing"
        ]
    },
    "U/A 16+": {
        "description": "Parental guidance for children below 16 years",
        "min_age": 16,
        "allowed_content": [
            "moderate sexual content",
            "alcohol",
            "tobacco",
            "weapons with violence"
        ]
    },
    "A": {
        "description": "Adults Only (18+)",
        "min_age": 18,
        "allowed_content": [
            "explicit sexual content",
            "violence and gore",
            "self harm or suicide",
            "hate speech or discrimination",
            "illegal substances",
            "gambling"
        ]
    },
    "S": {
        "description": "Special/Restricted Audiences",
        "min_age": 21,
        "allowed_content": [
            "extreme violence",
            "extreme controversial content"
        ]
    }
}

class ContentModerationSystem:
    def __init__(self):
        # Initialize models
        self.clip_model, self.preprocess, self.tokenizer = open_clip.create_model_and_transforms(
            MODEL_PATHS["CLIP_MODEL"],
            pretrained="openai"
        )
        self.yolo_model = YOLO(MODEL_PATHS["YOLO_MODEL"])
        self.vision_client = vision.ImageAnnotatorClient()

        # Set device
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.clip_model = self.clip_model.to(self.device)

        # Set system time and user
        self.current_time = datetime.strptime(SYSTEM_INFO["CURRENT_UTC"], "%Y-%m-%d %H:%M:%S")
        self.current_user = SYSTEM_INFO["CURRENT_USER"]

    def classify_with_clip(self, image_path):
        """Classify image content using CLIP model"""
        image = self.preprocess(Image.open(image_path)).unsqueeze(0)
        text_tokens = open_clip.tokenize(TEXT_DESCRIPTIONS)

        image = image.to(self.device)
        text_tokens = text_tokens.to(self.device)

        with torch.no_grad():
            image_features = self.clip_model.encode_image(image)
            text_features = self.clip_model.encode_text(text_tokens)

            image_features /= image_features.norm(dim=-1, keepdim=True)
            text_features /= text_features.norm(dim=-1, keepdim=True)

            similarity = (image_features @ text_features.T).squeeze(0)

        best_match_idx = similarity.argmax().item()
        return TEXT_DESCRIPTIONS[best_match_idx]

    def check_google_safesearch(self, image_path):
        """Check image content using Google Vision SafeSearch"""
        with open(image_path, "rb") as image_file:
            content = image_file.read()
            image = vision.Image(content=content)

        response = self.vision_client.safe_search_detection(image=image)
        safe = response.safe_search_annotation

        likelihood_dict = {
            0: "UNKNOWN",
            1: "VERY_UNLIKELY",
            2: "UNLIKELY",
            3: "POSSIBLE",
            4: "LIKELY",
            5: "VERY_LIKELY"
        }

        return {
            "violence": likelihood_dict[safe.violence],
            "adult": likelihood_dict[safe.adult],
            "racy": likelihood_dict[safe.racy],
            "medical": likelihood_dict[safe.medical]
        }

    def detect_with_yolo(self, image_path):
        """Detect objects using YOLO model"""
        results = self.yolo_model(image_path)
        detected_objects = []

        for result in results:
            for box in result.boxes:
                obj_name = result.names[int(box.cls)]
                detected_objects.append((obj_name, box.conf.item()))

        return detected_objects

    def determine_rating(self, clip_category, safe_search_results, yolo_detections):
        """Determine content rating based on multiple detection results"""
        rating = "U"
        reasons = []

        # Check CLIP category against ratings
        for rating_key, rating_info in CONTENT_RATINGS.items():
            if clip_category in rating_info["allowed_content"]:
                if rating_info["min_age"] > CONTENT_RATINGS[rating]["min_age"]:
                    rating = rating_key
                    reasons.append(f"Contains {clip_category}")
                break

        # Check SafeSearch results
        if safe_search_results["adult"] in ["VERY_LIKELY", "LIKELY"]:
            rating = max(rating, "A", key=lambda x: CONTENT_RATINGS[x]["min_age"])
            reasons.append("Adult content detected")
        elif safe_search_results["violence"] in ["VERY_LIKELY", "LIKELY"]:
            rating = max(rating, "U/A 16+", key=lambda x: CONTENT_RATINGS[x]["min_age"])
            reasons.append("Violence detected")

        # Check YOLO detections
        for obj, conf in yolo_detections:
            if conf > 0.6:
                if obj in ["violence", "explicit", "self-harm"]:
                    rating = "A"
                    reasons.append(f"Detected {obj}")
                elif obj == "weapons":
                    if safe_search_results["violence"] in ["POSSIBLE", "LIKELY", "VERY_LIKELY"]:
                        rating = max(rating, "U/A 16+", key=lambda x: CONTENT_RATINGS[x]["min_age"])
                        reasons.append("Weapons with violence context detected")

        return rating, reasons

    def process_content(self, path, viewer_age, content_type="image"):
        """Process content and return rating decision"""
        if content_type == "image":
            return self.process_image(path, viewer_age)
        else:
            return self.process_video(path, viewer_age)

    def process_image(self, image_path, viewer_age):
        """Process single image"""
        # Get content analysis results
        clip_category = self.classify_with_clip(image_path)
        safe_search_results = self.check_google_safesearch(image_path)
        yolo_detections = self.detect_with_yolo(image_path)

        # Determine rating and reasons
        rating, reasons = self.determine_rating(clip_category, safe_search_results, yolo_detections)

        # Determine action based on viewer age
        if int(viewer_age) < CONTENT_RATINGS[rating]["min_age"]:
            if rating in ["A", "S"]:
                action = "REMOVE"
            else:
                action = "BLUR"
        else:
            action = "ALLOW"

        return {
            "timestamp": self.current_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "path": image_path,
            "rating": rating,
            "action": action,
            "reasons": reasons
        }

    def process_video(self, video_path, viewer_age, fps=1):
        """Process video and return frame-by-frame decisions"""
        cap = cv2.VideoCapture(video_path)
        original_fps = cap.get(cv2.CAP_PROP_FPS)
        frame_interval = int(original_fps / fps)

        results = []
        frame_count = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_count % frame_interval == 0:
                # Save frame temporarily
                temp_frame_path = f"temp_frame_{frame_count}.jpg"
                cv2.imwrite(temp_frame_path, frame)

                # Process frame
                result = self.process_image(temp_frame_path, viewer_age)
                result["frame_number"] = frame_count
                result["timestamp"] = str(timedelta(seconds=frame_count/original_fps))

                results.append(result)

                # Remove temporary frame
                os.remove(temp_frame_path)

            frame_count += 1

        cap.release()
        return results

# Example usage
# if __name__ == "__main__":
#     # Initialize the system
#     cms = ContentModerationSystem()

#     # Process an image
#     # image_path = "/content/1_807bcd15-c754-4efa-9b90-c6111d24a01e.webp"
#     viewer_age = 12

#     # Process image
#     # result = cms.process_content(image_path, viewer_age, "image")
#     # print(f"Image Analysis Result:")
#     # print(f"Timestamp: {result['timestamp']}")
#     # print(f"Rating: {result['rating']}")
#     # print(f"Action: {result['action']}")
#     # print(f"Reasons: {', '.join(result['reasons'])}")
#     # print()

#     # Process a video
#     video_path = "/content/vid.mp4"
#     video_results = cms.process_content(video_path, viewer_age, "video")
#     print("Video Analysis Results:")
