import torch
import open_clip  # Using open_clip instead of clip-by-openai
from PIL import Image

# Load CLIP Model
model, preprocess, tokenizer = open_clip.create_model_and_transforms("ViT-B/32", pretrained="openai")

# Load and preprocess the image
image = preprocess(Image.open("/content/images (1).jpeg")).unsqueeze(0)

# Define categories for classification
text_descriptions = [
    "suicide attempt",
    "self-harm",
    "sex",
    "nude",
    "violent scene",
    "drugs and smoking",
    "kiss",
    "horror",
    "death",
    "alcohol",
    "weapons",
    "guns",
    "gore",
    "safe and normal content"
]

# Correct way to tokenize text
text_tokens = open_clip.tokenize(text_descriptions)  # ✅ Fixed line

# Move to device
device = "cpu"
model.to(device)
image = image.to(device)
text_tokens = text_tokens.to(device)

# Compute similarity
with torch.no_grad():
    image_features = model.encode_image(image)
    text_features = model.encode_text(text_tokens)

    # Normalize features
    image_features /= image_features.norm(dim=-1, keepdim=True)
    text_features /= text_features.norm(dim=-1, keepdim=True)

    # Compute similarity via dot product
    similarity = (image_features @ text_features.T).squeeze(0)

# Find the best match
best_match_idx = similarity.argmax().item()
print(f"Predicted Category: {text_descriptions[best_match_idx]}")
