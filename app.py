from flask import Flask, request, jsonify
import os
import re
from urllib.parse import urlparse

app = Flask(__name__)

def extract_youtube_url_simple(text):
    """
    Intenta extraer una URL de YouTube de un texto.
    """
    url_pattern = re.compile(r'http[s]?://(?:www\.)?youtube\.com/(?:watch\?v=|shorts/)([a-zA-Z0-9_-]+)')
    match = url_pattern.search(text)
    if match:
        return match.group(0)

    generic_url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
    generic_match = generic_url_pattern.search(text)
    if generic_match:
        parsed_url = urlparse(generic_match.group(0))
        if 'youtube.com' in parsed_url.netloc:
            return generic_match.group(0)
    return None

@app.route('/chatbot', methods=['POST'])
def chatbot_route():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided', 'success': False}), 400

        message_text = data.get('text', '').strip()
        chat_id = data.get('chatId')

        print(f"Received message text: '{message_text}'")  # Debugging line

        if not message_text:
            return jsonify({'error': 'Empty message', 'chatId': chat_id, 'success': False}), 400

        if message_text.lower().startswith('/process_youtube'):
            # Extrae la URL del resto del texto
            url_part = message_text[len('/process_youtube'):].strip()
            video_url = extract_youtube_url_simple(url_part)
            if not video_url:
                return jsonify({
                    'error': 'Formato de URL inválido.',
                    'chatId': chat_id,
                    'success': False
                }), 400

            return jsonify({
                'extracted_url': video_url,
                'chatId': chat_id,
                'success': True
            }), 200

        return jsonify({'message': 'Command not recognized', 'chatId': chat_id, 'success': False}), 200

    except Exception as e:
        return jsonify({'error': f'Internal error: {str(e)}', 'success': False}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
