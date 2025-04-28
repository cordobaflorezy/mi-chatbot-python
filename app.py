from flask import Flask, request, jsonify
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Configurar Gemini
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-pro-latest')

@app.route('/generate-title', methods=['POST'])
def generate_title():
    try:
        if not request.is_json:
            return jsonify({"error": "Solo se acepta JSON", "success": False}), 400

        data = request.get_json()
        raw_content = data.get('text', '').strip()

        if not raw_content:
            return jsonify({"error": "Texto no proporcionado", "success": False}), 400

        prompt = f"""Genera un título conciso para el siguiente artículo:
{raw_content}"""

        response = model.generate_content(prompt)
        title = response.text.strip()

        return jsonify({
            "success": True,
            "title": title
        }), 200

    except Exception as e:
        return jsonify({
            "error": f"Error: {str(e)}",
            "success": False
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
