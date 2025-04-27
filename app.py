from flask import Flask, request, jsonify
import os

app = Flask(__name__)

@app.route('/process_message', methods=['POST'])
def process_message():
    data = request.get_json()
    message_text = data.get('text', '')
    chat_id = data.get('chatId')

    response = f"¡Hola desde Python! Has dicho: {message_text}"

    return jsonify({'response': response, 'chatId': chat_id})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)