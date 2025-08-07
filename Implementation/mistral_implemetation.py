import os
# Résoudre le problème des tokenizers Hugging Face
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from mistralai import Mistral
from typing import List, Dict, Any, Optional
from config import Config
import traceback
import time

class LLMIntegration:
    def __init__(self):
        try:
            # Vérifier que la clé API Mistral est présente
            if not hasattr(Config, 'MISTRAL_API_KEY') or not Config.MISTRAL_API_KEY:
                raise ValueError("MISTRAL_API_KEY manquante dans la configuration")
            
            if not hasattr(Config, 'LLM_MODEL') or not Config.LLM_MODEL:
                # Utiliser un modèle Mistral par défaut si non spécifié
                self.model = "mistral-large-latest"
                print("Aucun modèle spécifié, utilisation de mistral-large-latest")
            else:
                self.model = Config.LLM_MODEL
            
            self.api_key = Config.MISTRAL_API_KEY
            
            # Initialiser le client Mistral
            print(f"Initialisation du client Mistral avec la clé: {self.api_key[:10]}...")
            self.client = Mistral(api_key=self.api_key)
            
            print(f"LLM initialisé avec Mistral API, modèle: {self.model}")
            
        except Exception as e:
            print(f"Erreur lors de l'initialisation du LLM: {e}")
            traceback.print_exc()
            raise
    
    def simple_test(self) -> Dict[str, Any]:
        """Test simple pour vérifier que Mistral fonctionne"""
        try:
            print("\n=== TEST SIMPLE MISTRAL ===")
            start_time = time.time()
            
            # Test très simple
            messages = [
                {"role": "user", "content": "Bonjour, réponds juste 'OK'"}
            ]
            
            print(f"Envoi d'un message test simple au modèle: {self.model}")
            print(f"Clé API utilisée: {self.api_key[:10]}...")
            
            # Paramètres très permissifs pour le test
            response = self.client.chat.complete(
                model=self.model,
                messages=messages,
                max_tokens=10,      # Très court
                temperature=0.1     # Très déterministe
            )
            
            end_time = time.time()
            response_time = end_time - start_time
            
            print(f"Réponse reçue en {response_time:.2f} secondes")
            print(f"Contenu de la réponse: {response.choices[0].message.content}")
            
            return {
                'success': True,
                'response': response.choices[0].message.content,
                'response_time': response_time,
                'model': self.model
            }
            
        except Exception as e:
            print(f"ERREUR lors du test simple: {e}")
            print(f"Type d'erreur: {type(e).__name__}")
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__
            }
    
    def test_with_different_models(self) -> Dict[str, Any]:
        """Teste différents modèles Mistral pour voir lequel fonctionne"""
        models_to_test = [
            "mistral-large-latest",
            "mistral-medium-latest", 
            "mistral-small-latest",
            "open-mistral-7b",
            "open-mixtral-8x7b"
        ]
        
        results = {}
        
        for model in models_to_test:
            print(f"\n--- Test du modèle: {model} ---")
            try:
                start_time = time.time()
                
                messages = [{"role": "user", "content": "Test"}]
                
                response = self.client.chat.complete(
                    model=model,
                    messages=messages,
                    max_tokens=5
                )
                
                end_time = time.time()
                response_time = end_time - start_time
                
                results[model] = {
                    'success': True,
                    'response_time': response_time,
                    'response': response.choices[0].message.content
                }
                
                print(f"✅ {model}: OK ({response_time:.2f}s)")
                
            except Exception as e:
                results[model] = {
                    'success': False,
                    'error': str(e),
                    'error_type': type(e).__name__
                }
                print(f"❌ {model}: ERREUR - {e}")
        
        return results
    
    def create_prompt(self, user_query: str, retrieved_chunks: List[Dict[str, Any]], intent: Optional[str] = None) -> str:
        """Créer le prompt optimisé pour OPTIM Finance"""
        
        try:
            # Construire le contexte à partir des chunks récupérés
            context_parts = []
            for i, chunk in enumerate(retrieved_chunks):
                # Vérifier la structure du chunk
                if not isinstance(chunk, dict):
                    print(f"WARNING: Chunk {i} n'est pas un dictionnaire: {type(chunk)}")
                    continue
                
                # Récupérer title et content avec des valeurs par défaut
                title = chunk.get('title', chunk.get('filename', f'Document {i+1}'))
                content = chunk.get('content', chunk.get('text', ''))
                
                # Vérifier que le contenu n'est pas vide
                if content and str(content).strip():
                    context_parts.append(f"**{title}**\n{content}")
                else:
                    print(f"WARNING: Chunk {i} a un contenu vide")
            
            context = "\n\n".join(context_parts)
            
            # Vérifier que nous avons du contexte
            if not context.strip():
                print(f"WARNING: Aucun contexte valide trouvé parmi {len(retrieved_chunks)} chunks")
                context = "Informations limitées disponibles dans notre base de connaissances."
            
            # Personnaliser selon l'intention
            intent_instructions = {
                'pricing': "Mets l'accent sur les tarifs exacts et les coûts détaillés.",
                'comparison': "Compare clairement les différentes solutions en listant les avantages/inconvénients.",
                'contact': f"N'hésite pas à proposer un contact direct : {Config.CONTACT_EMAIL} ou {Config.CONTACT_PHONE}",
                'definition': "Explique clairement les concepts avec des définitions précises.",
                'process': "Détaille les étapes et la procédure étape par étape.",
                'general': "Fournis une réponse complète et professionnelle."
            }
            
            specific_instruction = intent_instructions.get(intent, "Fournis une réponse claire et professionnelle.") if intent else "Fournis une réponse claire et professionnelle."
            
            prompt = f"""Tu es l'assistant virtuel expert d'OPTIM Finance, spécialisé dans les solutions financières pour freelances IT.

CONTEXTE PERTINENT :
{context}

QUESTION DU CLIENT : {user_query}

INSTRUCTIONS :
- Réponds de manière professionnelle et chaleureuse
- Utilise UNIQUEMENT les informations du contexte fourni ci-dessus
- Sois précis sur les chiffres (tarifs, pourcentages, délais)
- {specific_instruction}
- Si la question nécessite un contact direct, mention : {Config.CONTACT_EMAIL} ou {Config.CONTACT_PHONE}
- Sois concis mais complet (maximum 300 mots)
- Utilise un ton commercial professionnel mais pas agressif
- Si l'information n'est pas dans le contexte, dis-le clairement et propose de contacter l'équipe

RÉPONSE :"""
            
            print(f"Prompt créé - Longueur: {len(prompt)} caractères")
            return prompt
            
        except Exception as e:
            print(f"Erreur lors de la création du prompt: {e}")
            traceback.print_exc()
            raise
    
    def generate_response(self, user_query: str, retrieved_chunks: List[Dict[str, Any]], intent: Optional[str] = None) -> Dict[str, Any]:
        """Générer une réponse avec le LLM Mistral"""
        try:
            print(f"\n=== GÉNÉRATION DE RÉPONSE ===")
            print(f"Query: '{user_query}'")
            print(f"Chunks: {len(retrieved_chunks)}")
            print(f"Intent: {intent}")
            print(f"Modèle: {self.model}")
            
            start_time = time.time()
            
            # Debug: afficher la structure des premiers chunks
            for i, chunk in enumerate(retrieved_chunks[:2]):
                print(f"Chunk {i+1} - Clés: {list(chunk.keys())}")
                content_preview = str(chunk.get('content', ''))[:100]
                print(f"Contenu (preview): {content_preview}...")
            
            # Créer le prompt
            prompt = self.create_prompt(user_query, retrieved_chunks, intent)
            
            # Préparer les messages pour Mistral
            messages = [
                {
                    "role": "system",
                    "content": "Tu es l'assistant virtuel expert d'OPTIM Finance. Tu es professionnel, précis et utile."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            
            print("Envoi de la requête à Mistral...")
            
            # Paramètres généreux pour le test
            response = self.client.chat.complete(
                model=self.model,
                messages=messages,
                max_tokens=500,     # Plus généreux
                temperature=0.3,    # Modéré
                top_p=0.9          
            )
            
            end_time = time.time()
            response_time = end_time - start_time
            
            print(f"✅ Réponse reçue en {response_time:.2f} secondes")
            
            # Extraire le contenu de la réponse
            response_content = response.choices[0].message.content
            if response_content is None or not response_content.strip():
                response_content = "Désolé, je n'ai pas pu générer une réponse appropriée. Contactez notre équipe pour plus d'informations."
            
            # Créer la liste des sources
            sources = []
            for i, chunk in enumerate(retrieved_chunks):
                chunk_id = chunk.get('id', f'source_{i+1}')
                sources.append(chunk_id)
            
            return {
                'response': response_content.strip(),
                'sources': sources,
                'intent': intent,
                'provider': 'mistral',
                'model': self.model,
                'response_time': response_time,
                'success': True
            }
            
        except Exception as e:
            error_msg = f"Erreur Mistral API: {str(e)}"
            print(f"❌ ERREUR: {error_msg}")
            print(f"Type: {type(e).__name__}")
            traceback.print_exc()
            
            return {
                'response': f"Désolé, une erreur est survenue. Veuillez contacter notre équipe à {Config.CONTACT_EMAIL}",
                'sources': [],
                'intent': intent,
                'provider': 'mistral',
                'model': self.model,
                'error': error_msg,
                'error_type': type(e).__name__,
                'success': False
            }
    
    def test_connection(self) -> bool:
        """Tester la connexion à l'API Mistral"""
        try:
            print("\n=== TEST DE CONNEXION ===")
            result = self.simple_test()
            return result['success']
        except Exception as e:
            print(f"❌ Erreur de connexion: {e}")
            return False

# Script de test standalone
if __name__ == "__main__":
    print("=== TESTS MISTRAL API ===")
    
    try:
        # Initialiser
        llm = LLMIntegration()
        
        # Test simple
        print("\n1. Test de connexion simple...")
        simple_result = llm.simple_test()
        print(f"Résultat: {simple_result}")
        
        if simple_result['success']:
            print("✅ Test simple réussi!")
            
            # Test avec différents modèles
            print("\n2. Test de différents modèles...")
            models_result = llm.test_with_different_models()
            
            print("\n=== RÉSUMÉ DES TESTS ===")
            for model, result in models_result.items():
                if result['success']:
                    print(f"✅ {model}: {result['response_time']:.2f}s")
                else:
                    print(f"❌ {model}: {result['error']}")
        else:
            print("❌ Test simple échoué, vérifiez votre configuration")
            print(f"Erreur: {simple_result.get('error', 'Inconnue')}")
            
    except Exception as e:
        print(f"❌ Erreur lors des tests: {e}")
        traceback.print_exc()