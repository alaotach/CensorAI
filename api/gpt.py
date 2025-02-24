from g4f import Client
import json
client = Client()

def analyze_text_with_g4f(transcription_result):
    """Analyze text using g4f in chunks of 100 sentences"""
    analyzed_results = []
    
    # Define offensive/inappropriate words (can be expanded)
    offensive_words = {
        'explicit': ['fuck', 'shit', 'dick', 'pussy', 'cock', 'ass'],
        'violent': ['kill', 'murder', 'shoot', 'beat'],
        'inappropriate': ['suck', 'strip', 'blow']
    }

    for result in transcription_result['results']:
        words = result.get('words', [])
        
        for word_info in words:
            word = word_info['word'].lower()
            
            # Check if word is in any offensive category
            for category, word_list in offensive_words.items():
                if word in word_list:
                    analyzed_results.append({
                        "word": word_info['word'],
                        "category": category,
                        "start_time": float(word_info['start_time']),
                        "end_time": float(word_info['end_time'])
                    })
                    break

        # Also analyze context using g4f
        full_text = result.get('transcript', '')
        if full_text:
            system_prompt = """
            Analyze the text for inappropriate content. You must respond ONLY in this format:
            word,start_time,end_time

            Rules:
            1. Each line must contain exactly 3 comma-separated values
            2. If no inappropriate content is found, respond with: NONE
            3. DO NOT add any explanations or additional text
            4. Times must be numbers (float or integer)
            5. Use the word timings from the original text

            Example response for inappropriate content:
            fuck,1.2,1.8
            shit,3.4,3.9

            Example response for clean content:
            NONE
            """

            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": full_text + "\n\nWord timings:\n" + str(words)}
                ]
            )
            
            try:
                gpt_response = response.choices[0].message.content.strip()
                if gpt_response and gpt_response != "NONE":
                    for line in gpt_response.split('\n'):
                        if not line.strip():
                            continue
                        try:
                            parts = line.strip().split(',')
                            if len(parts) == 3:
                                word, start_time, end_time = parts
                                analyzed_results.append({
                                    "word": word.strip(),
                                    "category": "gpt_flagged",
                                    "start_time": float(start_time.strip()),
                                    "end_time": float(end_time.strip())
                                })
                        except ValueError as e:
                            print(f"Error processing line '{line}': {e}")
            except (KeyError, ValueError) as e:
                print(f"Error processing GPT response: {e}")
                print(f"Raw response: {response}")

    print(f"Found {len(analyzed_results)} flagged words")
    return analyzed_results