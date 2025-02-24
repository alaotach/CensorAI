from datetime import datetime

# System Configuration
SYSTEM_INFO = {
    "CURRENT_UTC": "2025-02-23 13:36:30",
    "CURRENT_USER": "alaotach",
    "VERSION": "1.0.0"
}

# Model Paths
MODEL_PATHS = {
    "YOLO_MODEL": "models/detector.pt",
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