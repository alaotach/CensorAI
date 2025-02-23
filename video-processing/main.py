from flask import Flask, request, send_file
import os
import tempfile
import uuid  # Import the uuid module
from werkzeug.utils import secure_filename # Import secure_filename
from makejson import ContentModerationSystem
import json
from video_processor import VideoEditor

app = Flask(__name__)

@app.route('/process_video', methods=['POST'])
def process_video():
    if 'video' not in request.files or 'age' not in request.form:
        return "Missing video or age", 400

    video = request.files['video']
    age = request.form['age']

    # Sanitize the filename
    filename = secure_filename(video.filename)
    if not filename:
        return "Invalid filename", 400

    # Save the video to a temporary file with a unique name
    temp_dir = tempfile.gettempdir()
    unique_filename = str(uuid.uuid4()) + "_" + filename  # Generate a unique filename
    video_path = os.path.join(temp_dir, unique_filename)

    try:
        video.save(video_path)
    except Exception as e:
        return f"Error saving video: {str(e)}", 500

    # Process the video based on the age
    processed_video_path = process_video_based_on_age(video_path, age)

    # Return the processed video
    return send_file(processed_video_path, as_attachment=True, mimetype='video/mp4')

def process_video_based_on_age(video_path, age):
    cms = ContentModerationSystem()
    video_results = cms.process_content(video_path, age, 'video')
    json_results = []
    for frame_result in video_results:
        if frame_result['action'].lower() != 'allow':
            json_results.append({
                "timestamp": frame_result['timestamp'],
                "operation": frame_result['action'].lower()
            })
    print(json_results)
    editor = VideoEditor()
    operations_data = json_results
    operations = editor.load_operations(operations_data)
    editor.process_video_with_audio(video_path, 'output.mp4', operations)

    # Return the path to the processed video
    return 'output.mp4'

if __name__ == '__main__':
    app.run(debug=True)
