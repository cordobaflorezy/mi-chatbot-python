from flask import Flask, request, jsonify
import os
import google.generativeai as genai
import subprocess
import tempfile
import whisper
import json
from datetime import datetime

app = Flask(__name__)

# --- Configuración de Gemini ---
google_api_key = os.environ.get("GOOGLE_API_KEY")
print(f"Clave de API de Gemini obtenida: {'Sí' if google_api_key else 'No'}")

if google_api_key:
    genai.configure(api_key=google_api_key)
    try:
        model_gemini = genai.GenerativeModel('gemini-1.5-flash')
        print("Modelo Gemini inicializado correctamente.")
    except Exception as e:
        model_gemini = None
        print(f"Error al inicializar el modelo Gemini: {e}")
else:
    model_gemini = None
    print("Error: La variable de entorno GOOGLE_API_KEY no está configurada.")

# --- Funciones auxiliares ---
def descargar_audio(video_url, output_file):
    try:
        if not video_url.startswith(('http://', 'https://')):
            return False, "URL debe comenzar con http:// o https://"

        command = [
            'yt-dlp',
            '-x',
            '--audio-format', 'mp3',
            '--no-warnings',
            '-o', output_file,
            video_url
        ]
        
        result = subprocess.run(command, check=True, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            return False, f"Error en yt-dlp: {result.stderr}"
            
        return True, output_file
    except subprocess.TimeoutExpired:
        return False, "Tiempo de espera agotado al descargar (5 minutos)"
    except subprocess.CalledProcessError as e:
        return False, f"Error en yt-dlp (code {e.returncode}): {e.stderr}"
    except Exception as e:
        return False, f"Error inesperado: {str(e)}"

def transcribir_audio(audio_file):
    try:
        model = whisper.load_model("base")
        result = model.transcribe(audio_file)
        return True, result["text"]
    except Exception as e:
        return False, f"Error al transcribir: {str(e)}"

# --- Endpoints principales ---
@app.route('/process_youtube', methods=['POST'])
def process_youtube_route():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No se proporcionaron datos JSON', 'success': False}), 400
            
        video_url = data.get('youtube_url')
        chat_id = data.get('chatId')

        if not video_url:
            return jsonify({'error': 'No se proporcionó URL', 'chatId': chat_id, 'success': False}), 400

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=True) as tmp_audio_file:
            audio_file_path = tmp_audio_file.name
            
            # Descargar audio
            success, result = descargar_audio(video_url, audio_file_path)
            if not success:
                return jsonify({
                    'error': f'Error en descarga: {result}',
                    'chatId': chat_id,
                    'success': False
                }), 500

            # Transcribir audio
            success, transcription = transcribir_audio(audio_file_path)
            if not success:
                return jsonify({
                    'error': f'Error en transcripción: {transcription}',
                    'chatId': chat_id,
                    'success': False
                }), 500

            return jsonify({
                'transcription': transcription,
                'chatId': chat_id,
                'success': True
            }), 200

    except Exception as e:
        print(f"Error inesperado: {str(e)}")
        return jsonify({
            'error': f'Error interno: {str(e)}',
            'success': False
        }), 500

@app.route('/chatbot', methods=['POST'])
def chatbot_route():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No se proporcionaron datos JSON', 'success': False}), 400
            
        message_text = data.get('text', '').strip()
        chat_id = data.get('chatId')

        if not message_text:
            return jsonify({'error': 'No se proporcionó mensaje', 'chatId': chat_id, 'success': False}), 400

        # Procesamiento de comandos
        if message_text.startswith('/process_youtube'):
            # Extraer URL (admite con o sin espacio)
            if ' ' in message_text:
                video_url = message_text.split(' ')[1]
            else:
                video_url = message_text[len('/process_youtube'):]
            
            video_url = video_url.strip()
            
            if not video_url:
                return jsonify({
                    'error': 'Formato incorrecto. Usa: /process_youtube<URL> o /process_youtube <URL>',
                    'chatId': chat_id,
                    'success': False
                }), 400

            if not video_url.startswith(('http://', 'https://')):
                return jsonify({
                    'error': 'URL inválida. Debe comenzar con http:// o https://',
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
        print(f"Error en chatbot: {str(e)}")
        return jsonify({
            'error': f'Error interno: {str(e)}',
            'success': False
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
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
    app.run(host='0.0.0.0', port=port, debug=True)
