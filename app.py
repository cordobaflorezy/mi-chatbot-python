from flask import Flask, request, jsonify
import os
import html
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

# Configuración de directorios
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
POSTS_DIR = os.path.join(BASE_DIR, 'public', 'posts')
os.makedirs(POSTS_DIR, exist_ok=True)

def process_with_ai(raw_content):
    prompt = f"""Analiza este artículo y genera:
1. Título atractivo (máx 60 caracteres)
2. Categoría principal (salud, belleza, tecnologia, deportes)
3. Excerpt breve (1 línea, máx 140 caracteres)
4. Tags clave (3-5 palabras clave)

Formato de respuesta JSON:
{{
    "title": "",
    "category": "",
    "excerpt": "",
    "tags": []
}}

Artículo:
{raw_content}"""

    response = model.generate_content(prompt)
    return json.loads(response.text)

def generate_html(content):
    # Procesar contenido primero
    processed_content = html.escape(content['raw_content']).replace('\n', '<br>')
    
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="{html.escape(content['excerpt'])}">
    <title>{html.escape(content['title'])}</title>
</head>
<body>
    <article>
        <h1>{html.escape(content['title'])}</h1>
        <div class="content">
            {processed_content}
        </div>
        <div class="meta">
            <span>Categoría: {content['category']}</span>
            <span>Tags: {', '.join(content['tags'])}</span>
        </div>
    </article>
</body>
</html>"""

@app.route('/auto-article', methods=['POST'])
def create_auto_article():
    try:
        # Paso 1: Recibir contenido crudo
        raw_content = request.json.get('content', '')
        if not raw_content:
            return jsonify({"error": "No content provided"}), 400

        # Paso 2: Procesar con Gemini
        ai_data = process_with_ai(raw_content)
        
        # Paso 3: Generar estructura de archivos
        slug = slugify(ai_data['title']) + '-' + str(uuid.uuid4())[:6]
        post_dir = os.path.join(POSTS_DIR, slug)
        os.makedirs(post_dir, exist_ok=True)

        # Paso 4: Crear HTML
        article_data = {
            **ai_data,
            "raw_content": raw_content,
            "slug": slug,
            "date": "2025-01-01"  # Puedes añadir fecha real aquí
        }
        
        with open(os.path.join(post_dir, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(generate_html(article_data))

        # Paso 5: Actualizar JSON
        json_path = os.path.join(POSTS_DIR, f"{ai_data['category']}.json")
        existing_data = []
        
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
        
        existing_data.append({
            "slug": slug,
            "title": ai_data['title'],
            "excerpt": ai_data['excerpt'],
            "category": ai_data['category'],
            "tags": ai_data['tags'],
            "htmlPath": f"/posts/{slug}/index.html"
        })
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, indent=2, ensure_ascii=False)

        return jsonify({
            "success": True,
            "ai_generated": ai_data,
            "files": {
                "html": f"/posts/{slug}/index.html",
                "json": f"{ai_data['category']}.json"
            }
        }), 201

    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok', 'version': '1.0'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
