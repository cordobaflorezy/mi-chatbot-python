from flask import Flask, request, jsonify
import os
import re
from urllib.parse import urlparse

app = Flask(__name__)

def extract_youtube_url_simple(text):
    """
    Improved YouTube URL extraction that handles more URL formats
    """
    # Patterns for various YouTube URL formats
    patterns = [
        r'(https?://(?:www\.)?youtube\.com/watch\?v=[a-zA-Z0-9_-]+)',
        r'(https?://(?:www\.)?youtube\.com/shorts/[a-zA-Z0-9_-]+)',
        r'(https?://youtu\.be/[a-zA-Z0-9_-]+)',
        r'(https?://(?:www\.)?youtube\.com/embed/[a-zA-Z0-9_-]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)
    
    return None

@app.route('/chatbot', methods=['POST'])
def chatbot_route():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided', 'success': False}), 400

        message_text = data.get('text', '').strip()
        chat_id = data.get('chatId')

        print(f"Received message text: '{message_text}'")  # Debugging

        if not message_text:
            return jsonify({'error': 'Empty message', 'chatId': chat_id, 'success': False}), 400

        # Check if the message contains a YouTube URL regardless of command
        video_url = extract_youtube_url_simple(message_text)
        if video_url:
            return jsonify({
                'extracted_url': video_url,
                'chatId': chat_id,
                'success': True
            }), 200

        return jsonify({
            'message': 'No YouTube URL found in message',
            'chatId': chat_id,
            'success': False
        }), 200

    except Exception as e:
        return jsonify({'error': f'Internal error: {str(e)}', 'success': False}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
