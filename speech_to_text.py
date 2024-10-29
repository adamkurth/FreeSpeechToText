import speech_recognition as sr
import os
from pydub import AudioSegment
from pydub.silence import split_on_silence
import tempfile
from datetime import datetime

def list_mp3_files(directory: str) -> list:
    """
    Lists all MP3 files in the specified directory.
    """
    mp3_files = []
    try:
        # If a file path is provided, use its directory
        if os.path.isfile(directory):
            directory = os.path.dirname(directory)
            
        # Get all MP3 files
        for file in os.listdir(directory):
            if file.lower().endswith('.mp3'):
                mp3_files.append(file)
                
        return mp3_files
    except Exception as e:
        print(f"Error listing MP3 files: {str(e)}")
        return []

def select_file(directory: str) -> str:
    """
    Displays available MP3 files and lets user select one.
    """
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
                selected_file = mp3_files[choice - 1]
                return os.path.join(directory, selected_file)
            else:
                print(f"Please enter a number between 1 and {len(mp3_files)}")
        except ValueError:
            print("Please enter a valid number or 'q' to quit")

def validate_audio_file(path: str) -> bool:
    """
    Validates that an audio file exists and can be opened.
    """
    try:
        if not os.path.exists(path):
            print(f"File not found: {path}")
            return False
            
        # Get file info
        print(f"File size: {os.path.getsize(path) / (1024*1024):.2f} MB")
        
        # Try to load with pydub
        audio = AudioSegment.from_mp3(path)
        duration = len(audio) / 1000.0  # Convert to seconds
        print(f"Audio file duration: {duration:.2f} seconds")
        print(f"Channels: {audio.channels}")
        print(f"Sample width: {audio.sample_width} bytes")
        print(f"Frame rate: {audio.frame_rate} Hz")
        
        return True
        
    except Exception as e:
        print(f"Error validating audio file: {str(e)}")
        return False

def process_audio(path: str) -> str:
    """
    Converts speech in an audio file to text using pydub for audio processing.
    """
    r = sr.Recognizer()
    
    try:
        print("\nValidating audio file...")
        if not validate_audio_file(path):
            raise ValueError("Invalid or empty audio file")

        print("\nLoading audio file...")
        audio = AudioSegment.from_mp3(path)
        
        # Convert to mono if stereo
        if audio.channels > 1:
            audio = audio.set_channels(1)
        
        print("\nDetecting speech segments...")
        chunks = split_on_silence(
            audio,
            min_silence_len=500,  # minimum length of silence (ms)
            silence_thresh=-40,    # threshold for silence (dB)
            keep_silence=100       # keep some silence at chunk boundaries
        )
        
        print(f"Found {len(chunks)} segments to process")
        whole_text = []

        # Process each chunk
        with tempfile.TemporaryDirectory() as folder_name:
            for i, chunk in enumerate(chunks):
                chunk_duration = len(chunk) / 1000.0
                print(f"\nProcessing chunk {i+1}/{len(chunks)} (Duration: {chunk_duration:.2f}s)")
                
                # Export chunk as WAV
                chunk_filename = os.path.join(folder_name, f"chunk{i}.wav")
                chunk.export(chunk_filename, format="wav")

                # Recognize the chunk
                with sr.AudioFile(chunk_filename) as source:
                    audio_listened = r.record(source)
                    
                    try:
                        text = r.recognize_google(audio_listened)
                        text = f"{text.capitalize()}. "
                        whole_text.append(text)
                        print(f"Transcribed: {text}")
                    except sr.UnknownValueError:
                        print("Could not understand audio in this chunk")
                        continue
                    except sr.RequestError as e:
                        print(f"Network error in speech recognition: {str(e)}")
                        continue

        if not whole_text:
            return "No speech could be recognized in the audio file."
            
        return "".join(whole_text)

    except Exception as e:
        print(f"\nError processing audio: {str(e)}")
        raise

def txt_file(file_path: str):
    """
    Extracts text from an audio file and saves it to Desktop.
    """
    try:
        # If it's a directory, let user select a file
        if os.path.isdir(file_path):
            selected_file = select_file(file_path)
            if not selected_file:
                print("No file selected. Exiting.")
                return
            file_path = selected_file
            
        print("\nStarting transcription process...")
        
        # Define output path on the Desktop
        output = os.path.join(os.path.expanduser('~'), 'Desktop', "Extracted Text.txt")

        # Extract text from the audio file
        text = process_audio(file_path)

        # Write to the text file
        with open(output, "w") as file:
            file.write(text)

        print("\n\nTranscription complete! Check your Desktop for 'Extracted Text.txt'")

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
    except Exception as e:
        print(f"\nAn unexpected error occurred: {str(e)}")