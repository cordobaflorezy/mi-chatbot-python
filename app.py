from flask import Flask, request, jsonify
import os
import re
from urllib.parse import urlparse

app = Flask(__name__)

def extract_youtube_url(text):
    """
    Extrae URLs de YouTube de diferentes formatos, incluyendo después de comandos
    """
    # Patrones mejorados que ignoran espacios y caracteres especiales
    patterns = [
        r'(https?://(?:www\.)?youtube\.com/watch\?v=[a-zA-Z0-9_-]+)',  # URL normal
        r'(https?://(?:www\.)?youtube\.com/shorts/[a-zA-Z0-9_-]+)',     # Shorts
        r'(https?://youtu\.be/[a-zA-Z0-9_-]+)',                        # URL corta
        r'(https?://(?:www\.)?youtube\.com/embed/[a-zA-Z0-9_-]+)',      # Embed
        r'(?:/process_youtube|/chatbot)\s*(https?://[^\s]+)'            # Tras comandos
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            url = match.group(1) if len(match.groups()) > 0 else match.group(0)
            # Validación básica de URL
            if 'youtube.com' in url or 'youtu.be' in url:
                return url.strip()
    
    return None

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

        # Extraer URL (funciona con o sin comandos)
        video_url = extract_youtube_url(message_text)
        
        if video_url:
            print(f"Extracted URL: {video_url}")  # Depuración
            return jsonify({
                'extracted_url': video_url,
                'chatId': chat_id,
                'success': True
            }), 200

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
