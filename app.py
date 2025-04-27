from flask import Flask, request, jsonify
import os
from langchain.llms import OpenAI  # Ejemplo: usar OpenAI (puede que no lo uses ahora)
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
import google.generativeai as genai

app = Flask(__name__)

# --- Configuración de OpenAI (si la mantienes) ---
openai_api_key = os.environ.get("OPENAI_API_KEY")
llm_openai = OpenAI(openai_api_key=openai_api_key)
prompt_openai = PromptTemplate(
    input_variables=["query"],
    template="Responde a la siguiente pregunta: {query}",
)
chain_openai = LLMChain(llm=llm_openai, prompt=prompt_openai)

# --- Configuración de Gemini ---
google_api_key = os.environ.get("AIzaSyB0fviuU2cwq7uNDXHMJ3mJLpx6iip8TeU")
genai.configure(api_key=google_api_key)
model_gemini_flash = genai.GenerativeModel('gemini-pro') # Puedes probar 'gemini-pro-vision' si quieres funcionalidades multimodales

@app.route('/process_message', methods=['POST'])
def process_message():
    data = request.get_json()
    message_text = data.get('text', '')
    chat_id = data.get('chatId')

    if message_text.lower().startswith("/pregunta"):
        query = message_text[len("/pregunta"):].strip()
        response = chain_openai.run(query) # Si quieres seguir usando OpenAI para esto
    elif message_text.lower().startswith("/gemini"):
        prompt_gemini = message_text[len("/gemini"):].strip()
        try:
            response_gemini = model_gemini_flash.generate_content(prompt_gemini)
            response_text = response_gemini.text
            return jsonify({'response': response_text, 'chatId': chat_id})
        except Exception as e:
            return jsonify({'error': str(e), 'chatId': chat_id})
    else:
        response = f"¡Hola desde Python! Has dicho: {message_text}"

    return jsonify({'response': response, 'chatId': chat_id})

@app.route('/ia', methods=['POST'])
def ia_route():
    data = request.get_json()
    message_text = data.get('text', '')
    chat_id = data.get('chatId')

    if message_text:
        try:
            response_gemini = model_gemini_flash.generate_content(message_text)
            response_text = response_gemini.text
            return jsonify({'response': response_text, 'chatId': chat_id})
        except Exception as e:
            return jsonify({'error': str(e), 'chatId': chat_id})
    else:
        return jsonify({'error': 'No se proporcionó ningún mensaje', 'chatId': chat_id})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)