from flask import Flask, request, jsonify
import os
import google.generativeai as genai
import subprocess
import tempfile
import whisper
import json
from datetime import datetime

app = Flask(__name__)

# --- Configuración de Gemini desde variable de entorno ---
google_api_key = os.environ.get("GOOGLE_API_KEY")
print(f"Clave de API de Gemini obtenida: {'Sí' if google_api_key else 'No'}")

if google_api_key:
    genai.configure(api_key=google_api_key)
    try:
        model_gemini = genai.GenerativeModel('gemini-1.5-flash') # O el modelo que prefieras
        print("Modelo Gemini inicializado correctamente.")
    except Exception as e:
        model_gemini = None
        print(f"Error al inicializar el modelo Gemini: {e}")
else:
    model_gemini = None
    print("Error: La variable de entorno GOOGLE_API_KEY no está configurada.")

# --- Configuración de GitHub desde variable de entorno ---
github_token = os.environ.get("GITHUB_TOKEN")
github_repo = os.environ.get("GITHUB_REPO")
github_username = os.environ.get("GITHUB_USERNAME")
print(f"Token de GitHub obtenido: {'Sí' if github_token else 'No'}")
print(f"Repositorio de GitHub: {github_repo}")
print(f"Usuario de GitHub: {github_username}")

# --- Funciones ---
def descargar_audio(video_url, output_file):
    try:
        command = [
            'yt-dlp',
            '-x',
            '--audio-format', 'mp3',
            '-o', output_file,
            video_url
        ]
        subprocess.run(command, check=True, capture_output=True, text=True)
        return True, output_file
    except subprocess.CalledProcessError as e:
        return False, f"Error al descargar el audio: {e.stderr}"
    except FileNotFoundError:
        return False, "Error: yt-dlp no se encontró. Asegúrate de que esté instalado."

def transcribir_audio(audio_file):
    try:
        model = whisper.load_model("large")
        result = model.transcribe(audio_file)
        return True, result["text"]
    except Exception as e:
        return False, f"Error al transcribir el audio: {e}"
    except FileNotFoundError:
        return False, "Error: El modelo de Whisper no se encontró. Asegúrate de que esté instalado."

def generar_slug(title):
    return title.lower().replace(' ', '-')

def generar_extracto(text, length=150):
    return text[:length] + "..."

