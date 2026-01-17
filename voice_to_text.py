#!/usr/bin/env python3
"""
Voice-to-Text Desktop Tool for Mac
Listens for Right Shift hotkey, records audio, transcribes with AWS Transcribe,
and pastes the result at cursor position.
"""

import io
import wave
import time
import threading
import tempfile
import os
import sys
import asyncio
from datetime import datetime

import pyaudio
import pyperclip
import boto3
from pynput import keyboard
from pynput.keyboard import Key, Controller, KeyCode
from amazon_transcribe.client import TranscribeStreamingClient
from amazon_transcribe.handlers import TranscriptResultStreamHandler
from amazon_transcribe.model import TranscriptEvent


class TranscriptHandler(TranscriptResultStreamHandler):
    """Custom handler for processing streaming transcription results"""

    def __init__(self, stream, callback):
        super().__init__(stream)
        self.callback = callback
        self.transcript = ""

    async def handle_transcript_event(self, transcript_event: TranscriptEvent):
        """Process incoming transcript events"""
        results = transcript_event.transcript.results

        for result in results:
            if not result.is_partial:
                # This is a final transcript
                for alt in result.alternatives:
                    self.transcript += alt.transcript + " "
                    # Call callback with final transcript
                    self.callback(self.transcript.strip())


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

        # Streaming transcription state
        self.transcription_result = None
        self.transcription_complete = threading.Event()

        # Keyboard controller for pasting
        self.kb_controller = Controller()

        # Hotkey combination: Right Shift key
        self.current_keys = set()
        self.hotkey_combination = {Key.shift_r}

        print("Voice-to-Text Tool initialized (Streaming Mode)")
        print("Press and hold Right Shift to record")
        print("Release to transcribe and paste")
        print("Press Ctrl+C to exit")

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
        """Process recorded audio using streaming transcription"""
        try:
            print("🔄 Processing audio...")

            # Reset transcription state
            self.transcription_result = None
            self.transcription_complete.clear()

            # Run async streaming transcription
            asyncio.run(self._stream_audio())

            # Wait for transcription to complete (with timeout)
            if self.transcription_complete.wait(timeout=10):
                if self.transcription_result:
                    # Paste the transcribed text
                    self._paste_text(self.transcription_result)
                    print(f"✅ Transcribed and pasted: {self.transcription_result}")
                else:
                    print("❌ No transcription result")
            else:
                print("❌ Transcription timeout")

        except Exception as e:
            print(f"❌ Error processing audio: {e}")

    async def _stream_audio(self):
        """Stream audio to AWS Transcribe using streaming API"""
        try:
            print("🔤 Starting streaming transcription...")

            # Get AWS region from session
            region = boto3.session.Session().region_name or "us-east-1"

            # Create transcribe streaming client
            client = TranscribeStreamingClient(region=region)

            # Audio generator to yield chunks
            async def audio_generator():
                # Convert recorded frames to PCM audio stream
                audio_data = b''.join(self.frames)
                chunk_size = 1024 * 8  # 8KB chunks

                for i in range(0, len(audio_data), chunk_size):
                    chunk = audio_data[i:i + chunk_size]
                    yield chunk
                    await asyncio.sleep(0.01)  # Small delay between chunks

            # Callback for handling transcript
            def on_transcript(text):
                self.transcription_result = text
                self.transcription_complete.set()

            # Start streaming transcription
            stream = await client.start_stream_transcription(
                language_code="en-US",
                media_sample_rate_hz=self.RATE,
                media_encoding="pcm",
            )

            # Create handler
            handler = TranscriptHandler(stream.output_stream, on_transcript)

            # Send audio and handle responses concurrently
            await asyncio.gather(
                self._write_audio_chunks(stream, audio_generator()),
                handler.handle_events()
            )

        except Exception as e:
            print(f"❌ Streaming transcription error: {e}")
            self.transcription_complete.set()

    async def _write_audio_chunks(self, stream, audio_generator):
        """Write audio chunks to the stream"""
        try:
            async for chunk in audio_generator:
                await stream.input_stream.send_audio_event(audio_chunk=chunk)
            # Signal end of audio stream
            await stream.input_stream.end_stream()
        except Exception as e:
            print(f"❌ Error writing audio chunks: {e}")

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
