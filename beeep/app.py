import os
from flask import Flask, request, jsonify, send_from_directory
import subprocess
from google.cloud import storage
from urllib.parse import urlparse
import requests

app = Flask(__name__)

# Initialize GCS client
storage_client = storage.Client()

# Directory to save downloaded files
DOWNLOAD_DIR = 'downloads'
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def download_blob(bucket_name, source_blob_name, destination_file_name):
    """Downloads a blob from the GCS bucket."""
    try:
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(source_blob_name)
        blob.download_to_filename(destination_file_name)
        print(f"Downloaded {source_blob_name} from bucket {bucket_name} to {destination_file_name}.")
    except Exception as e:
        print(f"Failed to download blob {source_blob_name} from bucket {bucket_name}. Error: {e}")
        raise

def download_file(url, destination_file_name):
    """Downloads a file from a given URL."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        with open(destination_file_name, 'wb') as file:
            file.write(response.content)
        print(f"Downloaded file from {url} to {destination_file_name}.")
    except Exception as e:
        print(f"Failed to download file from {url}. Error: {e}")
        raise

def verify_audio_file(file_path):
    """Verifies if the file is a valid audio file using ffprobe."""
    try:
        result = subprocess.run(['ffprobe', file_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            print(f"ffprobe error: {result.stderr.decode('utf-8')}")
            return False
        return True
    except Exception as e:
        print(f"Failed to run ffprobe on {file_path}. Error: {e}")
        return False

def repair_audio_file(file_path):
    """Repairs an audio file by remuxing it with FFmpeg."""
    repaired_file_path = file_path.replace('.mp3', '_repaired.mp3')  # Adjust extension if needed
    try:
        result = subprocess.run([
            'ffmpeg', '-i', file_path, '-acodec', 'copy', '-y', repaired_file_path
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if result.returncode != 0:
            print(f"FFmpeg repair error: {result.stderr.decode('utf-8')}")
            return None

        print(f"Repaired file saved as {repaired_file_path}")
        return repaired_file_path
    except Exception as e:
        print(f"Error repairing audio file {file_path}: {e}")
        return None

def upload_blob(bucket_name, source_file_name, destination_blob_name):
    """Uploads a file to the GCS bucket."""
    try:
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)
        blob.upload_from_filename(source_file_name)
        print(f"Uploaded {source_file_name} to bucket {bucket_name} as {destination_blob_name}.")
    except Exception as e:
        print(f"Failed to upload {source_file_name} to bucket {bucket_name}. Error: {e}")
        raise

@app.route('/add_beep', methods=['POST'])
def add_beep():
    if 'audio_file_url' not in request.json or 'durations' not in request.json:
        return jsonify({"error": "Missing audio file URL or durations"}), 400

    audio_file_url = request.json['audio_file_url']
    durations = request.json['durations']

    # Parse the URL to determine if it's a GCS URL or a normal URL
    parsed_url = urlparse(audio_file_url)

    # Extract the file name from the URL
    original_file_name = os.path.basename(parsed_url.path)
    audio_filename = os.path.join(DOWNLOAD_DIR, original_file_name)

    if parsed_url.scheme == 'gs':
        bucket_name = parsed_url.netloc
        blob_name = parsed_url.path.lstrip('/')
        try:
            download_blob(bucket_name, blob_name, audio_filename)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    else:
        try:
            download_file(audio_file_url, audio_filename)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    if not os.path.isfile(audio_filename):
        return jsonify({"error": f"File {audio_filename} not found after download"}), 500

    # Repair the audio file before processing
    repaired_audio_filename = repair_audio_file(audio_filename)
    if not repaired_audio_filename:
        return jsonify({"error": "Failed to repair the audio file"}), 500

    # Verify the repaired audio file
    if not verify_audio_file(repaired_audio_filename):
        return jsonify({"error": f"Invalid repaired audio file: {repaired_audio_filename}"}), 400

    # Generate beep sound
    beep_filename = os.path.join(DOWNLOAD_DIR, 'beep.wav')
    subprocess.run([
        'ffmpeg', '-f', 'lavfi', '-i', 'sine=frequency=1000:duration=0.5',
        '-y', beep_filename
    ])

    if not os.path.isfile(beep_filename):
        return jsonify({"error": f"File {beep_filename} not generated"}), 500

    # Parse durations and create filter_complex argument
    filter_complex = '[0:a]asplit=' + str(len(durations)) + ''.join([f'[a{i}]' for i in range(len(durations))]) + ';'
    for i, start_time in enumerate(durations):
        filter_complex += f'[a{i}]atrim=0:{start_time},asetpts=PTS-STARTPTS[a{i}start];'
        filter_complex += f'[a{i}]atrim={start_time}:{start_time + 0.5},asetpts=PTS-STARTPTS[a{i}beep];'
        filter_complex += f'[a{i}start][1:a][a{i}beep]concat=n=3:v=0:a=1[a{i}out];'

    filter_complex += ''.join([f'[a{i}out]' for i in range(len(durations))])
    filter_complex += f'concat=n={len(durations)}:v=0:a=1[outa]'

    output_filename = os.path.join(DOWNLOAD_DIR, f'output_{original_file_name}')
    result = subprocess.run([
        'ffmpeg', '-i', repaired_audio_filename, '-i', beep_filename, 
        '-filter_complex', filter_complex, '-map', '[outa]', 
        '-y', output_filename
    ])

    if not os.path.isfile(output_filename):
        return jsonify({"error": f"File {output_filename} not generated"}), 500

    output_blob_name = 'beeped_audio/' + os.path.basename(output_filename)
    try:
        upload_blob(bucket_name, output_filename, output_blob_name)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({
        "message": "Beep sound added successfully",
        "output_file": output_blob_name,
        "downloaded_file": f"/download/{original_file_name}"
    })

@app.route('/download/<filename>', methods=['GET'])
def download_file_route(filename):
    """Route to download a file from the server."""
    return send_from_directory(DOWNLOAD_DIR, filename)

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)   
