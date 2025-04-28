from flask import Flask, request
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

@app.route('/process-article', methods=['POST'])
def process_article():
    try:
        article_content = ""
        if 'article_text' in request.form:
            article_content = request.form['article_text']
        elif 'article_file' in request.files:
            article_file = request.files['article_file']
            if article_file.filename != '':
                article_content = article_file.read().decode('utf-8')

        if not article_content:
            return "No se proporcionó texto del artículo ni archivo.", 400

        # Generar resumen
        summary_prompt = f"""Genera un resumen conciso de un párrafo (máximo 150 palabras) para el siguiente artículo:
{article_content}"""
        summary_response = model.generate_content(summary_prompt)
        summary = summary_response.text.strip()

        # Generar metadatos JSON
        metadata_prompt = f"""Genera un JSON con metadatos para el siguiente artículo:
1. slug: Un slug único y amigable para SEO
2. title: Título del artículo
3. author: Un autor plausible
4. date: La fecha actual en formato YYYY-MM-DD
5. excerpt: Un resumen breve (máximo 160 caracteres)
6. thumbnail: Ruta de archivo sugerida
7. htmlPath: Ruta de archivo sugerida

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
{article_content}"""

        metadata_response = model.generate_content(metadata_prompt)
        cleaned_metadata = metadata_response.text.strip().replace('```json', '').replace('```', '')

        try:
            ai_metadata = json.loads(cleaned_metadata)
            ai_metadata['date'] = datetime.now().strftime('%Y-%m-%d')
            ai_metadata['slug'] = slugify(ai_metadata['title']) + '-' + str(uuid.uuid4())[:6]
            metadata_json_str = json.dumps(ai_metadata, indent=4)
        except json.JSONDecodeError:
            return f"Error al decodificar JSON de metadatos: {cleaned_metadata}", 500

        # Crear el contenido del archivo de respuesta (resumen y metadatos JSON)
        response_content = f"Resumen del artículo:\n{summary}\n\nMetadatos JSON:\n{metadata_json_str}"

        return response_content, 200, {'Content-Type': 'text/plain; charset=utf-8'}

    except Exception as e:
        return f"Error: {str(e)}", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
