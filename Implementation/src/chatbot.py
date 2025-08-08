import os
import sys
# Résoudre le problème des tokenizers Hugging Face
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from typing import Dict, Any, List, Optional
from search import SearchEngine
from llm_integration import LLMIntegration
from config import Config
import traceback

class OptimFinanceChatbot:
    def __init__(self, silent_mode: bool = False, use_chromadb=True):
        self.search_engine = SearchEngine(use_chromadb=use_chromadb)
        self.llm = LLMIntegration()
        self.is_initialized = False
        self.silent_mode = silent_mode
    
    def _print(self, message: str):
        """Print conditionnel selon le mode silencieux"""
        if not self.silent_mode:
            print(message)
    
    def initialize(self) -> None:
        """Initialiser le chatbot"""
        self._print("Initialisation du chatbot OPTIM Finance...")
        try:
            # Initialiser le moteur de recherche
            self.search_engine.initialize()
            
            # Tester la connexion LLM
            if self.llm.test_connection():
                self.is_initialized = True
                self._print("✅ Chatbot initialisé avec succès!")
            else:
                self._print("❌ Erreur: Impossible de se connecter au LLM")
                raise Exception("Échec de l'initialisation du LLM")
                
        except Exception as e:
            self._print(f"❌ Erreur lors de l'initialisation: {e}")
            raise
    
    def process_query(self, user_query: str, search_type: str = "hybrid", top_k: Optional[int] = None) -> Dict[str, Any]:
        """Traiter une requête utilisateur complète"""
        if not self.is_initialized:
            return {
                'query': user_query,
                'response': 'Chatbot non initialisé. Appelez initialize() d\'abord.',
                'error': 'not_initialized',
                'confidence': 'error'
            }
        
        try:
            self._print(f"\n{'='*50}")
            self._print(f"🔍 TRAITEMENT DE LA REQUÊTE: '{user_query}'")
            self._print(f"{'='*50}")
            
            # 1. Recherche dans la base de connaissances
            self._print("📚 Étape 1: Recherche dans la base de connaissances...")
            search_results = self.search_engine.search(
                query=user_query,
                search_type=search_type,
                top_k=top_k
            )
            
            self._print(f"📊 Résultats de recherche:")
            self._print(f"  - Nombre de résultats: {len(search_results['results'])}")
            self._print(f"  - Intention détectée: {search_results['intent']}")
            
            # 2. Vérifier si on a des résultats pertinents
            if not search_results['results']:
                self._print("⚠️ Aucun résultat pertinent trouvé")
                return {
                    'query': user_query,
                    'response': f"Je n'ai pas trouvé d'informations spécifiques sur votre question. Pour une réponse personnalisée, contactez notre équipe à {Config.CONTACT_EMAIL} ou au {Config.CONTACT_PHONE}.",
                    'intent': search_results['intent'],
                    'sources': [],
                    'confidence': 'low',
                    'num_sources': 0,
                    'search_type': search_type
                }
            
            # Debug: afficher les premiers résultats
            if not self.silent_mode:
                self._print(f"🔍 Aperçu des résultats:")
                for i, result in enumerate(search_results['results'][:2]):
                    score = result.get('final_score', result.get('similarity_score', result.get('keyword_score', 0)))
                    self._print(f"  Résultat {i+1} - Score: {score:.3f}")
                    self._print(f"  Titre: {result.get('title', 'N/A')}")
                    self._print(f"  Contenu (preview): {str(result.get('content', ''))[:100]}...")
            
            # 3. Génération de la réponse avec LLM
            self._print("🤖 Étape 2: Génération de la réponse avec LLM...")
            llm_response = self.llm.generate_response(
                user_query=user_query,
                retrieved_chunks=search_results['results'],
                intent=search_results['intent']
            )
            
            # Vérifier si la génération LLM a réussi
            if not llm_response.get('success', True):
                self._print(f"❌ Erreur LLM: {llm_response.get('error', 'Erreur inconnue')}")
                return {
                    'query': user_query,
                    'response': llm_response['response'],  # Message d'erreur déjà formaté
                    'intent': search_results['intent'],
                    'sources': [],
                    'confidence': 'error',
                    'num_sources': len(search_results['results']),
                    'search_type': search_type,
                    'error': llm_response.get('error')
                }
            
            # 4. Évaluer la confiance basée sur les scores
            confidence = self._evaluate_confidence(search_results['results'])
            
            self._print("✅ Réponse générée avec succès!")
            if not self.silent_mode:
                self._print(f"📈 Statistiques finales:")
                self._print(f"  - Confiance: {confidence}")
                self._print(f"  - Sources utilisées: {len(search_results['results'])}")
                self._print(f"  - Longueur de la réponse: {len(llm_response['response'])} caractères")
            
            return {
                'query': user_query,
                'response': llm_response['response'],
                'intent': search_results['intent'],
                'sources': llm_response['sources'],
                'confidence': confidence,
                'num_sources': len(search_results['results']),
                'search_type': search_type,
                'success': True
            }
            
        except Exception as e:
            error_msg = f"Erreur lors du traitement: {str(e)}"
            self._print(f"❌ {error_msg}")
            self._print(f"🔧 Type d'erreur: {type(e).__name__}")
            if not self.silent_mode:
                self._print(f"📋 Stack trace:")
                traceback.print_exc()
            
            return {
                'query': user_query,
                'response': f"Désolé, une erreur est survenue. Veuillez contacter notre équipe à {Config.CONTACT_EMAIL}",
                'error': error_msg,
                'confidence': 'error',
                'intent': 'unknown',
                'sources': [],
                'num_sources': 0,
                'success': False
            }
    
    def _evaluate_confidence(self, results: List[Dict[str, Any]]) -> str:
        """Évaluer la confiance de la réponse basée sur les scores"""
        if not results:
            return 'low'
        
        try:
            # Prendre le meilleur score
            scores = []
            for r in results:
                score = r.get('final_score', r.get('similarity_score', r.get('keyword_score', 0)))
                if isinstance(score, (int, float)):
                    scores.append(score)
            
            if not scores:
                return 'low'
            
            best_score = max(scores)
            
            if best_score > 0.8:
                return 'high'
            elif best_score > 0.6:
                return 'medium'
            else:
                return 'low'
                
        except Exception as e:
            self._print(f"⚠️ Erreur lors de l'évaluation de confiance: {e}")
            return 'low'
    
    def get_suggestions(self, partial_query: str) -> List[str]:
        """Obtenir des suggestions basées sur une requête partielle"""
        suggestions = [
            "Quels sont les tarifs du portage salarial ?",
            "Quelle différence entre auto-entreprise et société ?",
            "Comment vous contacter ?",
            "Quels sont les avantages du portage salarial ?",
            "Combien coûte la création d'une société ?",
            "Qu'est-ce que le portage salarial ?",
            "Quels sont les frais de gestion ?",
            "Comment fonctionne la facturation ?",
            "Quelles sont vos zones d'intervention ?",
            "Comment démarrer avec OPTIM Finance ?"
        ]
        
        if partial_query and len(partial_query.strip()) > 2:
            # Filtrer les suggestions basées sur la requête partielle
            partial_lower = partial_query.lower().strip()
            filtered = [s for s in suggestions if partial_lower in s.lower()]
            return filtered[:3] if filtered else suggestions[:3]
        
        return suggestions[:3]
    
    def get_status(self) -> Dict[str, Any]:
        """Obtenir le statut du chatbot"""
        return {
            'initialized': self.is_initialized,
            'search_engine_ready': hasattr(self.search_engine, 'vectorstore') if hasattr(self, 'search_engine') else False,
            'llm_ready': self.llm.test_connection() if hasattr(self, 'llm') else False
        }

