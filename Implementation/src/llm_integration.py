import os
import sys
# Résoudre le problème des tokenizers Hugging Face
os.environ["TOKENIZERS_PARALLELISM"] = "false"
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
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
                # Utiliser open-mistral-7b par défaut (le plus rapide selon tes tests)
                self.model = "open-mistral-7b"
                print("Aucun modèle spécifié, utilisation de open-mistral-7b")
            else:
                self.model = Config.LLM_MODEL
            
            self.api_key = Config.MISTRAL_API_KEY
            
            # Initialiser le client Mistral
            print(f"Initialisation du client Mistral avec le modèle: {self.model}")
            self.client = Mistral(api_key=self.api_key)
            
            print(f"✅ LLM initialisé avec Mistral API, modèle: {self.model}")
            
        except Exception as e:
            print(f"❌ Erreur lors de l'initialisation du LLM: {e}")
            traceback.print_exc()
            raise
    
    def create_prompt(self, user_query: str, retrieved_chunks: List[Dict[str, Any]], intent: Optional[str] = None) -> str:
        """Créer le prompt optimisé pour OPTIM Finance avec timing"""
        
        start_time = time.time()
        try:
            print(f"🔄 Création du prompt...")
            
            # Construire le contexte à partir des chunks récupérés
            context_parts = []
            for i, chunk in enumerate(retrieved_chunks):
                # Vérifier la structure du chunk
                if not isinstance(chunk, dict):
                    print(f"⚠️ WARNING: Chunk {i} n'est pas un dictionnaire: {type(chunk)}")
                    continue
                
                # Récupérer title et content avec des valeurs par défaut
                title = chunk.get('title', chunk.get('filename', f'Document {i+1}'))
                content = chunk.get('content', chunk.get('text', ''))
                
                # Vérifier que le contenu n'est pas vide
                if content and str(content).strip():
                    context_parts.append(f"**{title}**\n{content}")
                else:
                    print(f"⚠️ WARNING: Chunk {i} a un contenu vide")
            
            context = "\n\n".join(context_parts)
            
            # Vérifier que nous avons du contexte
            if not context.strip():
                print(f"⚠️ WARNING: Aucun contexte valide trouvé parmi {len(retrieved_chunks)} chunks")
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
            
            end_time = time.time()
            prompt_time = end_time - start_time
            
            print(f"✅ Prompt créé en {prompt_time:.3f}s - Longueur: {len(prompt)} caractères")
            return prompt
            
        except Exception as e:
            end_time = time.time()
            prompt_time = end_time - start_time
            print(f"❌ Erreur lors de la création du prompt en {prompt_time:.3f}s: {e}")
            traceback.print_exc()
            raise
    
    def generate_response(self, user_query: str, retrieved_chunks: List[Dict[str, Any]], intent: Optional[str] = None) -> Dict[str, Any]:
        """Générer une réponse avec timing détaillé pour diagnostic"""
        
        total_start_time = time.time()
        timings = {}
        
        try:
            print(f"\n{'='*60}")
            print(f"🚀 DÉBUT GÉNÉRATION DE RÉPONSE")
            print(f"Query: '{user_query}'")
            print(f"Chunks: {len(retrieved_chunks)}")
            print(f"Intent: {intent}")
            print(f"Modèle: {self.model}")
            print(f"{'='*60}")
            
            # 1. Analyse des chunks
            chunks_start = time.time()
            for i, chunk in enumerate(retrieved_chunks[:3]):  # Limiter à 3 pour le debug
                print(f"📄 Chunk {i+1} - Clés: {list(chunk.keys())}")
                content_preview = str(chunk.get('content', ''))[:100]
                print(f"   Contenu: {content_preview}...")
            chunks_end = time.time()
            timings['chunks_analysis'] = chunks_end - chunks_start
            
            # 2. Création du prompt
            prompt_start = time.time()
            prompt = self.create_prompt(user_query, retrieved_chunks, intent)
            prompt_end = time.time()
            timings['prompt_creation'] = prompt_end - prompt_start
            
            # 3. Préparation des messages
            messages_start = time.time()
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
            messages_end = time.time()
            timings['messages_prep'] = messages_end - messages_start
            
            # 4. Appel à l'API Mistral
            api_start = time.time()
            print(f"🔄 Envoi vers Mistral API ({self.model})...")
            
            response = self.client.chat.complete(
                model=self.model,
                messages=messages,
                max_tokens=400,    # Optimisé pour la vitesse
                temperature=0.2,   # Bas pour vitesse + cohérence
                top_p=0.9
            )
            
            api_end = time.time()
            timings['api_call'] = api_end - api_start
            
            print(f"✅ Réponse reçue de l'API en {timings['api_call']:.3f}s")
            
            # 5. Traitement de la réponse
            processing_start = time.time()
            
            response_content = response.choices[0].message.content
            if response_content is None or not response_content.strip():
                response_content = "Désolé, je n'ai pas pu générer une réponse appropriée. Contactez notre équipe pour plus d'informations."
            
            # Créer la liste des sources
            sources = []
            for i, chunk in enumerate(retrieved_chunks):
                chunk_id = chunk.get('id', f'source_{i+1}')
                sources.append(chunk_id)
            
            processing_end = time.time()
            timings['response_processing'] = processing_end - processing_start
            
            # Temps total
            total_end_time = time.time()
            total_time = total_end_time - total_start_time
            
            # Affichage détaillé des timings
            print(f"\n📊 ANALYSE DES TEMPS DE RÉPONSE:")
            print(f"   📄 Analyse chunks:     {timings['chunks_analysis']:.3f}s")
            print(f"   📝 Création prompt:    {timings['prompt_creation']:.3f}s") 
            print(f"   💬 Préparation msgs:   {timings['messages_prep']:.3f}s")
            print(f"   🌐 Appel API Mistral:  {timings['api_call']:.3f}s")
            print(f"   ⚙️ Traitement réponse: {timings['response_processing']:.3f}s")
            print(f"   ⏱️ TEMPS TOTAL:        {total_time:.3f}s")
            print(f"{'='*60}")
            
            return {
                'response': response_content.strip(),
                'sources': sources,
                'intent': intent,
                'provider': 'mistral',
                'model': self.model,
                'timings': timings,
                'total_time': total_time,
                'success': True
            }
            
        except Exception as e:
            total_end_time = time.time()
            total_time = total_end_time - total_start_time
            
            error_msg = f"Erreur Mistral API: {str(e)}"
            print(f"❌ ERREUR après {total_time:.3f}s: {error_msg}")
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
                'total_time': total_time,
                'timings': timings,
                'success': False
            }
    
    def test_connection(self) -> bool:
        """Tester la connexion à l'API Mistral"""
        try:
            print("\n🔍 TEST DE CONNEXION MISTRAL")
            start_time = time.time()
            
            messages = [{"role": "user", "content": "Test"}]
            
            response = self.client.chat.complete(
                model=self.model,
                messages=messages,
                max_tokens=5
            )
            
            end_time = time.time()
            response_time = end_time - start_time
            
            print(f"✅ Connexion OK en {response_time:.3f}s")
            return True
            
        except Exception as e:
            print(f"❌ Erreur de connexion: {e}")
            return False

