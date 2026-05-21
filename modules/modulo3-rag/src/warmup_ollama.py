import requests
import time
import sys

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3"

def wakeup_ollama():
    print(f"⏳ Despertando al modelo '{MODEL_NAME}' en Ollama...")
    print("Esto puede tardar unos segundos o minutos la primera vez mientras carga los pesos en memoria...")
    
    start_time = time.time()
    
    payload = {
        "model": MODEL_NAME,
        "prompt": "Responde solo con la palabra 'OK'",
        "stream": False
    }
    
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=300)
        response.raise_for_status()
        elapsed = time.time() - start_time
        
        texto_respuesta = response.json().get("response", "").strip()
        
        print(f"✅ ¡Ollama está listo y caliente! Modelo cargado en {elapsed:.2f} segundos.")
        print(f"🤖 Respuesta de prueba: {texto_respuesta}")
        
    except requests.exceptions.ConnectionError:
        print("❌ Error: Ollama no está ejecutándose. Asegúrate de haber iniciado el servicio (sudo systemctl start ollama).")
        sys.exit(1)
    except requests.exceptions.Timeout:
        print("❌ Error: Ollama ha tardado demasiado en responder (más de 5 minutos).")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error inesperado al conectar con Ollama: {e}")
        sys.exit(1)

if __name__ == "__main__":
    wakeup_ollama()
