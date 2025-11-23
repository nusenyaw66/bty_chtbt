# Mac Setup Guide - NAS Chatbot with ngrok

## Quick Start

### Step 1: Install ngrok (if not already installed)

```bash
# Using Homebrew (recommended)
brew install ngrok/ngrok/ngrok

# Or download from https://ngrok.com/download
# Unzip and move to /usr/local/bin/
```

### Step 2: Authenticate ngrok (one-time setup)

```bash
ngrok config add-authtoken YOUR_AUTH_TOKEN
```

Get your auth token from: https://dashboard.ngrok.com/get-started/your-authtoken

### Step 3: Verify ngrok is installed

```bash
ngrok version
```

### Step 4: Start Flask App on NAS (10.20.11.34)

On your NAS, run:
```bash
cd /path/to/bty_chtbt
python qa_lms_web.py
```

The app should be accessible at `http://10.20.11.34:8888`

### Step 5: Start ngrok Tunnel on Mac (10.20.11.199)

In a new terminal on your Mac, run:
```bash
cd /Users/wsun/Programming/bty_chtbt
./start_ngrok.sh
```

Or manually:
```bash
ngrok http 10.20.11.34:8888
```

### Step 6: Access Your Chatbot

ngrok will display a public URL like:
```
Forwarding    https://abc123.ngrok-free.app -> http://10.20.11.34:8888
```

Open that HTTPS URL in your browser! 🎉

## Useful Commands

### Check ngrok status
Visit `http://127.0.0.1:4040` in your browser to see:
- All HTTP requests
- Request/response details
- Tunnel status

### Test NAS connection
```bash
curl http://10.20.11.34:8888/api/health
```

### Check if Flask app is running on NAS
```bash
ping 10.20.11.34
```

## Troubleshooting

### "ngrok: command not found"
- Make sure ngrok is in your PATH
- Try: `which ngrok`
- If using Homebrew: `brew list ngrok`

### "authtoken required"
- Run: `ngrok config add-authtoken YOUR_TOKEN`
- Get token from: https://dashboard.ngrok.com/get-started/your-authtoken

### Can't reach NAS
- Check network connectivity: `ping 10.20.11.34`
- Verify Flask app is running on NAS
- Check firewall settings

### Port already in use
- Check what's using port 8888: `lsof -i :8888`
- Change port in `qa_lms_web.py` if needed

## Running in Background

### Using tmux (recommended)
```bash
# Start a new tmux session
tmux new -s ngrok

# Run ngrok
./start_ngrok.sh

# Detach: Ctrl+B, then D
# Reattach: tmux attach -t ngrok
```

### Using nohup
```bash
nohup ./start_ngrok.sh > ngrok.log 2>&1 &
```

## Configuration

The script is configured for:
- NAS IP: `10.20.11.34`
- NAS Port: `8888`

To change these, edit `start_ngrok.sh` or pass directly:
```bash
ngrok http YOUR_NAS_IP:YOUR_PORT
```

