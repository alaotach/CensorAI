import os
import subprocess
from flask import Flask, request, jsonify
from google.cloud import storage

app = Flask(__name__)

TEMP_FOLDER = "temp"
os.makedirs(TEMP_FOLDER, exist_ok=True)

# Initialize Google Cloud Storage client
storage_client = storage.Client()

def download_from_gcs(bucket_name, gcs_path, local_path):
    """Downloads a file from Google Cloud Storage to local storage."""
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(gcs_path)
    blob.download_to_filename(local_path)
    print(f"Downloaded {gcs_path} from GCS to {local_path}")

def upload_to_gcs(bucket_name, local_path, gcs_path):
    """Uploads a file from local storage to Google Cloud Storage."""
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(gcs_path)
    blob.upload_from_filename(local_path)
    print(f"Uploaded {local_path} to GCS as {gcs_path}")
    return f"gs://{bucket_name}/{gcs_path}"

def process_video(video_path, audio_url):
    """Replaces the audio in the video using FFmpeg."""
    audio_path = os.path.join(TEMP_FOLDER, "downloaded_audio.mp3")
    output_path = os.path.join(TEMP_FOLDER, "output.mp4")

    # Download the audio file from API
    os.system(f"curl -o {audio_path} {audio_url}")
    print(f"Audio downloaded: {audio_path}")

    # Run FFmpeg to merge new audio
    cmd = [
        "ffmpeg",
        "-i", video_path,        # Input video
        "-i", audio_path,        # Input new audio
        "-c:v", "libx264",       # Video codec
        "-c:a", "aac",           # Audio codec
        "-map", "0:v:0",         # Keep video from input
        "-map", "1:a:0",         # Use new audio
        "-preset", "fast",
        "-crf", "23",
        "-y",                    # Overwrite existing file
        output_path
    ]

    # Run FFmpeg
    try:
        subprocess.run(cmd, check=True)
        print(f"Video processing complete: {output_path}")
    except subprocess.CalledProcessError as e:
        raise Exception(f"FFmpeg failed: {e}")

    return output_path

@app.route("/convert", methods=["POST"])
def convert():
    """
    API endpoint to process a video from Google Cloud Storage with new audio.

    Request JSON:
    {
        "video_gcs": "gs://your-bucket/input.mp4",
        "audio_url": "https://example.com/audio.mp3",
        "output_gcs": "gs://your-bucket/output.mp4"
    }

    Returns:
    - JSON with output GCS URL.
    """
    data = request.json

    if "video_gcs" not in data or "audio_url" not in data or "output_gcs" not in data:
        return jsonify({"error": "Missing required parameters"}), 400

    video_gcs = data["video_gcs"]
    audio_url = data["audio_url"]
    output_gcs = data["output_gcs"]

    # Extract bucket names and paths
    video_bucket, video_blob = video_gcs.replace("gs://", "").split("/", 1)
    output_bucket, output_blob = output_gcs.replace("gs://", "").split("/", 1)

    # Define local file paths
    video_path = os.path.join(TEMP_FOLDER, "input.mp4")

    # Download video from GCS
    download_from_gcs(video_bucket, video_blob, video_path)

    try:
        # Process the video
        final_video_path = process_video(video_path, audio_url)
        
        # Upload final video to GCS
        final_gcs_url = upload_to_gcs(output_bucket, final_video_path, output_blob)

        return jsonify({"output_gcs": final_gcs_url}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
