import cv2
import numpy as np
from datetime import datetime
import json
import os
from typing import List, Dict
from moviepy.editor import VideoFileClip, AudioFileClip, VideoClip, concatenate_videoclips

class VideoOperation:
    def __init__(self, timestamp: str, operation: str, fps: float = 30.0):
        self.timestamp = timestamp
        self.operation = operation.lower()
        self.start_frame = None
        self.end_frame = None
        self.start_time = None
        self.end_time = None
        self.fps = fps
        self.duration = 1  # Duration in seconds

    def __str__(self):
        return f"Operation: {self.operation} at {self.timestamp} (Duration: {self.duration}s)"

class VideoEditor:
    def __init__(self):
        self.logger = []
        self.user = 'alaotach'
        self.current_time = "2025-02-23 13:06:54"
        self.fps = 25.0
        self.effect_duration = 1

    def log_message(self, message: str):
        """Add a log message with timestamp"""
        log_entry = f"[{self.current_time}] [{self.user}] {message}"
        print(log_entry)
        self.logger.append(log_entry)

    def timestamp_to_seconds(self, timestamp: str) -> float:
        """Convert timestamp (HH:MM:SS or HH:MM:SS.ffffff) to seconds"""
        try:
            try:
                time_obj = datetime.strptime(timestamp, '%H:%M:%S.%f')
                return time_obj.hour * 3600 + time_obj.minute * 60 + time_obj.second + time_obj.microsecond / 1000000.0
            except ValueError:
                time_obj = datetime.strptime(timestamp, '%H:%M:%S')
                return time_obj.hour * 3600 + time_obj.minute * 60 + time_obj.second
        except ValueError as e:
            self.log_message(f"Error parsing timestamp {timestamp}: {str(e)}")
            raise

    def load_operations(self, operations_data: List[Dict]) -> List[VideoOperation]:
        """Load operations from a list of dictionaries"""
        operations = []
        for op_data in operations_data:
            if 'timestamp' not in op_data or 'operation' not in op_data:
                self.log_message(f"Invalid operation data: {op_data}")
                continue
            if op_data['operation'].lower() not in ['blur', 'remove']:
                self.log_message(f"Invalid operation type: {op_data['operation']}")
                continue
            operations.append(VideoOperation(op_data['timestamp'], op_data['operation'], self.fps))
        return operations

    def apply_blur(self, frame):
        """Apply Gaussian blur to a frame"""
        return cv2.GaussianBlur(frame.astype(np.uint8), (99, 99), 0)

    def optimize_operations(self, operations: List[VideoOperation]) -> List[VideoOperation]:
        """Optimize operations by merging consecutive remove operations and preserving blur operations"""
        if not operations:
            return []

        # Sort operations by start time
        operations.sort(key=lambda x: x.start_time)
        optimized = []
        current = None

        for op in operations:
            if current is None:
                current = op
                continue

            # If there's a blur operation, we need to keep it separate
            if op.operation == 'blur':
                if current:
                    optimized.append(current)
                optimized.append(op)
                current = None
            # If current operation is blur, start a new segment
            elif current.operation == 'blur':
                optimized.append(current)
                current = op
            # If both are remove operations and they're close in time
            elif (op.operation == 'remove' and current.operation == 'remove' and 
                  abs(op.start_time - current.end_time) <= self.effect_duration * 1.1):  # Allow small gaps
                # Extend current remove operation
                current.end_time = op.end_time
                current.end_frame = op.end_frame
            else:
                optimized.append(current)
                current = op

        if current:
            optimized.append(current)

        self.log_message(f"Optimized {len(operations)} operations into {len(optimized)} operations")
        return optimized

    def get_video_segments(self, video: VideoFileClip, operations: List[VideoOperation]) -> List[VideoClip]:
        """Split video into segments based on optimized operations"""
        segments = []
        current_time = 0.0
        
        # Optimize operations
        operations = self.optimize_operations(operations)
        
        for op in operations:
            # Add segment before current operation if there's a gap
            if current_time < op.start_time - self.effect_duration * 0.5:  # Add small threshold
                segment = video.subclip(current_time, op.start_time)
                segments.append(segment)
                self.log_message(f"Added normal segment: {current_time:.3f}s - {op.start_time:.3f}s")

            # Handle the operation segment
            if op.operation == 'blur':
                segment = video.subclip(op.start_time, op.end_time)
                blurred_segment = segment.fl_image(self.apply_blur)
                segments.append(blurred_segment)
                self.log_message(f"Added blur segment: {op.start_time:.3f}s - {op.end_time:.3f}s")
                current_time = op.end_time
            elif op.operation == 'remove':
                self.log_message(f"Removing segment: {op.start_time:.3f}s - {op.end_time:.3f}s")
                current_time = op.end_time

        # Add final segment if there's remaining video
        if current_time < video.duration - self.effect_duration * 0.5:  # Add small threshold
            segment = video.subclip(current_time, video.duration)
            segments.append(segment)
            self.log_message(f"Added final segment: {current_time:.3f}s - {video.duration:.3f}s")

        return segments

    def process_video_with_audio(self, input_path: str, output_path: str, operations: List[VideoOperation]):
        """Process video with multiple operations while preserving audio"""
        self.log_message(f"Starting video processing with audio: {input_path}")

        try:
            # Load video with audio
            video = VideoFileClip(input_path)
            
            # Set video FPS if needed
            if video.fps != self.fps:
                self.log_message(f"Adjusting video FPS from {video.fps} to {self.fps}")
                video = video.set_fps(self.fps)

            # Convert timestamps to seconds and validate
            for op in operations:
                op.start_time = self.timestamp_to_seconds(op.timestamp)
                op.end_time = op.start_time + op.duration
                op.start_frame = int(op.start_time * self.fps)
                op.end_frame = int(op.end_time * self.fps)

            # Get optimized video segments
            segments = self.get_video_segments(video, operations)

            # Concatenate segments if any exist
            if segments:
                final_video = concatenate_videoclips(segments) if len(segments) > 1 else segments[0]

                # Write output video with audio
                self.log_message("Writing final video with audio...")
                final_video.write_videofile(
                    output_path,
                    codec='libx264',
                    audio_codec='aac',
                    temp_audiofile='temp-audio.m4a',
                    remove_temp=True,
                    fps=self.fps
                )

                final_video.close()
            else:
                self.log_message("No segments to process - all content was removed")

            # Cleanup
            video.close()
            self.log_message(f"Video processing completed: {output_path}")
            return True

        except Exception as e:
            self.log_message(f"Error processing video: {str(e)}")
            return False

