import unittest
from unittest.mock import patch, MagicMock

from src.rag_core import RAGCore


class TestRAGCore(unittest.TestCase):
    
    @patch("src.rag_core.SentenceTransformer")
    @patch("src.rag_core.Elasticsearch")
    @patch("src.rag_core.load_dotenv")
    @patch("src.rag_core.os.getenv")
    def setUp(self, mock_getenv, mock_load_dotenv, mock_es_class, mock_st_class):
        # Mocks para inicialización
        mock_getenv.return_value = "dummy_password"
        
        # Mock de Elasticsearch
        self.mock_es_instance = MagicMock()
        self.mock_es_instance.ping.return_value = True
        mock_es_class.return_value = self.mock_es_instance
        
        # Mock de SentenceTransformer
        self.mock_st_instance = MagicMock()
        mock_st_class.return_value = self.mock_st_instance
        
        # Instanciar el core con los mocks
        self.rag = RAGCore()

    def test_buscar_ayudas(self):
        # Configurar el mock del encoder
        mock_encode = MagicMock()
        mock_encode.tolist.return_value = [0.1] * 768
        self.mock_st_instance.encode.return_value = mock_encode

        # Configurar el mock de Elasticsearch search
        mock_response = {
            "hits": {
                "hits": [
                    {
                        "_score": 0.95,
                        "_source": {
                            "title": "Ayuda Test",
                            "description": "Desc",
                            "beneficiaries": "Todos",
                            "url": "http://test.com"
                        }
                    }
                ]
            }
        }
        self.mock_es_instance.search.return_value = mock_response

        # Ejecutar
        resultados = self.rag.buscar_ayudas("prueba")

        # Verificaciones
        self.mock_st_instance.encode.assert_called_once_with("query: prueba")
        self.mock_es_instance.search.assert_called_once()
        self.assertEqual(len(resultados), 1)
        self.assertEqual(resultados[0]["title"], "Ayuda Test")
        self.assertEqual(resultados[0]["_score"], 0.95)

    @patch("src.rag_core.requests.post")
    def test_generar_respuesta_exito(self, mock_post):
        # Configurar el mock de requests
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "Respuesta simulada de Ollama"}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        contexto = [
            {"title": "Doc 1", "description": "Desc 1", "beneficiaries": "Ben 1", "url": "http://doc1.com"}
        ]

        respuesta = self.rag.generar_respuesta("pregunta?", contexto)

        self.assertEqual(respuesta, "Respuesta simulada de Ollama")
        mock_post.assert_called_once()
        
        # Verificar que el payload contiene la pregunta y el prompt estricto
        args, kwargs = mock_post.call_args
        payload = kwargs.get("json")
        self.assertIsNotNone(payload)
        self.assertEqual(payload["model"], "llama3")
        self.assertIn("pregunta?", payload["prompt"])
        self.assertIn("ÚNICAMENTE", payload["system"])

    @patch("src.rag_core.requests.post")
    def test_generar_respuesta_error(self, mock_post):
        # Simular error de red
        import requests
        mock_post.side_effect = requests.exceptions.ConnectionError("Error de conexión")

        respuesta = self.rag.generar_respuesta("pregunta?", [])

        self.assertIn("Error de conexión", respuesta)


if __name__ == "__main__":
    unittest.main()
