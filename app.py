from flask import Flask, request, jsonify
import os
import json
import uuid
import google.generativeai as genai
from slugify import slugify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Configurar Gemini
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-pro-latest')

@app.route('/auto-article', methods=['POST'])
def create_auto_article():
    try:
        # Validar entrada
        if not request.is_json:
            return jsonify({"error": "Solo se acepta JSON", "success": False}), 400

        data = request.get_json()
        raw_content = data.get('text', '').strip()
        
        if len(raw_content) < 100:
            return jsonify({"error": "Contenido muy corto (mínimo 100 caracteres)", "success": False}), 400

        # Procesar con IA
        prompt = f"""Genera un JSON con:
1. title: Título del artículo
2. category: (salud|belleza|tecnologia|deportes)
3. excerpt: Resumen breve
4. tags: 3-5 palabras clave

Formato REQUERIDO:
{{
    "title": "...",
    "category": "...",
    "excerpt": "...",
    "tags": ["...", "..."]
}}

Artículo:
{raw_content}"""

        response = model.generate_content(prompt)
        cleaned_response = response.text.strip().replace('```json', '').replace('```', '')
        ai_data = json.loads(cleaned_response)

        # Generar slug único
        slug = slugify(ai_data['title']) + '-' + str(uuid.uuid4())[:6]

        return jsonify({
            "success": True,
            "slug": slug,
            "article_data": ai_data
        }), 201

    except Exception as e:
        return jsonify({
            "error": f"Error: {str(e)}",
            "raw_response": getattr(response, 'text', 'N/A'),
            "success": False
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
