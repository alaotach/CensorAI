from flask import Flask, request, jsonify
from google.cloud import speech, storage
import g4f
import os

app = Flask(__name__)

# Set up GCP authentication
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "gcp-key.json"

def download_audio_from_gcs(bucket_name, source_blob_name, destination_file_name):
    """Download an audio file from GCS"""
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(source_blob_name)
    blob.download_to_filename(destination_file_name)
    return destination_file_name

def transcribe_audio(file_path):
    """Transcribe audio with timestamps using Google Speech-to-Text"""
    client = speech.SpeechClient()
    
    with open(file_path, "rb") as audio_file:
        content = audio_file.read()
    
    audio = speech.RecognitionAudio(content=content)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
        language_code="en-US",
        enable_word_time_offsets=True
    )
    
    response = client.recognize(config=config, audio=audio)
    
    transcript = []
    timestamps = []
    for result in response.results:
        sentence = " ".join([word_info.word for word_info in result.alternatives[0].words])
        start_time = result.alternatives[0].words[0].start_time.total_seconds()
        transcript.append({"sentence": sentence, "start_time": start_time})
        timestamps.append(start_time)
    
    return transcript, timestamps

def analyze_text_with_g4f(text_segments):
    """Analyze text using g4f in chunks of 100 sentences"""
    system_prompt = """Identify abusive, offensive, or 18+ content in sentences and return flagged words along with timestamps."""
    analyzed_results = []
    
    for i in range(0, len(text_segments), 100):
        chunk = text_segments[i:i+100]
        text_content = "\n".join([item["sentence"] for item in chunk])
        response = g4f.ChatCompletion.create(
            model=g4f.models.default,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text_content}
            ]
        )
        analyzed_results.append(response)
    
    return analyzed_results

@app.route('/process_audio', methods=['POST'])
def process_audio():
    data = request.json
    bucket_name = "duhack"
    source_blob_name = data.get('file_name')
    
    if not bucket_name or not source_blob_name:
        return jsonify({"error": "Missing parameters"}), 400
    
    local_audio_path = download_audio_from_gcs(bucket_name, source_blob_name, 'temp_audio.wav')
    transcript, timestamps = transcribe_audio(local_audio_path)
    analyzed_text = analyze_text_with_g4f(transcript)
    
    return jsonify({"transcript": transcript, "analyzed_text": analyzed_text, "timestamps": timestamps})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)