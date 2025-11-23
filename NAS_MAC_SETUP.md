# Setup Guide: Flask on Mac, HTML on NAS

This guide explains how to run the Flask API backend on your Mac and serve the HTML page from your NAS.

## Architecture

```
Internet → ngrok (Mac: 10.20.11.121) → Flask API (Mac: 10.20.11.121:8888)
                                         ↑
HTML Page (NAS: 10.20.11.34) ──────────┘
```

## Setup Instructions

### Step 1: Run Flask API on Mac

On your Mac (10.20.11.121), start the Flask API server:

```bash
cd /Users/wsun/Programming/bty_chtbt
python qa_lms_api.py
```

The API will be available at `http://10.20.11.121:8888`

Verify it's running:
```bash
curl http://10.20.11.121:8888/api/health
```

### Step 2: Setup ngrok on Mac (Optional - for internet access)

If you want to access the chatbot from the internet, run ngrok on your Mac:

```bash
cd /Users/wsun/Programming/bty_chtbt
./start_ngrok.sh
```

This will create a public URL like `https://abc123.ngrok-free.app` that tunnels to your Mac Flask API.

**Note:** If using ngrok, you'll need to update the API URL in `chat_standalone.html` (see Step 4).

### Step 3: Copy HTML File to NAS

Copy `chat_standalone.html` to your NAS (10.20.11.34). You can:

**Option A: Use SCP (if you have SSH access)**
```bash
scp chat_standalone.html user@10.20.11.34:/path/to/web/directory/
```

**Option B: Use NAS web interface**
- Log into your NAS web interface
- Navigate to your web directory
- Upload `chat_standalone.html`

**Option C: Use NAS file share**
- Mount your NAS share on Mac
- Copy the file to the web directory

### Step 4: Configure API Endpoint in HTML

Edit `chat_standalone.html` on your NAS and update the API endpoint:

**For local network access (Mac IP):**
```javascript
const API_BASE_URL = 'http://10.20.11.121:8888';
```

**For internet access via ngrok:**
```javascript
const API_BASE_URL = 'https://your-ngrok-url.ngrok-free.app';
```

**Note:** The HTML file already has logic to auto-detect if it's served from NAS (10.20.11.34) and use the Mac IP by default.

### Step 5: Serve HTML from NAS

**Option A: Using NAS built-in web server**
- Most NAS systems have a built-in web server
- Place `chat_standalone.html` in the web directory (usually `/web/` or `/www/`)
- Access at `http://10.20.11.34/chat_standalone.html`

**Option B: Using Python SimpleHTTPServer (temporary)**
```bash
# On NAS
cd /path/to/html/file
python3 -m http.server 8000
```
Access at `http://10.20.11.34:8000/chat_standalone.html`

**Option C: Using nginx/Apache**
- Configure your web server to serve static files
- Place HTML in web root directory

### Step 6: Access Your Chatbot

Open your browser and navigate to:
- Local: `http://10.20.11.34/chat_standalone.html` (or wherever you placed it)
- Internet (if using ngrok): `http://10.20.11.34/chat_standalone.html`

The HTML page will automatically make API calls to your Mac Flask backend!

## Configuration Summary

| Component | Location | URL/Address |
|-----------|----------|-------------|
| Flask API | Mac (10.20.11.121) | `http://10.20.11.121:8888` |
| HTML Page | NAS (10.20.11.34) | `http://10.20.11.34/chat_standalone.html` |
| ngrok Tunnel | Mac (10.20.11.121) | `https://your-url.ngrok-free.app` (optional) |

## Troubleshooting

### CORS Errors

If you see CORS errors in the browser console, make sure:
1. Flask API has CORS enabled (already configured in `qa_lms_api.py`)
2. The API URL in HTML matches exactly (including `http://` or `https://`)

### Connection Refused

If the HTML can't connect to the API:
1. Check Flask API is running on Mac: `curl http://10.20.11.121:8888/api/health`
2. Check firewall settings on Mac (port 8888 should be open)
3. Verify API URL in HTML matches your Mac's IP

### ngrok Issues

If using ngrok and it's not working:
1. Make sure ngrok is authenticated: `ngrok config add-authtoken YOUR_TOKEN`
2. Check ngrok is tunneling to correct port: `ngrok http 8888`
3. Update HTML with the correct ngrok URL

### Testing Connection

Test if HTML can reach Flask API:
```bash
# From NAS or any device on network
curl http://10.20.11.121:8888/api/health
```

Should return:
```json
{"status":"OK","model":"qwen2.5-7b-instruct-mlx","vector_store_loaded":true}
```

## Quick Start Commands

### Mac (Terminal 1): Start Flask API
```bash
cd /Users/wsun/Programming/bty_chtbt
python qa_lms_api.py
```

### Mac (Terminal 2): Start ngrok (optional)
```bash
cd /Users/wsun/Programming/bty_chtbt
ngrok http 8888
```

### NAS: Serve HTML
- Place `chat_standalone.html` in web directory
- Access via browser at `http://10.20.11.34/chat_standalone.html`

## Security Considerations

1. **Local Network Only**: For local network access, no additional security needed
2. **Internet Access via ngrok**: 
   - Consider adding basic authentication to Flask API
   - Use ngrok's built-in authentication features
   - Consider rate limiting
3. **HTTPS**: ngrok provides HTTPS automatically, but for local network you may want to use a reverse proxy

## Files Reference

- `qa_lms_api.py` - Flask API backend (runs on Mac)
- `chat_standalone.html` - HTML frontend (served from NAS)
- `start_ngrok.sh` - ngrok tunnel script (runs on Mac)

