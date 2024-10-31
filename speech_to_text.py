import speech_recognition as sr
import os
from pydub import AudioSegment
from pydub.silence import split_on_silence
import tempfile
from pathlib import Path
from datetime import datetime
import time
import json

def list_mp3_files(directory: str) -> list:
    """Lists all MP3 files in the specified directory."""
    mp3_files = []
    try:
        if os.path.isfile(directory):
            directory = os.path.dirname(directory)
        for file in os.listdir(directory):
            if file.lower().endswith('.mp3'):
                mp3_files.append(file)
        return mp3_files
    except Exception as e:
        print(f"Error listing MP3 files: {str(e)}")
        return []

def select_file(directory: str) -> str:
    """Displays available MP3 files and lets user select one."""
    mp3_files = list_mp3_files(directory)
    if not mp3_files:
        print(f"No MP3 files found in {directory}")
        return None
    print("\nAvailable MP3 files:")
    for i, file in enumerate(mp3_files, 1):
        print(f"{i}. {file}")
    while True:
        try:
            choice = input("\nEnter the number of the file to process (or 'q' to quit): ")
            if choice.lower() == 'q':
                return None
            choice = int(choice)
            if 1 <= choice <= len(mp3_files):
                return os.path.join(directory, mp3_files[choice - 1])
            else:
                print(f"Please enter a number between 1 and {len(mp3_files)}")
        except ValueError:
            print("Please enter a valid number or 'q' to quit")

def transcribe_chunk(recognizer, audio_chunk, retries=3, delay=1):
    """Transcribes an audio chunk with retry logic."""
    for attempt in range(retries):
        try:
            text = recognizer.recognize_google(audio_chunk)
            return f"{text.capitalize()}. "
        except sr.UnknownValueError:
            return None
        except sr.RequestError as e:
            if attempt < retries - 1:
                print(f"Network error, retrying in {delay} seconds... (Attempt {attempt + 1}/{retries})")
                time.sleep(delay)
                delay *= 2  # Exponential backoff
            else:
                raise

def process_audio(path: str) -> str:
    """Converts speech in an audio file to text with robust error handling."""
    r = sr.Recognizer()
    
    try:
        print("\nLoading audio file...")
        audio = AudioSegment.from_mp3(path)
        
        if audio.channels > 1:
            audio = audio.set_channels(1)
        
        print("\nDetecting speech segments...")
        chunks = split_on_silence(
            audio,
            min_silence_len=500,
            silence_thresh=-40,
            keep_silence=100
        )
        
        print(f"Found {len(chunks)} segments to process")
        whole_text = []
        progress_file = "transcription_progress.json"
        
        # Load progress if exists
        start_index = 0
        if os.path.exists(progress_file):
            try:
                with open(progress_file, 'r') as f:
                    progress = json.load(f)
                    if progress.get('file') == path:
                        start_index = progress.get('last_chunk', 0)
                        whole_text = progress.get('text', [])
                        print(f"\nResuming from chunk {start_index + 1}")
            except Exception as e:
                print(f"Could not load progress file: {e}")

        # Process each chunk
        with tempfile.TemporaryDirectory() as folder_name:
            for i, chunk in enumerate(chunks[start_index:], start_index):
                chunk_duration = len(chunk) / 1000.0
                print(f"\nProcessing chunk {i+1}/{len(chunks)} (Duration: {chunk_duration:.2f}s)")
                
                try:
                    # Export chunk as WAV
                    chunk_filename = os.path.join(folder_name, f"chunk{i}.wav")
                    chunk.export(chunk_filename, format="wav")

                    # Recognize the chunk
                    with sr.AudioFile(chunk_filename) as source:
                        audio_listened = r.record(source)
                        
                        text = transcribe_chunk(r, audio_listened)
                        if text:
                            whole_text.append(text)
                            print(f"Transcribed: {text}")
                        else:
                            print("Could not understand audio in this chunk")

                    # Save progress
                    progress = {
                        'file': path,
                        'last_chunk': i,
                        'text': whole_text
                    }
                    with open(progress_file, 'w') as f:
                        json.dump(progress, f)

                except Exception as e:
                    print(f"\nError processing chunk {i+1}: {str(e)}")
                    print("Saving progress and continuing...")
                    continue

        # Clean up progress file
        if os.path.exists(progress_file):
            os.remove(progress_file)

        if not whole_text:
            return "No speech could be recognized in the audio file."
            
        return "".join(whole_text)

    except Exception as e:
        print(f"\nError processing audio: {str(e)}")
        raise

def txt_file(file_path: str):
    """Extracts text from an audio file and saves it to the same directory with progress tracking."""
    try:
        if os.path.isdir(file_path):
            selected_file = select_file(file_path)
            if not selected_file:
                print("No file selected. Exiting.")
                return
            file_path = selected_file
            
        print("\nStarting transcription process...")
        
        # Create a unique filename based on the input file
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        
        # Define the output path in the same directory as the input file
        output_dir = os.path.dirname(file_path)
        output = os.path.join(output_dir, f"{base_name}.txt")

        # Extract text from the audio file
        text = process_audio(file_path)

        # Write to the text file
        with open(output, "w") as file:
            file.write(text)

        print(f"\n\nTranscription complete! Check the directory for '{os.path.basename(output)}'")

    except Exception as e:
        print(f"\nError: {str(e)}")
        print("\nTroubleshooting tips:")
        print("1. Make sure the audio file path is correct")
        print("2. Check if you have an active internet connection")
        print("3. Verify the audio file isn't corrupted")
        print("4. Make sure you have ffmpeg installed")

if __name__ == "__main__":
    try:
        path = input("Give me the file/directory path: ")
        txt_file(path)
    except KeyboardInterrupt:
        print("\nProcess interrupted by user")
        print("Progress has been saved. You can resume by running the script again.")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {str(e)}")