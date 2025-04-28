from flask import Flask, request, jsonify
import os
import re
import subprocess
import tempfile
import whisper
from urllib.parse import urlparse
import google.generativeai as genai

app = Flask(__name__)

# Configuración de Gemini (opcional, para el futuro)
google_api_key = os.environ.get("GOOGLE_API_KEY")
if google_api_key:
    genai.configure(api_key=google_api_key)
    model_gemini = genai.GenerativeModel('gemini-1.5-flash')
else:
    model_gemini = None

def extract_youtube_url(text):
    """
    Extrae URLs de YouTube de diferentes formatos, incluyendo después de comandos
    """
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

def descargar_audio(video_url, output_file):
    """Descarga audio usando yt-dlp con manejo robusto de errores"""
    try:
        command = [
            'yt-dlp',
            '-x',
            '--audio-format', 'mp3',
            '--no-warnings',
            '--quiet',
            '-o', output_file,
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
        return True, output_file
    except subprocess.TimeoutExpired:
        return False, "Tiempo de espera agotado"
    except subprocess.CalledProcessError as e:
        return False, f"Error en yt-dlp: {e.stderr}"
    except Exception as e:
        return False, f"Error inesperado: {str(e)}"

@app.route('/chatbot', methods=['POST'])
def chatbot_route():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided', 'success': False}), 400

        message_text = data.get('text', '').strip()
        chat_id = data.get('chatId')

        print(f"Received raw message: '{message_text}'")  # Depuración

        if not message_text:
            return jsonify({'error': 'Empty message', 'chatId': chat_id, 'success': False}), 400

        video_url = extract_youtube_url(message_text)

        if video_url:
            print(f"Extracted URL: {video_url}")  # Depuración
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=True) as tmp_audio_file:
                # Descargar audio
                success, result = descargar_audio(video_url, tmp_audio_file.name)
                if not success:
                    return jsonify({'error': f'Error al descargar el audio: {result}', 'chatId': chat_id, 'success': False}), 500

                # Transcribir audio
                try:
                    model = whisper.load_model("base")
                    transcription = model.transcribe(tmp_audio_file.name)["text"]
                    return jsonify({
                        'transcription': transcription,
                        'chatId': chat_id,
                        'success': True
                    }), 200
                except Exception as e:
                    return jsonify({'error': f'Error al transcribir el audio: {str(e)}', 'chatId': chat_id, 'success': False}), 500
        else:
            return jsonify({
                'error': 'No se encontró URL de YouTube válida',
                'chatId': chat_id,
                'success': False
            }), 200

    except Exception as e:
        return jsonify({'error': f'Error interno: {str(e)}', 'success': False}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
