from flask import Flask, request, jsonify
import os
import re
from urllib.parse import urlparse

app = Flask(__name__)

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
        # Removed the specific googleusercontent check
        return url_part
    except:
        return None

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

            return jsonify({
                'extracted_url': video_url,
                'chatId': chat_id,
                'success': True
            }), 200

        # Resto de la lógica para otros comandos...
        return jsonify({'message': 'Command not recognized', 'chatId': chat_id, 'success': False}), 200

    except Exception as e:
        return jsonify({'error': f'Internal error: {str(e)}', 'success': False}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
