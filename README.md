# Voice-to-Text Desktop Tool for Mac

A lightweight Mac desktop application that converts speech to text using AWS Transcribe. Press and hold a hotkey, speak, release, and the transcribed text automatically appears at your cursor position.

## Features

- **Push-to-talk interface**: Press and hold Cmd+Shift+Space to record
- **Automatic transcription**: Uses AWS Transcribe for accurate speech-to-text
- **Seamless pasting**: Transcribed text appears at your cursor (works in any app)
- **No data persistence**: Audio and transcriptions are not saved
- **Background operation**: Runs continuously in the terminal

## Prerequisites

- **macOS** (tested on recent versions)
- **Python 3.7+**
- **AWS Account** with configured credentials
- **Microphone** access

## Installation

### 1. Install Python Dependencies

First, install PortAudio (required for PyAudio):

```bash
brew install portaudio
```

Then install Python packages:

```bash
pip install -r requirements.txt
```

**Note**: If you encounter issues installing PyAudio, you may need to install it separately:

```bash
pip install --upgrade pip setuptools wheel
pip install pyaudio
```

### 2. Configure AWS Credentials

This tool uses your existing AWS CLI credentials. Ensure you have:

- AWS CLI installed and configured (`aws configure`)
- An AWS account with access to:
  - **Amazon Transcribe**
  - **Amazon S3** (for temporary audio storage)

Verify your credentials:

```bash
aws sts get-caller-identity
```

### 3. Grant Microphone Permissions

When you first run the application, macOS will prompt you to grant microphone access to your terminal application (Terminal.app, iTerm2, etc.). Click **Allow**.

If you missed the prompt or need to change permissions:
1. Go to **System Preferences → Security & Privacy → Privacy → Microphone**
2. Enable access for your terminal application

## Usage

### Running the Application

Start the voice-to-text tool:

```bash
python voice_to_text.py
```

You should see:
```
Using existing S3 bucket: voice-to-text-temp-XXXXXXXXXXXX
Voice-to-Text Tool initialized
Press and hold Cmd+Shift+Space to record
Release to transcribe and paste
Press Ctrl+C to exit
```

### Recording and Transcribing

1. **Position your cursor** where you want text to appear (any application)
2. **Press and hold** `Cmd+Shift+Space`
3. **Speak** clearly into your microphone
4. **Release** the hotkey when done speaking
5. **Wait** 2-5 seconds for transcription to complete
6. The transcribed text will automatically paste at your cursor position

### Example Workflow

```
1. Open your text editor, browser, or any app
2. Click where you want to type
3. Hold Cmd+Shift+Space
4. Say: "This is a test of the voice to text application"
5. Release Cmd+Shift+Space
6. Text appears: "This is a test of the voice to text application"
```

### Stopping the Application

Press `Ctrl+C` in the terminal to exit.

## How It Works

1. **Hotkey Detection**: Listens for Cmd+Shift+Space using `pynput`
2. **Audio Recording**: Records from microphone using `PyAudio` at 16kHz
3. **AWS Upload**: Temporarily uploads audio to S3
4. **Transcription**: Uses AWS Transcribe to convert speech to text
5. **Auto-paste**: Copies to clipboard and simulates Cmd+V
6. **Cleanup**: Deletes S3 object and transcription job

## Troubleshooting

### "No audio recorded" message

- Ensure your microphone is connected and working
- Check System Preferences → Sound → Input to verify the correct microphone is selected
- Speak while holding the hotkey (don't release too quickly)

### AWS errors

- **Credentials error**: Run `aws configure` to set up credentials
- **Region not set**: Ensure AWS CLI has a default region configured
- **Permission denied**: Your AWS IAM user needs permissions for S3 and Transcribe

### Microphone permission denied

- Go to System Preferences → Security & Privacy → Privacy → Microphone
- Enable access for your terminal application
- Restart the terminal and try again

### PyAudio installation fails

On macOS, you may need to install PortAudio first:

```bash
brew install portaudio
export LDFLAGS="-L/opt/homebrew/lib"
export CPPFLAGS="-I/opt/homebrew/include"
pip install pyaudio
```

### Hotkey not working

- The hotkey combination is: **Cmd+Shift+Space** (all three keys together)
- Make sure you're holding all three keys before speaking
- Try restarting the application

### Paste not working

- The application uses Cmd+V to paste
- Ensure the target application supports standard paste commands
- Check that your cursor is positioned in an editable field

## AWS Resources

The tool automatically creates and manages:

- **S3 Bucket**: `voice-to-text-temp-{your-account-id}`
  - Auto-deletes objects after 1 day (lifecycle policy)
  - Used for temporary audio storage only

- **Transcription Jobs**: Automatically deleted after each transcription

### Manual Cleanup

If you want to remove the S3 bucket:

```bash
aws s3 rb s3://voice-to-text-temp-XXXXXXXXXXXX --force
```

## Cost Estimate

AWS Transcribe pricing (as of 2025):
- **$0.024 per minute** of audio (first 12 months with free tier)
- **Free tier**: 60 minutes per month for 12 months

S3 storage costs are minimal since files are deleted immediately.

Example: 100 transcriptions of 10 seconds each = ~17 minutes = **$0.41/month**

## Limitations

- **Batch mode**: Uses AWS Transcribe batch mode (not streaming), so there's a 2-5 second delay
- **English only**: Currently configured for US English (`en-US`)
- **Mac only**: Uses Mac-specific keyboard shortcuts and system integration
- **Terminal must be running**: Application runs in foreground terminal (not a true background daemon)

## Future Enhancements (Version 2)

- Amazon Bedrock integration for text improvement
- Support for other languages
- Streaming transcription for faster results
- True menu bar application (no terminal needed)
- Custom hotkey configuration
- Transcription history (optional)

## License

MIT License - Feel free to modify and use as needed.