# Test direct pour diagnostiquer le problème
def diagnose_chatbot_performance():
    """Diagnostic complet des performances du chatbot"""
    
    print("🔍 DIAGNOSTIC PERFORMANCE CHATBOT")
    print("="*60)
    
    try:
        # Simuler des chunks comme dans ton vrai chatbot
        fake_chunks = [
            {
                'id': 'doc_1',
                'title': 'Services OPTIM Finance',
                'content': 'OPTIM Finance propose des solutions pour freelances IT incluant portage salarial, micro-entreprise, et EURL.'
            },
            {
                'id': 'doc_2', 
                'title': 'Tarifs',
                'content': 'Nos tarifs commencent à partir de 5% pour le portage salarial.'
            }
        ]
        
        # Test avec différentes requêtes
        test_queries = [
            "Quels sont vos services?",
            "Combien coûte le portage salarial?",
            "Je veux créer une micro-entreprise"
        ]
        
        llm = LLMIntegration()
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n🔄 TEST {i}: '{query}'")
            result = llm.generate_response(query, fake_chunks, 'general')
            
            if result['success']:
                print(f"✅ Test {i} réussi en {result['total_time']:.3f}s")
            else:
                print(f"❌ Test {i} échoué: {result.get('error', 'Erreur inconnue')}")
    
    except Exception as e:
        print(f"❌ Erreur lors du diagnostic: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    diagnose_chatbot_performance()