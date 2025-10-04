import os
import re
os.environ["TOKENIZERS_PARALLELISM"] = "false"
import sys
from mistralai.client import MistralClient
from typing import List, Dict, Any, Optional
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config
import traceback

class LLMIntegration:
    def __init__(self):
        try:
            if not hasattr(Config, 'MISTRAL_API_KEY') or not Config.MISTRAL_API_KEY:
                raise ValueError("MISTRAL_API_KEY manquante dans la configuration")
            
            if not hasattr(Config, 'LLM_MODEL') or not Config.LLM_MODEL:
                self.model = "open-mistral-7b"
                print("Aucun modèle spécifié, utilisation de open-mistral-7b")
            else:
                self.model = Config.LLM_MODEL
            
            self.api_key = Config.MISTRAL_API_KEY
            self.client = MistralClient(api_key=self.api_key)
            
            print(f"LLM initialisé avec Mistral API, modèle: {self.model}")
            
        except Exception as e:
            print(f"Erreur lors de l'initialisation du LLM: {e}")
            raise
    
    def analyze_query_intent(self, query: str) -> dict:
        """Analyser ce que l'utilisateur demande VRAIMENT"""
        query_lower = query.lower()
        
        # Question de contact
        if any(word in query_lower for word in ['contacter', 'contact', 'joindre', 'appeler', 'écrire', 'email', 'téléphone', 'mail']):
            return {'type': 'contact', 'expected_length': 'very_short', 'max_tokens': 80}
        
        # Question qui/quoi (présentation)
        elif any(word in query_lower for word in ['qui est', 'qui êtes', 'c\'est quoi', 'qu\'est-ce', 'présentez']):
            return {'type': 'definition', 'expected_length': 'short', 'max_tokens': 120}
        
        # Question comment (processus)
        elif 'comment' in query_lower:
            return {'type': 'process', 'expected_length': 'medium', 'max_tokens': 250}
        
        # Question tarif/prix
        elif any(word in query_lower for word in ['tarif', 'prix', 'coût', 'combien', 'frais']):
            return {'type': 'pricing', 'expected_length': 'short', 'max_tokens': 100}
        
        # Question différence/comparaison
        elif any(word in query_lower for word in ['différence', 'comparer', 'vs', 'mieux', 'choisir entre']):
            return {'type': 'comparison', 'expected_length': 'medium', 'max_tokens': 200}
        
        # Défaut
        else:
            return {'type': 'general', 'expected_length': 'medium', 'max_tokens': 200}
    
    def create_prompt(self, user_query: str, retrieved_chunks: List[Dict[str, Any]], intent: Optional[str] = None) -> tuple:
        """Créer le prompt optimisé pour OPTIM Finance avec analyse intelligente"""
        
        try:
            # Analyser ce que veut vraiment l'utilisateur
            query_analysis = self.analyze_query_intent(user_query)
            
            # Adapter le contexte selon le type
            max_chunks = 1 if query_analysis['type'] == 'contact' else 2
            max_context_length = 150 if query_analysis['type'] in ['contact', 'pricing'] else 300
            
            # Construire le contexte (LIMITÉ aux infos essentielles)
            context_parts = []
            for i, chunk in enumerate(retrieved_chunks[:max_chunks]):
                if not isinstance(chunk, dict):
                    continue
                
                title = chunk.get('title', chunk.get('filename', f'Document {i+1}'))
                content = chunk.get('content', chunk.get('text', ''))
                
                if content and str(content).strip():
                    preview = content[:max_context_length]
                    context_parts.append(f"{title}: {preview}")
            
            context = "\n".join(context_parts)
            
            if not context.strip():
                context = "Informations limitées disponibles."
            
            # Instructions selon le type de question
            length_instructions = {
                'contact': "Donne UNIQUEMENT les coordonnées de contact. 1-2 phrases MAX.",
                'definition': "Présentation en 2-3 phrases. Pas de détails techniques.",
                'pricing': "Donne le prix et ce qu'il inclut. 2-3 phrases MAX.",
                'process': "Liste les étapes principales uniquement.",
                'comparison': "Compare les points clés uniquement.",
                'general': "Réponds précisément sans détails superflus."
            }
            
            instruction = length_instructions[query_analysis['type']]
            
            prompt = f"""Tu es l'assistant d'OPTIM Finance.

CONTEXTE :
{context}

QUESTION : {user_query}

INSTRUCTION : {instruction}

RÈGLE CRITIQUE : Dès que tu as répondu à la question → ARRÊTE IMMÉDIATEMENT. Ne parle PAS d'autres services/avantages non demandés.

RÉPONSE :"""
            
            return prompt, query_analysis
            
        except Exception as e:
            print(f"Erreur lors de la création du prompt: {e}")
            traceback.print_exc()
            raise
    
    def generate_response(self, user_query: str, retrieved_chunks: List[Dict[str, Any]], intent: Optional[str] = None) -> Dict[str, Any]:
        """Générer une réponse avec le LLM Mistral"""
        try:
            print(f"Génération de réponse pour: '{user_query}'")
            
            # Créer le prompt et obtenir l'analyse
            prompt, query_analysis = self.create_prompt(user_query, retrieved_chunks, intent)
            
            # System prompt adaptatif
            system_content = {
                'contact': "Tu donnes uniquement les coordonnées de contact. Rien d'autre.",
                'definition': "Tu présentes brièvement l'entreprise en 2-3 phrases.",
                'pricing': "Tu donnes le prix et ce qu'il inclut. Point.",
                'process': "Tu expliques les étapes principales.",
                'comparison': "Tu compares les options demandées.",
                'general': "Tu réponds précisément à la question posée."
            }
            
            messages = [
                {
                    "role": "system",
                    "content": system_content[query_analysis['type']] + " Dès que la réponse est complète, tu t'arrêtes."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            
            print(f"Type de question détecté: {query_analysis['type']}")
            print(f"Tokens max alloués: {query_analysis['max_tokens']}")
            print("Appel à l'API Mistral...")
            
            # Appel à l'API Mistral avec paramètres adaptés
            response = self.client.chat(
                model=self.model,
                messages=messages,
                max_tokens=query_analysis['max_tokens'],
                temperature=0.3,
                top_p=0.9,
                stop=[
                    "\n\nEn ce qui concerne",
                    "\n\nEn choisissant",
                    "\n\nEn outre",
                    "\n\nChez OPTIM Finance",
                    "\n\nNous proposons",
                    "\n\nVous bénéficiez",
                    "\n\nPar ailleurs"
                ]
            )
            
            print("Réponse reçue de Mistral API")
            
            response_content = response.choices[0].message.content
            if response_content is None or not response_content.strip():
                response_content = f"Désolé, je n'ai pas pu générer une réponse. Contactez notre équipe à {Config.CONTACT_EMAIL}"
            
            response_content = response_content.strip()
            
            # POST-TRAITEMENT INTELLIGENT : Détecter si le modèle a commencé à divaguer
            divagation_markers = [
                'en ce qui concerne', 'en outre', 'par ailleurs', 
                'nous proposons également', 'vous bénéficiez',
                'en choisissant', 'chez optim finance, nous'
            ]
            
            for marker in divagation_markers:
                marker_pos = response_content.lower().find(marker)
                if marker_pos > 50:  # Si trouvé après 50 caractères
                    # Couper juste avant
                    last_period = response_content[:marker_pos].rfind('.')
                    if last_period > 0:
                        response_content = response_content[:last_period + 1]
                        print(f"Divagation détectée et coupée à '{marker}'")
                        break
            
            # Couper phrases incomplètes à la fin
            last_punct = max(
                response_content.rfind('.'),
                response_content.rfind('!'),
                response_content.rfind('?')
            )
            if 0 < last_punct < len(response_content) - 10:
                response_content = response_content[:last_punct + 1]
                print("Phrase incomplète coupée")
            
            sources = [chunk.get('id', f'source_{i+1}') for i, chunk in enumerate(retrieved_chunks)]
            
            print(f"Réponse finale générée ({len(response_content)} caractères)")
            
            return {
                'response': response_content,
                'sources': sources,
                'intent': intent,
                'provider': 'mistral',
                'model': self.model,
                'query_type': query_analysis['type'],
                'success': True
            }
            
        except Exception as e:
            if "authentication" in str(e).lower() or "unauthorized" in str(e).lower():
                error_msg = "Erreur d'authentification Mistral"
                print(f"{error_msg}: {e}")
                return {
                    'response': f"Erreur technique. Contactez {Config.CONTACT_EMAIL}",
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
                    'response': f"Service surchargé. Réessayez ou contactez {Config.CONTACT_EMAIL}",
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
                traceback.print_exc()
                
                return {
                    'response': f"Erreur survenue. Contactez {Config.CONTACT_EMAIL}",
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
            test_messages = [{"role": "user", "content": "Test"}]
            
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