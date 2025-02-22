import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

EXTRACT_API = os.getenv("EXTRACT_API", "http://extract-service:5000/extract")
PROCESS_AUDIO_API = os.getenv("PROCESS_AUDIO_API", "http://process-audio-service:5000/process_audio")
ADD_BEEP_API = os.getenv("ADD_BEEP_API", "http://add-beep-service:5000/add_beep")
CONVERT_API = os.getenv("CONVERT_API", "http://convert-service:5000/convert")

@app.route("/process_video", methods=["POST"])
def process_video():
    if "file" not in request.files or "username" not in request.form:
        return jsonify({"error": "File and username are required"}), 400
    
    file = request.files["file"]
    username = request.form["username"].strip()
    
    # Step 1: Upload to Extract API
    extract_response = requests.post(EXTRACT_API, files={"file": file}, data={"username": username})
    if extract_response.status_code != 200:
        return jsonify({"error": "Extract API failed", "details": extract_response.json()}), 500
    extract_data = extract_response.json()
    
    # Step 2: Process Audio API
    process_audio_response = requests.post(PROCESS_AUDIO_API, json={"file_name": extract_data["wav"].split("/")[-1]})
    if process_audio_response.status_code != 200:
        return jsonify({"error": "Process Audio API failed", "details": process_audio_response.json()}), 500
    process_audio_data = process_audio_response.json()
    
    # Step 3: Add Beep API
    beep_response = requests.post(ADD_BEEP_API, files={"audio": open("temp_audio.wav", "rb")}, json={"durations": process_audio_data["timestamps"]})
    if beep_response.status_code != 200:
        return jsonify({"error": "Add Beep API failed", "details": beep_response.json()}), 500
    beep_data = beep_response.json()
    
    # Step 4: Convert API
    convert_response = requests.post(CONVERT_API, json={
        "video_gcs": extract_data["video"],
        "audio_url": beep_data["output_file"],
        "output_gcs": f"gs://duhack/processed/{username}.mp4"
    })
    if convert_response.status_code != 200:
        return jsonify({"error": "Convert API failed", "details": convert_response.json()}), 500
    convert_data = convert_response.json()
    
    return jsonify({"processed_video": convert_data["output_gcs"]})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
