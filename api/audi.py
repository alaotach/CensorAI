from google.cloud import speech

def transcribe_gcs_with_word_time_offsets(audio_uri: str) -> dict:
    """Transcribe the given audio file asynchronously and output the word time
    offsets.
    Args:
        audio_uri (str): The Google Cloud Storage URI of the input audio file.
            E.g., gs://[BUCKET]/[FILE]
    Returns:
        dict: The response containing the transcription results with word time offsets.
    """
    from google.cloud import speech

    client = speech.SpeechClient()

    audio = speech.RecognitionAudio(uri=audio_uri)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=44100,  # Update to match the sample rate of the audio file
        language_code="en-US",
        enable_word_time_offsets=True,
    )

    operation = client.long_running_recognize(config=config, audio=audio)

    print("Waiting for operation to complete...")
    result = operation.result(timeout=90)

    transcription_result = {
        "results": []
    }
    print(result.results)
    for result in result.results:
        print(result)
        alternative = result.alternatives[0]
        words = []
        for word_info in alternative.words:
            words.append({
                "word": word_info.word,
                "start_time": word_info.start_time.total_seconds(),
                "end_time": word_info.end_time.total_seconds()
            })
        transcription_result["results"].append({
            "transcript": alternative.transcript,
            "confidence": alternative.confidence,
            "words": words
        })
        print(f"Transcript: {alternative.transcript}")
        print(f"Confidence: {alternative.confidence}")
    print(transcription_result)

    return transcription_result