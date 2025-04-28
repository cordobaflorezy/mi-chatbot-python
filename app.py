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

# Configuración de Gemini
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-pro-latest')

# Configuración de directorios
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
POSTS_DIR = os.path.join(BASE_DIR, 'public', 'posts')
os.makedirs(POSTS_DIR, exist_ok=True)

def process_with_ai(raw_content):
    try:
        prompt = f"""Genera un JSON válido con:
1. title: Título atractivo (60 caracteres max)
2. category: (salud|belleza|tecnologia|deportes)
3. excerpt: Resumen breve (140 caracteres max)
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
        cleaned = response.text.strip().replace('```json', '').replace('```', '')
        return json.loads(cleaned)
    
    except json.JSONDecodeError:
        raise ValueError(f"Respuesta inválida de Gemini: {response.text}")
    except Exception as e:
        raise RuntimeError(f"Error en IA: {str(e)}")

def generate_html(content):
    safe_content = html.escape(content['raw_content']).replace('\n', '<br>')
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="{html.escape(content['excerpt'])}">
    <title>{html.escape(content['title'])}</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; padding: 20px; }}
        .content {{ white-space: pre-line; }}
        .meta {{ color: #666; margin-top: 20px; }}
    </style>
</head>
<body>
    <article>
        <h1>{html.escape(content['title'])}</h1>
        <div class="content">{safe_content}</div>
        <div class="meta">
            <p>Categoría: {content['category']}</p>
            <p>Tags: {', '.join(content['tags'])}</p>
        </div>
    </article>
</body>
</html>"""

@app.route('/auto-article', methods=['POST'])
def create_auto_article():
    response_template = {
        "success": False,
        "chatId": "unknown",
        "error": None,
        "article": None
    }

    try:
        # Validar entrada
        if not request.is_json:
            response_template["error"] = "Solo se acepta JSON"
            return jsonify(response_template), 400

        data = request.get_json()
        response_template["chatId"] = data.get('chatId', 'unknown')

        if 'text' not in data or len(data['text'].strip()) < 100:
            response_template["error"] = "Texto inválido (mínimo 100 caracteres)"
            return jsonify(response_template), 400

        # Procesar con IA
        raw_content = data['text'].strip()
        ai_data = process_with_ai(raw_content)

        # Generar estructura de archivos
        slug = f"{slugify(ai_data['title'])}-{uuid.uuid4().hex[:6]}"
        post_dir = os.path.join(POSTS_DIR, slug)
        os.makedirs(post_dir, exist_ok=True)

        # Crear HTML
        article_data = {
            **ai_data,
            "raw_content": raw_content,
            "slug": slug,
            "date": "2025-01-01"
        }
        
        with open(os.path.join(post_dir, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(generate_html(article_data))

        # Actualizar JSON
        json_file = os.path.join(POSTS_DIR, f"{ai_data['category']}.json")
        articles = []
        
        if os.path.exists(json_file):
            with open(json_file, 'r', encoding='utf-8') as f:
                articles = json.load(f)
        
        articles.append({
            "slug": slug,
            "title": ai_data['title'],
            "excerpt": ai_data['excerpt'],
            "category": ai_data['category'],
            "tags": ai_data['tags'],
            "htmlPath": f"/posts/{slug}/index.html"
        })
        
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(articles, f, indent=2, ensure_ascii=False)

        return jsonify({
            "success": True,
            "chatId": response_template["chatId"],
            "article": {
                "slug": slug,
                "url": f"/posts/{slug}/index.html",
                "preview": ai_data['excerpt']
            }
        }), 201

    except Exception as e:
        response_template["error"] = str(e)
        return jsonify(response_template), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "ok",
        "posts": sum(len(files) for _, _, files in os.walk(POSTS_DIR)),
        "categories": [f.split('.')[0] for f in os.listdir(POSTS_DIR) if f.endswith('.json')]
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
