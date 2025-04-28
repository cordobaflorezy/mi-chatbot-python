from flask import Flask, request, jsonify
import os
import json
import uuid
import google.generativeai as genai
from slugify import slugify
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

app = Flask(__name__)

# Configurar Gemini
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-pro-latest')

@app.route('/generate-metadata', methods=['POST'])
def generate_metadata():
    try:
        if not request.is_json:
            return jsonify({"error": "Solo se acepta JSON", "success": False}), 400

        data = request.get_json()
        raw_content = data.get('text', '').strip()

        if not raw_content:
            return jsonify({"error": "Texto no proporcionado", "success": False}), 400

        prompt = f"""Genera un JSON con metadatos para el siguiente artículo:
1. slug: Un slug único y amigable para SEO (ejemplo: titulo-del-articulo-uuid)
2. title: Título del artículo (informativo y atractivo)
3. author: Un autor plausible para este artículo (si no se puede determinar, usa "AI Generated")
4. date: La fecha actual en formato YYYY-MM-DD
5. excerpt: Un resumen breve y atractivo del artículo (máximo 160 caracteres)
6. thumbnail: Una ruta de archivo de imagen sugerida para la miniatura (ejemplo: /posts/nombre-del-articulo/miniatura.jpg)
7. htmlPath: Una ruta de archivo sugerida para el contenido HTML del artículo (ejemplo: /posts/nombre-del-articulo/index.html)

Formato REQUERIDO:
{{
    "slug": "...",
    "title": "...",
    "author": "...",
    "date": "...",
    "excerpt": "...",
    "thumbnail": "...",
    "htmlPath": "..."
}}

Artículo:
{raw_content}"""

        response = model.generate_content(prompt)
        cleaned_response = response.text.strip().replace('```json', '').replace('```', '')

        try:
            ai_metadata = json.loads(cleaned_response)

            # Asegurar que la fecha sea la actual
            ai_metadata['date'] = datetime.now().strftime('%Y-%m-%d')

            # Generar slug único basado en el título generado por la IA
            ai_metadata['slug'] = slugify(ai_metadata['title']) + '-' + str(uuid.uuid4())[:6]

            return jsonify({
                "success": True,
                "metadata": ai_metadata
            }), 200

        except json.JSONDecodeError:
            return jsonify({"error": "Error al decodificar la respuesta JSON de la IA", "raw_response": cleaned_response, "success": False}), 500

    except Exception as e:
        return jsonify({
            "error": f"Error: {str(e)}",
            "success": False
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
