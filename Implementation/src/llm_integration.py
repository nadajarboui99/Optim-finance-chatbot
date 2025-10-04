import os
# Résoudre le problème des tokenizers Hugging Face
os.environ["TOKENIZERS_PARALLELISM"] = "false"
import sys
# Updated import for newer mistralai package
from mistralai.client import MistralClient
from typing import List, Dict, Any, Optional
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config
import traceback

class LLMIntegration:
    def __init__(self):
        try:
            # Vérifier que la clé API Mistral est présente
            if not hasattr(Config, 'MISTRAL_API_KEY') or not Config.MISTRAL_API_KEY:
                raise ValueError("MISTRAL_API_KEY manquante dans la configuration")
            
            if not hasattr(Config, 'LLM_MODEL') or not Config.LLM_MODEL:
                # Utiliser un modèle Mistral par défaut si non spécifié
                self.model = "open-mistral-7b"
                print("Aucun modèle spécifié, utilisation de open-mistral-7b")
            else:
                self.model = Config.LLM_MODEL
            
            self.api_key = Config.MISTRAL_API_KEY
            
            # Initialiser le client Mistral avec la nouvelle API
            self.client = MistralClient(api_key=self.api_key)
            
            print(f"LLM initialisé avec Mistral API, modèle: {self.model}")
            
        except Exception as e:
            print(f"Erreur lors de l'initialisation du LLM: {e}")
            raise
    
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
- Réponds UNIQUEMENT à la question posée
- Donne EXACTEMENT l'information nécessaire (ni plus, ni moins)

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
            print(f"Génération de réponse pour: '{user_query}'")
            print(f"Nombre de chunks: {len(retrieved_chunks)}")
            print(f"Intention détectée: {intent}")
            print(f"Modèle Mistral: {self.model}")
            
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
            
            print("Appel à l'API Mistral...")
            
            # Appel à l'API Mistral avec paramètres optimisés pour la vitesse
            response = self.client.chat(
                model=self.model,
                messages=messages,
                max_tokens=400,  # Réduit pour une réponse plus rapide
                temperature=0.3,  # Plus bas pour une génération plus rapide et déterministe
                top_p=0.95,       # Nucleus sampling pour la vitesse
            )
            
            print("Réponse reçue de Mistral API")
            
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
                'success': True
            }
            
        except Exception as e:
            # Gestion des erreurs spécifiques à Mistral
            if "authentication" in str(e).lower() or "unauthorized" in str(e).lower():
                error_msg = "Erreur d'authentification Mistral - Vérifiez votre clé API"
                print(f"{error_msg}: {e}")
                return {
                    'response': f"Désolé, une erreur technique est survenue. Veuillez contacter notre équipe à {Config.CONTACT_EMAIL}",
                    'sources': [],
                    'intent': intent,
                    'provider': 'mistral',
                    'error': error_msg,
                    'success': False
                }
            
            elif "rate" in str(e).lower() or "quota" in str(e).lower():
                error_msg = "Limite de taux Mistral atteinte"
                print(f"{error_msg}: {e}")
                return {
                    'response': f"Désolé, notre service est temporairement surchargé. Veuillez réessayer dans quelques instants ou contacter {Config.CONTACT_EMAIL}",
                    'sources': [],
                    'intent': intent,
                    'provider': 'mistral',
                    'error': error_msg,
                    'success': False
                }
            
            elif "timeout" in str(e).lower():
                error_msg = "Timeout de l'API Mistral"
                print(f"{error_msg}: {e}")
                return {
                    'response': f"Désolé, la réponse prend trop de temps. Veuillez réessayer ou contacter {Config.CONTACT_EMAIL}",
                    'sources': [],
                    'intent': intent,
                    'provider': 'mistral',
                    'error': error_msg,
                    'success': False
                }
            
            else:
                error_msg = f"Erreur Mistral API: {str(e)}"
                print(f"ERREUR LLM DÉTAILLÉE: {error_msg}")
                print(f"Type d'erreur: {type(e).__name__}")
                print(f"Stack trace complet:")
                traceback.print_exc()
                
                return {
                    'response': f"Désolé, une erreur est survenue. Veuillez contacter notre équipe à {Config.CONTACT_EMAIL}",
                    'sources': [],
                    'intent': intent,
                    'provider': 'mistral',
                    'error': error_msg,
                    'success': False
                }
    
    def test_connection(self) -> bool:
        """Tester la connexion à l'API Mistral"""
        try:
            print("Test de connexion à Mistral API...")
            test_messages = [
                {"role": "user", "content": "Test de connexion"}
            ]
            
            response = self.client.chat(
                model=self.model,
                messages=test_messages,
                max_tokens=5
            )
            print("Connexion Mistral API OK")
            return True
        except Exception as e:
            print(f"Erreur de connexion Mistral API: {e}")
            return False