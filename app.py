from flask import Flask, request, jsonify
import os
import google.generativeai as genai
import subprocess
import tempfile
import whisper
import json
import re
from urllib.parse import urlparse

app = Flask(__name__)

# Configuración de Gemini
google_api_key = os.environ.get("GOOGLE_API_KEY")
if google_api_key:
    genai.configure(api_key=google_api_key)
    model_gemini = genai.GenerativeModel('gemini-1.5-flash')
else:
    model_gemini = None

def extract_youtube_url(command_text):
    """
    Extrae la URL de YouTube del comando de Telegram de manera robusta
    """
    # Elimina el comando y cualquier espacio sobrante
    url_part = re.sub(r'^/process_youtube\s*', '', command_text).strip()
    
    # Si la URL no comienza con http(s), intenta corregirla
    if not url_part.startswith(('http://', 'https://')):
        if 'youtube.com' in url_part or 'youtu.be' in url_part:
            url_part = 'https://' + url_part.lstrip(':/')
        else:
            return None
    
    # Validación adicional de la URL
    try:
        parsed = urlparse(url_part)
        if not all([parsed.scheme, parsed.netloc]):
            return None
        if 'youtube.com' not in parsed.netloc and 'youtu.be' not in parsed.netloc:
            return None
        return url_part
    except:
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

        if not message_text:
            return jsonify({'error': 'Empty message', 'chatId': chat_id, 'success': False}), 400

        # Procesamiento de comandos de YouTube
        if message_text.lower().startswith('/process_youtube'):
            video_url = extract_youtube_url(message_text)
            if not video_url:
                return jsonify({
                    'error': 'Formato inválido. Use: /process_youtube <URL> o /process_youtube<URL>',
                    'chatId': chat_id,
                    'success': False
                }), 400

            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=True) as tmp_audio_file:
                # Descargar audio
                success, result = descargar_audio(video_url, tmp_audio_file.name)
                if not success:
                    return jsonify({'error': result, 'chatId': chat_id, 'success': False}), 500

                # Transcribir audio
                model = whisper.load_model("base")
                transcription = model.transcribe(tmp_audio_file.name)["text"]
                
                return jsonify({
                    'transcription': transcription,
                    'chatId': chat_id,
                    'success': True
                }), 200

        # Resto de la lógica para otros comandos...
        
    except Exception as e:
        return jsonify({'error': f'Internal error: {str(e)}', 'success': False}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
