# Quick Start Guide

Everything is installed and ready to go!

## To Start the App

```bash
cd /Users/nitheshsivakumar/Documents/talkable
./run.sh
```

## How to Use

1. **Start the app** with the command above
2. You'll see a message: "Press and hold Cmd+Shift+Space to record"
3. **Open any app** (browser, VS Code, Notes, terminal, etc.)
4. **Click where you want to type**
5. **Press and hold** `Cmd+Shift+Space`
6. **Speak** into your microphone
7. **Release** the keys when done
8. **Wait** 2-5 seconds - text will automatically appear!

## To Stop the App

Press `Ctrl+C` in the terminal

## First Time Running

When you first run it, macOS may ask for:
- **Microphone permission** - Click "Allow"
- **Accessibility permission** - If it asks, go to System Preferences → Security & Privacy → Privacy → Accessibility and enable Terminal

## Example Test

1. Run `./run.sh`
2. Open TextEdit or any text app
3. Hold Cmd+Shift+Space and say "Hello world this is a test"
4. Release and wait - the text should appear!

## Troubleshooting

If you get errors:
- Make sure your microphone is connected
- Check System Preferences → Sound → Input to select the right mic
- Ensure AWS credentials are working: `aws sts get-caller-identity`

---

Ready to test? Just run `./run.sh` and try it out!
