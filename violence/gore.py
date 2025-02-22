from google.cloud import vision

client = vision.ImageAnnotatorClient()

with open("/content/MV5BMjVlOTk5MDYtNGNlMy00ZjIzLTkwZmEtNmViODE0Zjg1ODZjXkEyXkFqcGc@.V1.jpg", "rb") as image_file:
    content = image_file.read()
    image = vision.Image(content=content)

response = client.safe_search_detection(image=image)
safe = response.safe_search_annotation

# Likelihood mapping
likelihood_dict = {
    0: "UNKNOWN",
    1: "VERY_UNLIKELY",
    2: "UNLIKELY",
    3: "POSSIBLE",
    4: "LIKELY",
    5: "VERY_LIKELY"
}

print(f"Violence Likelihood: {likelihood_dict[safe.violence]}")
