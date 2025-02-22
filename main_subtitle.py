import json
import g4f
import re
import time
from flask import Flask, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

app = Flask(__name__)

# ✅ List of abusive words
ABUSIVE_WORDS = {"bc", "mc", "chutiya", "lodu", "gandu", "madarchod", "bhosdike", "chut", "gaand", "suar", "randi",
                 "harami", "kutte", "lavde", "kamina", "ullu", "suar", "tatti", "bkl", "fattu", "sali", "saala", "jhant",
                 "tatte", "randi", "lund", "laude", "kutta", "kaminey", "behenchod", "teri maa", "loda"}

def extract_video_id(youtube_url):
    """Extract video ID from a YouTube URL"""
    match = re.search(r"(?:v=|youtu\.be/|embed/|shorts/|watch\?v=)([\w-]{11})", youtube_url)
    return match.group(1) if match else None

def detect_abusive_words(subtitles):
    """Detect abusive words using AI + wordlist"""
    text = "\n".join([entry["text"] for entry in subtitles])

    system_prompt = (
        "Analyze the transcript carefully.\n"
        "Detect **all** abusive words (slangs, mild, and strong).\n"
        "Return **ONLY JSON**, no markdown, no extra text.\n"
        "Each entry must include: abusive word and its timestamp.\n"
    )

    try:
        response = g4f.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": text}]
        )

        if not response or response.strip() == "":
            return []

        json_match = re.search(r"\[.*\]", response, re.DOTALL)
        if json_match:
            clean_response = json_match.group(0)
        else:
            return []

        try:
            ai_detected_words = json.loads(clean_response)
        except json.JSONDecodeError:
            return []

        # ✅ Manual abusive word detection
        final_results = []
        for entry in subtitles:
            sentence = entry["text"]
            start_timestamp = entry["start"]

            for word in ABUSIVE_WORDS:
                if re.search(rf"\b{word}\b", sentence, re.IGNORECASE):
                    final_results.append({"word": word, "timestamp": f"{start_timestamp}s"})

        final_results.extend(ai_detected_words)
        return final_results

    except Exception:
        return []

def get_youtube_subtitles(youtube_url, lang="hi"):
    """Fetch subtitles and detect abusive words"""
    video_id = extract_video_id(youtube_url)
    if not video_id:
        return None, "Invalid YouTube URL!"

    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=[lang])
        abusive_words = detect_abusive_words(transcript)
        return abusive_words, None
    except (TranscriptsDisabled, NoTranscriptFound):
        return None, "Subtitles are disabled or unavailable!"
    except Exception as e:
        return None, str(e)

@app.route('/analyze', methods=['POST'])
def analyze_video():
    start_time = time.time()
    data = request.get_json()
    
    youtube_url = data.get("youtube_url")
    user_age = data.get("user_age")

    if not youtube_url or not isinstance(user_age, int):
        return jsonify({"error": "Invalid input! Provide a valid YouTube URL and user age."}), 400

    abusive_words, error = get_youtube_subtitles(youtube_url)

    if error:
        return jsonify({"error": error}), 400

    abusive_count = len(abusive_words)

    # ✅ Age-based filtering
    if user_age < 12:
        allowed = False
    elif 12 <= user_age < 16:
        allowed = abusive_count < 5
    else:
        allowed = True

    end_time = time.time()
    execution_time = round(end_time - start_time, 2)

    return jsonify({
        "youtube_url": youtube_url,
        "user_age": user_age,
        "abusive_word_count": abusive_count,
        "allowed_to_watch": allowed,
        "execution_time": execution_time
    })

if __name__ == '__main__':
    app.run(debug=True)
