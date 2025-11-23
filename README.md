Quick start (on your Mac)
Install and authenticate ngrok (if needed):
   brew install ngrok/ngrok/ngrok   ngrok config add-authtoken YOUR_AUTH_TOKEN
Start Flask app on NAS (10.20.11.34):
   python qa_lms_web.py
Start ngrok tunnel on your Mac (10.20.11.199):
   cd /Users/wsun/Programming/bty_chtbt   ./start_ngrok.sh
Access your chatbot — ngrok will show a public URL like https://abc123.ngrok-free.app