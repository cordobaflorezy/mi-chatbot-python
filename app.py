from flask import Flask, request, jsonify
import os
import google.generativeai as genai

app = Flask(__name__)

# --- Configuración de Gemini desde variable de entorno ---
google_api_key = os.environ.get("GOOGLE_API_KEY")
print(f"Clave de API de Gemini obtenida: {'Sí' if google_api_key else 'No'}")
genai.configure(api_key=google_api_key)
try:
    model_gemini = genai.GenerativeModel('gemini-pro') # O 'gemini-pro-vision' si necesitas multimodalidad
    print("Modelo Gemini inicializado correctamente.")
except Exception as e:
    print(f"Error al inicializar el modelo Gemini: {e}")
    model_gemini = None

@app.route('/process_message', methods=['POST'])
def process_message():
    data = request.get_json()
    message_text = data.get('text', '')
    chat_id = data.get('chatId')

    print(f"Mensaje recibido en /process_message: '{message_text}', Chat ID: {chat_id}")

    if message_text and model_gemini:
        if message_text.lower().startswith("/gemini"):
            prompt_gemini = message_text[len("/gemini"):].strip()
            print(f"Prompt enviado a Gemini: '{prompt_gemini}'")
            print(f"Prompt enviado a Gemini (repr): {repr(prompt_gemini)}")
            try:
                response_gemini = model_gemini.generate_content(prompt_gemini)
                print(f"Respuesta cruda de Gemini: {response_gemini}")
                response_text = response_gemini.text
                print(f"Texto de la respuesta de Gemini: '{response_text}'")
                return jsonify({'response': response_text, 'chatId': chat_id})
            except Exception as e:
                print(f"Error al llamar a Gemini: {e}")
                return jsonify({'error': str(e), 'chatId': chat_id})
        else:
            response = f"¡Hola desde Python! Has dicho: {message_text}"
            print(f"Respuesta básica: '{response}'")
            return jsonify({'response': response, 'chatId': chat_id})
    elif not message_text:
        error_message = "No se proporcionó ningún mensaje."
        print(error_message)
        return jsonify({'error': error_message, 'chatId': chat_id})
    else:
        error_message = "El modelo Gemini no está inicializado."
        print(error_message)
        return jsonify({'error': error_message, 'chatId': chat_id})

@app.route('/ia', methods=['POST'])
def ia_route():
    data = request.get_json()
    message_text = data.get('text', '')
    chat_id = data.get('chatId')

    print(f"Mensaje recibido en /ia: '{message_text}', Chat ID: {chat_id}")

    if message_text and model_gemini:
        try:
            response_gemini = model_gemini.generate_content(message_text)
            print(f"Respuesta cruda de Gemini (/ia): {response_gemini}")
            response_text = response_gemini.text
            print(f"Texto de la respuesta de Gemini (/ia): '{response_text}'")
            return jsonify({'response': response_text, 'chatId': chat_id})
        except Exception as e:
            print(f"Error al llamar a Gemini (/ia): {e}")
            return jsonify({'error': str(e), 'chatId': chat_id})
    elif not message_text:
        error_message = "No se proporcionó ningún mensaje en /ia."
        print(error_message)
        return jsonify({'error': error_message, 'chatId': chat_id})
    else:
        error_message = "El modelo Gemini no está inicializado (/ia)."
        print(error_message)
        return jsonify({'error': error_message, 'chatId': chat_id})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
