import os
from flask import Flask, request, jsonify
import subprocess

app = Flask(__name__)

@app.route('/add_beep', methods=['POST'])
def add_beep():
    if 'audio' not in request.files or 'durations' not in request.json:
        return jsonify({"error": "Missing audio file or durations"}), 400

    audio_file = request.files['audio']
    durations = request.json['durations']
    
    # Save the uploaded audio file
    audio_filename = 'input_audio.wav'
    audio_file.save(audio_filename)

    # Generate beep sound
    beep_filename = 'beep.wav'
    subprocess.run([
        'ffmpeg', '-f', 'lavfi', '-i', 'sine=frequency=1000:duration=0.5',
        '-y', beep_filename
    ])

    # Parse durations and create filter_complex argument
    filter_complex = '[0:a]asplit=' + str(len(durations)) + ''.join([f'[a{i}]' for i in range(len(durations))]) + ';'
    for i, start_time in enumerate(durations):
        filter_complex += f'[a{i}]atrim=0:{start_time},asetpts=PTS-STARTPTS[a{i}start];'
        filter_complex += f'[a{i}]atrim={start_time}:{start_time + 0.5},asetpts=PTS-STARTPTS[a{i}beep];'
        filter_complex += f'[a{i}start][1:a][a{i}beep]concat=n=3:v=0:a=1[a{i}out];'

    filter_complex += ''.join([f'[a{i}out]' for i in range(len(durations))])
    filter_complex += f'concat=n={len(durations)}:v=0:a=1[outa]'

    # Run ffmpeg command to add beep sound
    output_filename = 'output_audio.wav'
    subprocess.run([
        'ffmpeg', '-i', audio_filename, '-i', beep_filename, 
        '-filter_complex', filter_complex, '-map', '[outa]', 
        '-y', output_filename
    ])

    return jsonify({"message": "Beep sound added successfully", "output_file": output_filename})

if __name__ == "__main__":
    app.run(debug=True,host='0.0.0.0',port=5000)