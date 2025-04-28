from flask import Flask, request, jsonify
import os
import google.generativeai as genai
import subprocess
import tempfile
import whisper
import json
from datetime import datetime

app = Flask(__name__)

# --- Configuración de Gemini desde variable de entorno ---
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

# --- Funciones ---
def descargar_audio(video_url, output_file):
    try:
        command = [
            'yt-dlp',
            '-x',
            '--audio-format', 'mp3',
            '-o', output_file,
            video_url
        ]
        subprocess.run(command, check=True, capture_output=True, text=True)
        return True, output_file
    except subprocess.CalledProcessError as e:
        return False, f"Error al descargar el audio: {e.stderr}"
    except FileNotFoundError:
        return False, "Error: yt-dlp no se encontró. Asegúrate de que esté instalado."

def transcribir_audio(audio_file):
    try:
        model = whisper.load_model("base")  # Cambiado a 'base' para menos requisitos de hardware
        result = model.transcribe(audio_file)
        return True, result["text"]
    except Exception as e:
        return False, f"Error al transcribir el audio: {e}"

# --- Endpoints ---
@app.route('/process_youtube', methods=['POST'])
def process_youtube_route():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No se proporcionaron datos JSON', 'success': False}), 400
            
        video_url = data.get('youtube_url')
        chat_id = data.get('chatId')

        if not video_url:
            return jsonify({'error': 'No se proporcionó la URL de YouTube', 'chatId': chat_id, 'success': False}), 400

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=True) as tmp_audio_file:
            audio_file_path = tmp_audio_file.name
            print(f"Descargando audio de: {video_url}")
            descarga_exitosa, descarga_resultado = descargar_audio(video_url, audio_file_path)

            if descarga_exitosa:
                print("Audio descargado exitosamente. Transcribiendo...")
                transcripcion_exitosa, transcripcion_resultado = transcribir_audio(audio_file_path)
                if transcripcion_exitosa:
                    print("Transcripción completada.")
                    return jsonify({
                        'transcription': transcripcion_resultado, 
                        'chatId': chat_id,
                        'success': True
                    }), 200
                else:
                    print(f"Error en la transcripción: {transcripcion_resultado}")
                    return jsonify({
                        'error': f'Error en la transcripción: {transcripcion_resultado}',
                        'chatId': chat_id,
                        'success': False
                    }), 500
            else:
                print(f"Error en la descarga del audio: {descarga_resultado}")
                return jsonify({
                    'error': f'Error en la descarga del audio: {descarga_resultado}',
                    'chatId': chat_id,
                    'success': False
                }), 500
    except Exception as e:
        print(f"Error inesperado en /process_youtube: {str(e)}")
        return jsonify({
            'error': f'Error interno del servidor: {str(e)}',
            'success': False
        }), 500

@app.route('/chatbot', methods=['POST'])
def chatbot_route():
    """Endpoint específico para integración con Telegram"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No se proporcionaron datos JSON', 'success': False}), 400
            
        message_text = data.get('text', '')
        chat_id = data.get('chatId')

        if not message_text:
            return jsonify({'error': 'No se proporcionó texto', 'chatId': chat_id, 'success': False}), 400

        # Manejo de comandos de Telegram
        if message_text.startswith('/process_youtube'):
            # Extraer la URL del comando
            parts = message_text.split()
            if len(parts) < 2:
                return jsonify({
                    'error': 'Debes proporcionar una URL de YouTube después del comando',
                    'chatId': chat_id,
                    'success': False
                }), 400
                
            video_url = parts[1]
            # Reutilizamos la función process_youtube_route
            return process_youtube_route()
            
        elif model_gemini:
            try:
                response_gemini = model_gemini.generate_content(message_text)
                response_text = response_gemini.text
                return jsonify({
                    'response': response_text, 
                    'chatId': chat_id,
                    'success': True
                }), 200
            except Exception as e:
                error_message = f"Error al generar respuesta: {str(e)}"
                print(error_message)
                return jsonify({
                    'error': error_message, 
                    'chatId': chat_id,
                    'success': False
                }), 500
        else:
            error_message = "El modelo Gemini no está disponible"
            print(error_message)
            return jsonify({
                'error': error_message, 
                'chatId': chat_id,
                'success': False
            }), 503
    except Exception as e:
        print(f"Error inesperado en /chatbot: {str(e)}")
        return jsonify({
            'error': f'Error interno del servidor: {str(e)}',
            'success': False
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