def main():
    # First, ensure required packages are installed
    try:
        import moviepy
    except ImportError:
        print("Installing required packages...")
        os.system('pip install moviepy')
        os.system('apt-get update && apt-get install -y ffmpeg')

    editor = VideoEditor()

    # Interactive input
    while True:
        print("\nVideo Editor Menu:")
        print("1. Process video with operations from JSON file")
        print("2. Add operations interactively")
        print("3. Exit")

        choice = input("Select an option (1-3): ")

        if choice == '1':
            input_video = input("Enter input video path: ")
            output_video = input("Enter output video path: ")
            json_path = input("Enter JSON file path with operations: ")

            try:
                with open(json_path, 'r') as f:
                    operations_data = json.load(f)
                operations = editor.load_operations(operations_data)
                editor.process_video_with_audio(input_video, output_video, operations)
            except Exception as e:
                editor.log_message(f"Error: {str(e)}")

        elif choice == '2':
            operations_data = []
            input_video = input("Enter input video path: ")
            output_video = input("Enter output video path: ")

            while True:
                timestamp = input("Enter timestamp (HH:MM:SS or HH:MM:SS.ffffff) or 'done' to finish: ")
                if timestamp.lower() == 'done':
                    break

                operation = input("Enter operation (blur/remove): ")
                operations_data.append({
                    "timestamp": timestamp,
                    "operation": operation
                })

            operations = editor.load_operations(operations_data)
            editor.process_video_with_audio(input_video, output_video, operations)

        elif choice == '3':
            print("Exiting...")
            break

        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()