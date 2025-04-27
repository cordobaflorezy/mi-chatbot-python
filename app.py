from flask import Flask, request, jsonify
import os
import google.generativeai as genai

app = Flask(__name__)

# --- Configuración de Gemini desde variable de entorno ---
google_api_key = os.environ.get("GOOGLE_API_KEY")
genai.configure(api_key=google_api_key)
model_gemini = genai.GenerativeModel('gemini-pro') # O 'gemini-pro-vision' si necesitas multimodalidad

@app.route('/process_message', methods=['POST'])
def process_message():
    data = request.get_json()
    message_text = data.get('text', '')
    chat_id = data.get('chatId')

    if message_text:
        try:
            response_gemini = model_gemini.generate_content(message_text)
            response_text = response_gemini.text
            return jsonify({'response': response_text, 'chatId': chat_id})
        except Exception as e:
            return jsonify({'error': str(e), 'chatId': chat_id})
    else:
        return jsonify({'error': 'No se proporcionó ningún mensaje', 'chatId': chat_id})

@app.route('/ia', methods=['POST'])
def ia_route():
    data = request.get_json()
    message_text = data.get('text', '')
    chat_id = data.get('chatId')

    if message_text:
        try:
            response_gemini = model_gemini.generate_content(message_text)
            response_text = response_gemini.text
            return jsonify({'response': response_text, 'chatId': chat_id})
        except Exception as e:
            return jsonify({'error': str(e), 'chatId': chat_id})
    else:
        return jsonify({'error': 'No se proporcionó ningún mensaje', 'chatId': chat_id})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)