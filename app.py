from flask import Flask, request, jsonify
import os
import re
import subprocess
import tempfile
import whisper
from urllib.parse import urlparse
import google.generativeai as genai
from threading import Lock

app = Flask(__name__)

# Configuración global
google_api_key = os.environ.get("GOOGLE_API_KEY")
if google_api_key:
    genai.configure(api_key=google_api_key)
    model_gemini = genai.GenerativeModel('gemini-1.5-flash')
else:
    model_gemini = None

# Cargar modelo Whisper una sola vez
whisper_model = whisper.load_model("base")
model_lock = Lock()

def extract_youtube_url(text):
    patterns = [
        r'(https?://(?:www\.)?youtube\.com/watch\?v=[a-zA-Z0-9_-]+)',
        r'(https?://(?:www\.)?youtube\.com/shorts/[a-zA-Z0-9_-]+)',
        r'(https?://youtu\.be/[a-zA-Z0-9_-]+)',
        r'(https?://(?:www\.)?youtube\.com/embed/[a-zA-Z0-9_-]+)',
        r'(?:/process_youtube|/chatbot)\s*(https?://[^\s]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            url = match.group(1) if len(match.groups()) > 0 else match.group(0)
            if 'youtube.com' in url or 'youtu.be' in url:
                return url.strip()
    return None

def descargar_audio(video_url):
    try:
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_file:
            temp_path = tmp_file.name
        
        command = [
            'yt-dlp',
            '-x',
            '--audio-format', 'mp3',
            '--no-warnings',
            '--quiet',
            '-o', temp_path,
            video_url
        ]
        
        result = subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=300
        )
        return True, temp_path
    except Exception as e:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        return False, str(e)

@app.route('/chatbot', methods=['POST'])
def chatbot_route():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided', 'success': False}), 400

        message_text = data.get('text', '').strip()
        chat_id = data.get('chatId')

        if not message_text or not chat_id:
            return jsonify({'error': 'Invalid request data', 'success': False}), 400

        video_url = extract_youtube_url(message_text)
        if not video_url:
            return jsonify({
                'error': 'No valid YouTube URL found',
                'chatId': chat_id,
                'success': False
            }), 400

        # Descargar audio
        download_success, audio_path = descargar_audio(video_url)
        if not download_success:
            return jsonify({
                'error': f'Audio download failed: {audio_path}',
                'chatId': chat_id,
                'success': False
            }), 500

        # Transcribir
        try:
            with model_lock:
                result = whisper_model.transcribe(audio_path)
            transcription = result["text"]
        except Exception as e:
            return jsonify({
                'error': f'Transcription failed: {str(e)}',
                'chatId': chat_id,
                'success': False
            }), 500
        finally:
            if os.path.exists(audio_path):
                os.unlink(audio_path)

        # Opcional: Procesar con Gemini
        summary = ""
        if model_gemini and transcription:
            try:
                response = model_gemini.generate_content(
                    f"Resume este contenido en 3 puntos clave:\n{transcription}"
                )
                summary = response.text
            except Exception:
                summary = "No se pudo generar resumen"

        return jsonify({
            'transcription': transcription,
            'summary': summary,
            'chatId': chat_id,
            'success': True
        }), 200

    except Exception as e:
        return jsonify({
            'error': f'Internal server error: {str(e)}',
            'success': False
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
