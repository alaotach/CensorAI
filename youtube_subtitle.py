import json
import g4f
import re
import time
import os
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

# ✅ List of abusive words (add more as needed)
ABUSIVE_WORDS = {"bc", "mc", "chutiya", "lodu", "gandu", "madarchod", "bhosdike", "chut", "gaand", "suar", "randi",
                 "harami", "kutte", "lavde", "lodu", "kamina", "ullu", "suar", "tatti", "bkl", "fattu", "sali",
                 "saala", "jhant", "tatte", "randi", "lund", "laude", "kutta", "kaminey", "behenchod", "bkl",
                 "teri maa", "loda"}

def extract_video_id(youtube_url):
    """Extract video ID from a YouTube URL"""
    match = re.search(r"(?:v=|youtu\.be/|embed/|shorts/|watch\?v=)([\w-]{11})", youtube_url)
    return match.group(1) if match else None

def detect_abusive_words(subtitles):
    """Detect abusive words using g4f AI + custom wordlist"""
    text = "\n".join([f"[{entry['start']}s] {entry['text']}" for entry in subtitles])

    system_prompt = (
        "Analyze the transcript carefully.\n"
        "Detect **all** abusive words (slangs, mild, and strong).\n"
        "Return **ONLY JSON** format, no markdown, no extra text.\n"
        "Each entry must include: abusive word, full sentence, word timestamp, and sentence start timestamp.\n"
        "Example JSON format:\n"
        "[{\"word\": \"bc\", \"sentence\": \"Arey bc kya kar raha hai?\", \"word_timestamp\": \"10.5s\", \"sentence_start_timestamp\": \"9.0s\"}]"
    )

    try:
        response = g4f.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ]
        )

        if not response or response.strip() == "":
            print("⚠️ g4f returned an empty response.")
            return []

        # 🔥 Extract JSON from response
        json_match = re.search(r"\[.*\]", response, re.DOTALL)
        if json_match:
            clean_response = json_match.group(0)  # Extract JSON part
        else:
            print("❌ g4f returned non-JSON output. Response:", response)
            return []

        # ✅ Parse JSON safely
        try:
            ai_detected_words = json.loads(clean_response)
        except json.JSONDecodeError:
            print("❌ Still invalid JSON. Response:", clean_response)
            return []

        # ✅ Check AI result + Manual abusive words matching
        final_results = []
        for entry in subtitles:
            sentence = entry["text"]
            start_timestamp = entry["start"]

            for word in ABUSIVE_WORDS:
                if re.search(rf"\b{word}\b", sentence, re.IGNORECASE):
                    final_results.append({
                        "word": word,
                        "sentence": sentence,
                        "word_timestamp": f"{start_timestamp}s",
                        "sentence_start_timestamp": f"{start_timestamp}s"
                    })

        # ✅ Combine AI + Manual Detection
        final_results.extend(ai_detected_words)
        return final_results

    except Exception as e:
        print(f"❌ g4f Error: {e}")
        return []

def get_youtube_subtitles(youtube_url):
    """Fetch subtitles (manual or auto-generated), detect abusive words, save results"""
    start_time = time.time()  # ⏳ Start timer

    video_id = extract_video_id(youtube_url)
    if not video_id:
        print("❌ Invalid YouTube URL!")
        return

    try:
        # 🔍 Get available subtitles
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        subtitles = None

        # ✅ Try manual subtitles first
        for transcript in transcript_list:
            if not transcript.is_generated:
                subtitles = transcript.fetch()
                print("📜 Using **manual** subtitles")
                break

        # ✅ If no manual subtitles, try auto-generated ones
        if not subtitles:
            for transcript in transcript_list:
                if transcript.is_generated:
                    subtitles = transcript.fetch()
                    print("🎙️ Using **auto-generated** subtitles")
                    break

        if not subtitles:
            print("❌ No subtitles available for this video.")
            return

        # Save full subtitles
        subtitles_filename = f"{video_id}_subtitles.json"
        with open(subtitles_filename, "w", encoding="utf-8") as file:
            json.dump(subtitles, file, indent=4, ensure_ascii=False)

        print(f"📜 Subtitles saved as {subtitles_filename}")

        # Detect abusive words
        abusive_words = detect_abusive_words(subtitles)

        # Save as JSON file
        json_filename = f"{video_id}_abusive_words.json"
        with open(json_filename, "w", encoding="utf-8") as file:
            json.dump(abusive_words, file, indent=4, ensure_ascii=False)

        end_time = time.time()  # ⏳ End timer
        execution_time = round(end_time - start_time, 2)  # Execution time in seconds

        print(f"🚫 Abusive words saved as {json_filename}")
        print(f"⏳ Execution Time: {execution_time} seconds")
        print(f"To open the files, run:\n\ncat {subtitles_filename}\ncat {json_filename}"
              if os.name != "nt" else f"type {subtitles_filename} & type {json_filename}")

    except TranscriptsDisabled:
        print("❌ Error: Subtitles are **disabled** for this video.")

    except NoTranscriptFound:
        print("❌ Error: No subtitles found, even auto-generated ones.")

    except Exception as e:
        print(f"❌ Unexpected Error: {e}")



youtube_url = "https://www.youtube.com/watch?v=WX7DBPcsiEs"  # Replace with your YouTube URL
get_youtube_subtitles(youtube_url)
