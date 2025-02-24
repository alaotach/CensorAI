import torch
import open_clip
import cv2
import numpy as np
from PIL import Image
from google.cloud import vision
from ultralytics import YOLO
from datetime import datetime
from config import SYSTEM_INFO, MODEL_PATHS, TEXT_DESCRIPTIONS, CONTENT_RATINGS

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

    def process_frame(self, frame_path, viewer_age):
        """Process a single frame and return moderation results"""
        clip_category = self.classify_with_clip(frame_path)
        safe_search_results = self.check_google_safesearch(frame_path)
        yolo_detections = self.detect_with_yolo(frame_path)

        rating, reasons = self.determine_rating(clip_category, safe_search_results, yolo_detections)

        if viewer_age < CONTENT_RATINGS[rating]["min_age"]:
            if rating in ["A", "S"]:
                action = "REMOVE"
            else:
                action = "BLUR"
        else:
            action = "ALLOW"

        return {
            "timestamp": self.current_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "rating": rating,
            "action": action,
            "reasons": reasons,
            "detections": {
                "clip_category": clip_category,
                "safe_search": safe_search_results,
                "yolo_objects": yolo_detections
            }
        }