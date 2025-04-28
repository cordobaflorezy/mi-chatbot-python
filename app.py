from flask import Flask, request, jsonify
import os
import google.generativeai as genai
import subprocess
import tempfile
import whisper
import json
import re

app = Flask(__name__)

# --- Configuración de Gemini ---
google_api_key = os.environ.get("GOOGLE_API_KEY")
if google_api_key:
    genai.configure(api_key=google_api_key)
    try:
        model_gemini = genai.GenerativeModel('gemini-1.5-flash')
        print("✅ Modelo Gemini inicializado")
    except Exception as e:
        model_gemini = None
        print(f"❌ Error en Gemini: {e}")
else:
    model_gemini = None
    print("❌ GOOGLE_API_KEY no configurada")

# --- Funciones principales ---
def normalize_youtube_url(url):
    """Normaliza URLs de YouTube"""
    url = url.strip()
    
    # Si la URL no comienza con http(s) pero contiene dominio de YouTube
    if not url.startswith(('http://', 'https://')):
        if 'youtube.com' in url or 'youtu.be' in url:
            url = 'https://' + url.lstrip(':/')
        else:
            return None
    
    # Limpieza de parámetros adicionales
    url = re.sub(r'&.*$', '', url)  # Elimina parámetros después del ID
    return url

def descargar_audio(video_url, output_file):
    """Descarga audio usando yt-dlp"""
    try:
        command = [
            'yt-dlp',
            '-x',  # Extraer audio
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
        return False, "Tiempo de espera agotado (5 minutos)"
    except subprocess.CalledProcessError as e:
        return False, f"Error en yt-dlp: {e.stderr}"
    except Exception as e:
        return False, f"Error inesperado: {str(e)}"

def transcribir_audio(audio_file):
    """Transcribe audio usando Whisper"""
    try:
        model = whisper.load_model("base")
        result = model.transcribe(audio_file)
        return True, result["text"]
    except Exception as e:
        return False, f"Error en Whisper: {str(e)}"

# --- Endpoints ---
@app.route('/process_youtube', methods=['POST'])
def process_youtube_route():
    """Endpoint para procesar videos de YouTube"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Datos JSON no proporcionados', 'success': False}), 400
            
        video_url = data.get('youtube_url')
        chat_id = data.get('chatId')

        if not video_url:
            return jsonify({'error': 'URL no proporcionada', 'chatId': chat_id, 'success': False}), 400

        # Normalizar URL
        video_url = normalize_youtube_url(video_url)
        if not video_url:
            return jsonify({'error': 'URL de YouTube inválida', 'chatId': chat_id, 'success': False}), 400

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=True) as tmp_audio_file:
            # Descargar audio
            success, result = descargar_audio(video_url, tmp_audio_file.name)
            if not success:
                return jsonify({'error': result, 'chatId': chat_id, 'success': False}), 500

            # Transcribir audio
            success, transcription = transcribir_audio(tmp_audio_file.name)
            if not success:
                return jsonify({'error': transcription, 'chatId': chat_id, 'success': False}), 500

            return jsonify({
                'transcription': transcription,
                'chatId': chat_id,
                'success': True
            }), 200

    except Exception as e:
        return jsonify({'error': f'Error interno: {str(e)}', 'success': False}), 500

@app.route('/chatbot', methods=['POST'])
def chatbot_route():
    """Endpoint principal para Telegram"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Datos no proporcionados', 'success': False}), 400
            
        message_text = data.get('text', '').strip()
        chat_id = data.get('chatId')

        if not message_text:
            return jsonify({'error': 'Mensaje vacío', 'chatId': chat_id, 'success': False}), 400

        # Comando para procesar YouTube
        if message_text.startswith('/process_youtube'):
            # Extraer URL (soporta con/sin espacio)
            url_part = message_text[len('/process_youtube'):].strip()
            if ' ' in url_part:  # Si hay espacio después del comando
                video_url = url_part.split(' ', 1)[1].strip()
            else:
                video_url = url_part
            
            # Normalizar URL
            video_url = normalize_youtube_url(video_url)
            if not video_url:
                return jsonify({
                    'error': 'Formato incorrecto. Ejemplo: /process_youtube https://youtube.com/watch?v=ID',
                    'chatId': chat_id,
                    'success': False
                }), 400

            # Procesar con el endpoint existente
            request._cached_data = json.dumps({'youtube_url': video_url, 'chatId': chat_id})
            return process_youtube_route()
            
        # Chat normal con Gemini    
        elif model_gemini:
            try:
                response = model_gemini.generate_content(message_text)
                return jsonify({
                    'response': response.text,
                    'chatId': chat_id,
                    'success': True
                }), 200
            except Exception as e:
                return jsonify({
                    'error': f'Error en Gemini: {str(e)}',
                    'chatId': chat_id,
                    'success': False
                }), 500
        else:
            return jsonify({
                'error': 'Servicio de IA no disponible',
                'chatId': chat_id,
                'success': False
            }), 503

    except Exception as e:
        return jsonify({
            'error': f'Error interno: {str(e)}',
            'success': False
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint para verificar el estado del servicio"""
    return jsonify({
        'status': 'OK',
        'services': {
            'whisper': True,
            'gemini': model_gemini is not None,
            'yt-dlp': True
        }
    }), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