def generar_html(title, author, content):
    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{ font-family: sans-serif; line-height: 1.6; color: #333; margin: 20px; }}
        h1, h2, h3 {{ color: #0056b3; }}
        p {{ margin-bottom: 1em; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>
        <p><strong>Por {author}</strong></p>
        <div>
            {content.replace('\\n', '<br>')}
        </div>
    </div>
</body>
</html>"""
    return html_content

def get_file_from_github(path):
    import requests
    headers = {'Authorization': f'token {github_token}'}
    url = f'https://api.github.com/repos/{github_username}/{github_repo}/contents/{path}'
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    content = response.json().get('content')
    if content:
        import base64
        return base64.b64decode(content).decode('utf-8')
    return '[]'

def upload_file_to_github(path, content, message):
    import requests
    headers = {'Authorization': f'token {github_token}'}
    url = f'https://api.github.com/repos/{github_username}/{github_repo}/contents/{path}'
    data = {
        'message': message,
        'content': content.encode('utf-8').decode('unicode_escape').encode('utf-8').decode('base64').decode('utf-8').encode('base64').decode('utf-8'),
        'sha': None  # GitHub automáticamente detecta si el archivo existe
    }
    response = requests.put(url, headers=headers, json=data)
    response.raise_for_status()
    return response.json().get('commit').get('html_url')

def determinar_categoria(texto):
    if not model_gemini:
        return "general"  # Default si Gemini no está inicializado
    prompt = f"Determina la categoría principal de este texto (gana, salud, home): '{texto}'"
    try:
        response = model_gemini.generate_content(prompt)
        categoria = response.text.strip().lower()
        if categoria in ["gana", "salud", "home"]:
            return categoria
        else:
            return "general"
    except Exception as e:
        print(f"Error al determinar la categoría con Gemini: {e}")
        return "general"

# --- Endpoints ---
@app.route('/process_youtube', methods=['POST'])
def process_youtube_route():
    data = request.get_json()
    video_url = data.get('youtube_url')
    chat_id = data.get('chatId')

    if not video_url:
        return jsonify({'error': 'No se proporcionó la URL de YouTube', 'chatId': chat_id}), 400

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=True) as tmp_audio_file:
        audio_file_path = tmp_audio_file.name
        print(f"Descargando audio de: {video_url} a {audio_file_path}")
        descarga_exitosa, descarga_resultado = descargar_audio(video_url, audio_file_path)

        if descarga_exitosa:
            print(f"Audio descargado exitosamente. Transcribiendo...")
            transcripcion_exitosa, transcripcion_resultado = transcribir_audio(audio_file_path)
            if transcripcion_exitosa:
                print(f"Transcripción completada.")
                # Llamar a Gemini para corrección y creación del post
                prompt_ia = f"Corrige la gramática, ortografía y expande este texto para crear un post de blog coherente:\n\n{transcripcion_resultado}"
                try:
                    response_ia = model_gemini.generate_content(prompt_ia)
                    contenido_post = response_ia.text.strip()

                    # Generar metadatos
                    titulo_base = contenido_post.split('\n')[0] if contenido_post.split('\n') else "Nuevo Artículo"
                    titulo = titulo_base.replace('#', '').strip()
                    slug = generar_slug(titulo)
                    autor = "IA" # Puedes hacerlo dinámico si lo extraes de alguna forma
                    fecha = datetime.now().strftime('%Y-%m-%d')
                    extracto = generar_extracto(contenido_post)
                    thumbnail = f"/posts/{slug}/thumbnail.jpg" # Placeholder
                    html_path = f"/posts/{slug}/index.html"

                    # Determinar categoría
                    categoria = determinar_categoria(titulo + " " + extracto)
                    json_path = f"public/{categoria}.json"

                    # Generar HTML
                    html_content = generar_html(titulo, autor, contenido_post)
                    html_file_path_github = f"public/posts/{slug}/index.html"
                    upload_file_to_github(html_file_path_github, html_content, f"Publicar artículo: {titulo}")
                    print(f"Archivo HTML subido a GitHub: {html_file_path_github}")

                    # Actualizar JSON
                    existing_json_str = get_file_from_github(json_path)
                    try:
                        existing_data = json.loads(existing_json_str)
                        if not isinstance(existing_data, list):
                            existing_data = []
                    except json.JSONDecodeError:
                        existing_data = []

                    new_post_data = {
                        "slug": slug,
                        "title": titulo,
                        "author": autor,
                        "date": fecha,
                        "excerpt": extracto,
                        "thumbnail": thumbnail,
                        "htmlPath": html_path
                    }
                    existing_data.append(new_post_data)
                    upload_file_to_github(json_path, json.dumps(existing_data, indent=2), f"Actualizar {categoria}.json con: {titulo}")
                    print(f"Archivo JSON actualizado en GitHub: {json_path}")

                    return jsonify({'message': f'Artículo "{titulo}" publicado exitosamente', 'chatId': chat_id}), 200

                except Exception as e_ia:
                    return jsonify({'error': f'Error al procesar el texto con la IA: {e_ia}', 'chatId': chat_id}), 500

            else:
                print(f"Error en la transcripción: {transcripcion_resultado}")
                return jsonify({'error': f'Error en la transcripción: {transcripcion_resultado}', 'chatId': chat_id}), 500
        else:
            print(f"Error en la descarga del audio: {descarga_resultado}")
            return jsonify({'error': f'Error en la descarga del audio: {descarga_resultado}', 'chatId': chat_id}), 500

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
            error_message = f"Error al llamar a Gemini (/ia): {e}"
            print(error_message)
            return jsonify({'error': error_message, 'chatId': chat_id})
    elif not message_text:
        error_message = "No se proporcionó ningún mensaje en /ia."
        print(error_message)
        return jsonify({'error': error_message, 'chatId': chat_id})
    else:
        error_message = "El modelo Gemini no está inicializado (/ia). Verifica la configuración de la clave de API."
        print(error_message)
        return jsonify({'error': error_message, 'chatId': chat_id})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
