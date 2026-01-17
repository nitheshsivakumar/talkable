# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A lightweight macOS desktop application that converts speech to text using AWS Transcribe. Users press and hold Cmd+Shift+Space, speak, release, and the transcribed text automatically pastes at the cursor position in any application.

## Development Commands

### Setup and Installation

```bash
# Initial setup (installs dependencies, configures environment)
./setup.sh

# Or manual setup:
brew install portaudio
pip3 install -r requirements.txt
```

### Running the Application

```bash
# Start the application (uses virtual environment)
./run.sh

# Or run directly:
python3 voice_to_text.py
```

### Testing AWS Configuration

```bash
# Verify AWS credentials are configured
aws sts get-caller-identity

# Check AWS region
aws configure get region
```

## Architecture

### Core Components

**Single-file application** (`voice_to_text.py`) organized as a class-based design:

- **VoiceToText class**: Main application controller containing all functionality
- **Audio recording**: PyAudio-based recording with 16kHz sampling rate optimized for speech
- **Hotkey detection**: pynput keyboard listener monitoring Cmd+Shift+Space combination
- **AWS integration**: boto3 clients for S3 (temporary storage) and Transcribe (speech-to-text)
- **Auto-paste**: pyperclip + keyboard controller for clipboard-based text insertion

### Application Flow

1. **Initialization**: Creates/finds S3 bucket (`voice-to-text-temp-{account-id}`) with 1-day auto-delete lifecycle policy
2. **Hotkey monitoring**: Continuously listens for Cmd+Shift+Space press/release events
3. **Recording**: On hotkey press, streams audio from microphone into memory buffer
4. **Processing** (threaded): On hotkey release:
   - Converts recorded audio frames to WAV format (in-memory)
   - Uploads WAV to S3
   - Starts AWS Transcribe batch job
   - Polls for completion (0.5s intervals)
   - Retrieves transcript from results JSON
   - Cleans up S3 object and transcription job
5. **Pasting**: Copies text to clipboard and simulates Cmd+V keypress

### Key Design Decisions

- **Batch mode**: Uses AWS Transcribe batch API (not streaming), resulting in 2-5 second latency after recording
- **No persistence**: Audio and transcripts are never saved locally; S3 objects are deleted immediately
- **Threaded processing**: Audio processing runs in daemon thread to avoid blocking keyboard listener
- **In-memory WAV**: Audio is converted to WAV format without writing to disk
- **Clipboard-based pasting**: Uses system clipboard + Cmd+V simulation for universal app compatibility

## AWS Resources

### Auto-Created Resources

- **S3 Bucket**: `voice-to-text-temp-{aws-account-id}`
  - Region: Matches AWS CLI default region
  - Lifecycle: Objects auto-delete after 1 day (safety net)
  - Used for: Temporary audio file storage during transcription

- **Transcription Jobs**: Created per recording, immediately deleted after retrieval

### Required IAM Permissions

The AWS user/role needs:
- S3: CreateBucket, PutObject, DeleteObject, PutLifecycleConfiguration, HeadBucket
- Transcribe: StartTranscriptionJob, GetTranscriptionJob, DeleteTranscriptionJob
- STS: GetCallerIdentity (for bucket naming)

## Configuration

### Audio Settings (hardcoded in voice_to_text.py:26-30)

```python
CHUNK = 1024          # Buffer size for audio stream
FORMAT = paInt16      # 16-bit audio
CHANNELS = 1          # Mono recording
RATE = 16000          # 16kHz sample rate (optimal for speech recognition)
```

### Hotkey Combination (voice_to_text.py:48-50)

```python
# Current: Cmd+Shift+Space
self.hotkey_combination = {Key.cmd, Key.shift, Key.space}
```

### Transcription Language (voice_to_text.py:204)

```python
LanguageCode='en-US'  # US English only
```

## Dependencies

- **boto3**: AWS SDK for S3 and Transcribe API
- **pynput**: Cross-platform keyboard/mouse listener and controller
- **pyaudio**: Audio I/O library (requires PortAudio system library)
- **pyperclip**: Cross-platform clipboard operations

## Platform-Specific Notes

### macOS Requirements

- **Microphone permission**: System Preferences → Security & Privacy → Privacy → Microphone
- **Accessibility permission** (if needed): System Preferences → Security & Privacy → Privacy → Accessibility
- **PortAudio**: Must be installed via Homebrew for PyAudio to compile

### Not Cross-Platform

This application is Mac-specific due to:
- Hotkey combination uses `Key.cmd` (Command key)
- Paste operation simulates Cmd+V (Mac keyboard shortcut)
- Tested only on macOS

## Common Issues

### PyAudio Installation Failures

PyAudio requires PortAudio headers. If installation fails:

```bash
brew install portaudio
export LDFLAGS="-L/opt/homebrew/lib"
export CPPFLAGS="-I/opt/homebrew/include"
pip install pyaudio
```

### AWS Region Configuration

The S3 bucket creation handles `us-east-1` specially (no LocationConstraint needed). If bucket creation fails, check that AWS region is set:

```bash
aws configure get region
```

### No Audio Recorded

Common causes:
- Microphone not selected in System Preferences → Sound → Input
- Hotkey released too quickly (minimum ~1 second recording needed)
- Microphone permission not granted to terminal app

## Future Enhancement Notes

README.md mentions planned Version 2 features:
- Amazon Bedrock integration for text improvement
- Multi-language support (change LanguageCode parameter)
- Streaming transcription (switch from batch to streaming API)
- Menu bar app (requires macOS app framework, no terminal)
- Custom hotkey configuration (modify hotkey_combination set)
- Optional transcription history (requires data persistence layer)

## Alternative Implementation: Local Whisper Model

**Cost-saving alternative explored**: Replace AWS Transcribe with OpenAI Whisper (local, offline model)

### Benefits of Whisper Implementation
- **Cost**: Completely free (no AWS charges)
- **Speed**: 1-3 seconds processing (vs current 8-10 seconds with AWS batch)
- **Privacy**: Audio never leaves the computer
- **Offline**: Works without internet connection
- **Accuracy**: Comparable to AWS Transcribe

### Implementation Approach
1. Replace `boto3` dependency with `openai-whisper` package
2. Remove all AWS-related code (S3 upload, Transcribe job management, bucket creation)
3. Replace `_transcribe_audio()` method to use local Whisper model
4. Process audio directly from in-memory WAV buffer (no S3 upload needed)
5. Use Whisper with Metal acceleration on Apple Silicon for <1 second processing

### Model Size Options
- `tiny`: ~40MB, fastest, less accurate
- `base`: ~75MB, good balance
- `small`: ~150MB, better accuracy (recommended)
- `medium`: ~1.5GB, very accurate
- `large`: ~3GB, best accuracy

### Code Changes Required
```python
# Replace boto3 with whisper
import whisper

# In __init__:
self.model = whisper.load_model("small")  # One-time model load

# Replace _transcribe_audio() method:
def _transcribe_audio(self, wav_data):
    # Write to temp file for Whisper
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
        temp_audio.write(wav_data)
        temp_path = temp_audio.name

    result = self.model.transcribe(temp_path)
    os.unlink(temp_path)
    return result["text"]
```

### Tradeoffs
- **One-time download**: Model files (150MB-3GB depending on size)
- **CPU/GPU usage**: Uses local compute instead of cloud
- **No AWS infrastructure**: Eliminates S3 bucket, IAM permissions, etc.
