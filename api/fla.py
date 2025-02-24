from flask import Flask, request, send_file
import os
import tempfile
import uuid
from werkzeug.utils import secure_filename
from makejson import ContentModerationSystem
from video_processor import VideoEditor
from audi import transcribe_gcs_with_word_time_offsets
from google.cloud import storage
from gpt import analyze_text_with_g4f
from pydub import AudioSegment

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
    unique_filename = str(uuid.uuid4()) + "_" + filename
    video_path = os.path.join(temp_dir, unique_filename)

    try:
        video.save(video_path)
    except Exception as e:
        return f"Error saving video: {str(e)}", 500

    # Process the video based on the age
    processed_video_path = process_video_based_on_age(video_path, age)

    # Extract audio from the processed video
    audio_path = extract_audio_from_video(processed_video_path)

    # Upload the audio to Google Cloud Storage
    gcs_uri = upload_to_gcs(audio_path)

    # Transcribe the audio
    transcription_result = transcribe_gcs_with_word_time_offsets(gcs_uri)

    # Analyze the transcription with GPT
    flagged_words = analyze_text_with_g4f(transcription_result)

    # Add beep sounds to the audio at flagged words
    final_video_path = add_beep_sounds(processed_video_path, flagged_words)

    # Return the processed video, transcription result, and flagged words
    return send_file(
            final_video_path,
            mimetype='video/mp4',
            as_attachment=True,
            download_name='processed_video.mp4'
        )
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

def extract_audio_from_video(video_path):
    """Extracts audio from the video and returns the path to the audio file."""
    audio_path = video_path.replace('.mp4', '.wav')
    os.system(f"ffmpeg -y -i {video_path} -vn -acodec pcm_s16le -ar 44100 -ac 1 {audio_path}")  # Convert to mono
    return audio_path

def upload_to_gcs(file_path):
    """Uploads a file to Google Cloud Storage and returns the URI."""
    client = storage.Client()
    bucket_name = 'audiofiles-censor'  # Replace with your bucket name
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(os.path.basename(file_path))
    blob.upload_from_filename(file_path)
    return f'gs://{bucket_name}/{blob.name}'

def add_beep_sounds(video_path, flagged_words):
    """Add beep sounds to the audio at flagged words."""
    # Extract audio from video
    audio_path = video_path.replace('.mp4', '.wav')
    os.system(f"ffmpeg -y -i {video_path} -q:a 0 -map a {audio_path}")

    # Load audio
    audio = AudioSegment.from_wav(audio_path)
    beep = AudioSegment.from_wav("beep.wav")  # Load a beep sound file

    # Add beep sounds at flagged words
    for word in flagged_words:
        start_time = word['start_time'] * 1000  # Convert to milliseconds
        end_time = word['end_time'] * 1000  # Convert to milliseconds
        audio = audio.overlay(beep, position=start_time, gain_during_overlay=-10)

    # Export the modified audio
    modified_audio_path = audio_path.replace('.wav', '_modified.wav')
    audio.export(modified_audio_path, format='wav')

    # Replace the audio in the video with the modified audio
    final_video_path = video_path.replace('.mp4', '_final.mp4')
    os.system(f"ffmpeg -y -i {video_path} -i {modified_audio_path} -c:v copy -map 0:v:0 -map 1:a:0 {final_video_path}")

    return final_video_path

if __name__ == '__main__':
    app.run(debug=True)