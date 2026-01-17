#!/usr/bin/env python3
"""
Voice-to-Text Desktop Tool for Mac
Listens for Cmd+Shift+Space hotkey, records audio, transcribes with AWS Transcribe,
and pastes the result at cursor position.
"""

import io
import wave
import time
import threading
import tempfile
import os
import sys
from datetime import datetime

import pyaudio
import boto3
import pyperclip
from pynput import keyboard
from pynput.keyboard import Key, Controller


class VoiceToText:
    def __init__(self):
        # Audio recording settings
        self.CHUNK = 1024
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 16000  # 16kHz is optimal for speech recognition

        # Recording state
        self.is_recording = False
        self.frames = []
        self.audio = None
        self.stream = None

        # AWS clients
        self.s3_client = boto3.client('s3')
        self.transcribe_client = boto3.client('transcribe')

        # Get or create S3 bucket for temporary audio storage
        self.bucket_name = self._get_or_create_bucket()

        # Keyboard controller for pasting
        self.kb_controller = Controller()

        # Hotkey combination: Cmd+Shift+Space
        self.current_keys = set()
        self.hotkey_combination = {Key.cmd, Key.shift, Key.space}

        print("Voice-to-Text Tool initialized")
        print("Press and hold Cmd+Shift+Space to record")
        print("Release to transcribe and paste")
        print("Press Ctrl+C to exit")

    def _get_or_create_bucket(self):
        """Get or create an S3 bucket for temporary audio storage"""
        bucket_name = f"voice-to-text-temp-{boto3.client('sts').get_caller_identity()['Account']}"

        try:
            # Check if bucket exists
            self.s3_client.head_bucket(Bucket=bucket_name)
            print(f"Using existing S3 bucket: {bucket_name}")
        except:
            # Create bucket if it doesn't exist
            try:
                print(f"Creating S3 bucket: {bucket_name}")
                self.s3_client.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={'LocationConstraint': boto3.session.Session().region_name}
                    if boto3.session.Session().region_name != 'us-east-1' else {}
                )

                # Enable lifecycle policy to auto-delete objects after 1 day
                self.s3_client.put_bucket_lifecycle_configuration(
                    Bucket=bucket_name,
                    LifecycleConfiguration={
                        'Rules': [{
                            'Id': 'DeleteAfter1Day',
                            'Status': 'Enabled',
                            'Prefix': '',
                            'Expiration': {'Days': 1}
                        }]
                    }
                )
                print(f"Created S3 bucket with auto-delete policy: {bucket_name}")
            except Exception as e:
                print(f"Error creating bucket: {e}")
                print("Transcription will still work, but files won't be auto-deleted")

        return bucket_name

    def start_recording(self):
        """Start recording audio from microphone"""
        if self.is_recording:
            return

        print("\n🎤 Recording started...")
        self.is_recording = True
        self.frames = []

        try:
            self.audio = pyaudio.PyAudio()
            self.stream = self.audio.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RATE,
                input=True,
                frames_per_buffer=self.CHUNK,
                stream_callback=self._audio_callback
            )
            self.stream.start_stream()
        except Exception as e:
            print(f"❌ Error starting recording: {e}")
            self.is_recording = False
            if self.stream:
                self.stream.close()
            if self.audio:
                self.audio.terminate()

    def _audio_callback(self, in_data, frame_count, time_info, status):
        """Callback function to capture audio data"""
        if self.is_recording:
            self.frames.append(in_data)
        return (in_data, pyaudio.paContinue)

    def stop_recording(self):
        """Stop recording and process the audio"""
        if not self.is_recording:
            return

        self.is_recording = False
        print("⏹️  Recording stopped")

        # Stop and close the stream
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if self.audio:
            self.audio.terminate()

        # Check if we have any audio data
        if not self.frames:
            print("❌ No audio recorded")
            return

        # Process the recording in a separate thread
        threading.Thread(target=self._process_audio, daemon=True).start()

    def _process_audio(self):
        """Process recorded audio: save to WAV, transcribe, paste text"""
        try:
            print("🔄 Processing audio...")

            # Create WAV file in memory
            wav_buffer = io.BytesIO()
            wf = wave.open(wav_buffer, 'wb')
            wf.setnchannels(self.CHANNELS)
            wf.setsampwidth(pyaudio.PyAudio().get_sample_size(self.FORMAT))
            wf.setframerate(self.RATE)
            wf.writeframes(b''.join(self.frames))
            wf.close()

            # Get the WAV data
            wav_data = wav_buffer.getvalue()

            # Transcribe the audio
            transcribed_text = self._transcribe_audio(wav_data)

            if transcribed_text:
                # Paste the transcribed text
                self._paste_text(transcribed_text)
                print(f"✅ Transcribed and pasted: {transcribed_text}")
            else:
                print("❌ No transcription result")

        except Exception as e:
            print(f"❌ Error processing audio: {e}")

    def _transcribe_audio(self, wav_data):
        """Upload audio to S3 and transcribe using AWS Transcribe"""
        try:
            # Generate unique job name
            job_name = f"voice-to-text-{int(time.time() * 1000)}"
            s3_key = f"{job_name}.wav"

            # Upload to S3
            print(f"☁️  Uploading audio to S3...")
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=wav_data
            )

            # Start transcription job
            print("🔤 Starting transcription...")
            file_uri = f"s3://{self.bucket_name}/{s3_key}"

            self.transcribe_client.start_transcription_job(
                TranscriptionJobName=job_name,
                Media={'MediaFileUri': file_uri},
                MediaFormat='wav',
                LanguageCode='en-US'
            )

            # Wait for transcription to complete
            while True:
                status = self.transcribe_client.get_transcription_job(
                    TranscriptionJobName=job_name
                )
                job_status = status['TranscriptionJob']['TranscriptionJobStatus']

                if job_status == 'COMPLETED':
                    # Get the transcription result
                    transcript_uri = status['TranscriptionJob']['Transcript']['TranscriptFileUri']

                    # Download and parse the transcript
                    import json
                    import urllib.request
                    with urllib.request.urlopen(transcript_uri) as response:
                        transcript_data = json.loads(response.read().decode())

                    transcribed_text = transcript_data['results']['transcripts'][0]['transcript']

                    # Clean up S3 and transcription job
                    self._cleanup_aws_resources(job_name, s3_key)

                    return transcribed_text

                elif job_status == 'FAILED':
                    print(f"❌ Transcription failed: {status['TranscriptionJob'].get('FailureReason', 'Unknown error')}")
                    self._cleanup_aws_resources(job_name, s3_key)
                    return None

                # Wait a bit before checking again
                time.sleep(0.5)

        except Exception as e:
            print(f"❌ Transcription error: {e}")
            return None

    def _cleanup_aws_resources(self, job_name, s3_key):
        """Clean up S3 object and transcription job"""
        try:
            # Delete S3 object
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)

            # Delete transcription job
            self.transcribe_client.delete_transcription_job(TranscriptionJobName=job_name)
        except Exception as e:
            print(f"⚠️  Warning: Error cleaning up AWS resources: {e}")

    def _paste_text(self, text):
        """Paste text at current cursor position"""
        try:
            # Copy to clipboard
            pyperclip.copy(text)

            # Small delay to ensure clipboard is ready
            time.sleep(0.1)

            # Simulate Cmd+V to paste
            with self.kb_controller.pressed(Key.cmd):
                self.kb_controller.press('v')
                self.kb_controller.release('v')

        except Exception as e:
            print(f"❌ Error pasting text: {e}")

    def on_press(self, key):
        """Handle key press events"""
        self.current_keys.add(key)

        # Check if hotkey combination is pressed
        if self.hotkey_combination.issubset(self.current_keys):
            if not self.is_recording:
                self.start_recording()

    def on_release(self, key):
        """Handle key release events"""
        # If any key in the hotkey combination is released, stop recording
        if key in self.hotkey_combination and self.is_recording:
            self.stop_recording()

        # Remove from current keys
        try:
            self.current_keys.remove(key)
        except KeyError:
            pass

    def run(self):
        """Start the voice-to-text tool"""
        try:
            # Set up keyboard listener
            with keyboard.Listener(
                on_press=self.on_press,
                on_release=self.on_release
            ) as listener:
                listener.join()
        except KeyboardInterrupt:
            print("\n👋 Exiting...")
            sys.exit(0)


def main():
    """Main entry point"""
    try:
        app = VoiceToText()
        app.run()
    except KeyboardInterrupt:
        print("\n👋 Exiting...")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
