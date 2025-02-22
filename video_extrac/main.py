import os
import uuid
from flask import Flask, request, jsonify
import subprocess
from google.cloud import storage

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output"
BUCKET_NAME = "duhack"
CREDENTIALS_PATH = "gcp-key.json"  # Ensure this file exists in the same directory

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = CREDENTIALS_PATH

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Initialize GCP Storage Client
storage_client = storage.Client()

def generate_filename(username, original_filename):
    random_text = uuid.uuid4().hex[:8]  # Generate 8-character random text
    filename, ext = os.path.splitext(original_filename)
    return f"{username}-{random_text}{ext}"

def upload_to_gcp(bucket_name, source_file, destination_blob):
    try:
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(destination_blob)
        blob.upload_from_filename(source_file)
        return f"https://storage.googleapis.com/{bucket_name}/{destination_blob}"
    except Exception as e:
        return f"Error uploading to GCP: {str(e)}"

@app.route("/extract", methods=["POST"])
def extract():
    try:
        if "file" not in request.files or "username" not in request.form:
            return jsonify({"error": "File and username are required"}), 400
        
        file = request.files["file"]
        username = request.form["username"].strip()
        if file.filename == "" or not username:
            return jsonify({"error": "Invalid file or username"}), 400
        
        new_filename = generate_filename(username, file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, new_filename)
        file.save(filepath)
        
        filename_no_ext, _ = os.path.splitext(new_filename)
        audio_output = os.path.join(OUTPUT_FOLDER, f"{filename_no_ext}.mp3")
        video_output = os.path.join(OUTPUT_FOLDER, f"{filename_no_ext}_video.mp4")
        subtitle_output = os.path.join(OUTPUT_FOLDER, f"{filename_no_ext}.srt")
        wav_output = os.path.join(OUTPUT_FOLDER, f"{filename_no_ext}.wav")
        
        # Extract audio
        subprocess.run(["ffmpeg", "-i", filepath, "-q:a", "0", "-map", "a", audio_output], stderr=subprocess.DEVNULL)
        
        # Extract video without audio
        subprocess.run(["ffmpeg", "-i", filepath, "-an", "-c:v", "copy", video_output], stderr=subprocess.DEVNULL)
        
        # Extract subtitles (if available)
        subprocess.run(["ffmpeg", "-i", filepath, "-map", "0:s:0?", "-c:s", "copy", subtitle_output], stderr=subprocess.DEVNULL)
        
        # Convert to WAV, mono, 16kHz, 16-bit
        subprocess.run(["ffmpeg", "-i", filepath, "-ac", "1", "-ar", "16000", "-sample_fmt", "s16", wav_output], stderr=subprocess.DEVNULL)
        
        # Upload files to GCP
        video_url = upload_to_gcp(BUCKET_NAME, filepath, f"videos/{new_filename}")
        audio_url = upload_to_gcp(BUCKET_NAME, audio_output, f"audio/{filename_no_ext}.mp3")
        wav_url = upload_to_gcp(BUCKET_NAME, wav_output, f"audio/{filename_no_ext}.wav")
        
        subtitle_url = "Subtitle not found"
        if os.path.exists(subtitle_output):
            subtitle_url = upload_to_gcp(BUCKET_NAME, subtitle_output, f"subtitles/{filename_no_ext}.srt")
        
        return jsonify({
            "video": video_url,
            "audio": audio_url,
            "wav": wav_url,
            "subtitle": subtitle_url
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)