# Interface CLI pour tester
def main():
    try:
        print("🚀 Démarrage du chatbot OPTIM Finance...")
        chatbot = OptimFinanceChatbot(silent_mode=False)  # Mode verbose pour CLI
        
        print("⚡ Initialisation en cours...")
        chatbot.initialize()
        
        print(f"\n{'='*60}")
        print("🤖 Assistant OPTIM Finance - PRÊT")
        print("💡 Tapez 'quit', 'exit' ou 'q' pour quitter")
        print("📊 Tapez 'status' pour voir l'état du système")
        print("❓ Tapez 'help' pour voir les suggestions")
        print(f"{'='*60}")
        
        while True:
            try:
                user_input = input("\n🤔 Votre question: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("👋 Au revoir !")
                    break
                
                if user_input.lower() == 'status':
                    status = chatbot.get_status()
                    print(f"\n📊 Statut du système:")
                    for key, value in status.items():
                        emoji = "✅" if value else "❌"
                        print(f"  {emoji} {key}: {value}")
                    continue
                
                if user_input.lower() == 'help':
                    suggestions = chatbot.get_suggestions("")
                    print(f"\n💡 Suggestions de questions:")
                    for i, suggestion in enumerate(suggestions, 1):
                        print(f"  {i}. {suggestion}")
                    continue
                
                if not user_input:
                    print("⚠️ Veuillez poser une question.")
                    continue
                
                # Traitement de la requête
                response = chatbot.process_query(user_input)
                
                # Affichage de la réponse
                print(f"\n💬 Réponse: {response['response']}")
                print(f"🎯 Intention détectée: {response['intent']}")
                print(f"📊 Confiance: {response['confidence']}")
                print(f"📚 Sources utilisées: {response.get('num_sources', 0)}")
                
                if response.get('error'):
                    print(f"⚠️ Erreur technique: {response['error']}")
                
            except KeyboardInterrupt:
                print("\n⛔ Arrêt demandé par l'utilisateur.")
                break
            except Exception as e:
                print(f"\n❌ Erreur inattendue: {e}")
                traceback.print_exc()
                
    except Exception as e:
        print(f"💥 Erreur critique lors du démarrage: {e}")
        traceback.print_exc()

class NullWriter:
    """Classe pour rediriger stdout/stderr vers nulle part"""
    def write(self, x): pass
    def flush(self): pass

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Mode backend: une seule question en argument - MODE SILENCIEUX TOTAL
        question = sys.argv[1]

        # Sauvegarder les références originales
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        
        try:
            # Rediriger TOUTES les sorties vers null pendant l'initialisation et le traitement
            sys.stdout = NullWriter()
            sys.stderr = NullWriter()
            
            # Créer le chatbot en mode silencieux
            chatbot = OptimFinanceChatbot(silent_mode=True)
            chatbot.initialize()

            response = chatbot.process_query(question)
            
            # Restaurer stdout pour afficher SEULEMENT la réponse
            sys.stdout = original_stdout
            sys.stderr = original_stderr
            
            # Afficher SEULEMENT la réponse pour Node.js
            print(response["response"])
            
        except Exception as e:
            # Restaurer les sorties en cas d'erreur
            sys.stdout = original_stdout
            sys.stderr = original_stderr
            
            # En cas d'erreur, afficher un message d'erreur simple
            print(f"Désolé, une erreur est survenue. Veuillez contacter notre équipe à contact@optim-finance.com")
    else:
        # Mode CLI interactif - MODE VERBOSE
        main()