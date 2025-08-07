#!/usr/bin/env python3
"""
Optimized persistent chatbot for OPTIM Finance
Keeps the chatbot initialized and processes requests via stdin/stdout for maximum speed
"""

import os
import sys
import json
import time
import traceback
from io import StringIO

# Résoudre le problème des tokenizers Hugging Face
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Rediriger les warnings et logs non critiques
import warnings
warnings.filterwarnings("ignore")

from typing import Dict, Any, List, Optional
from search import SearchEngine
from llm_integration import LLMIntegration
from config import Config

class NullWriter:
    """Classe pour rediriger stdout/stderr vers nulle part"""
    def write(self, x): pass
    def flush(self): pass

class PersistentOptimFinanceChatbot:
    def __init__(self):
        self.chatbot = None
        self.is_initialized = False
        self.initialization_start = time.time()
        
        # Rediriger toutes les sorties pendant l'initialisation
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        
    def initialize(self):
        """Initialiser le chatbot UNE SEULE FOIS au démarrage"""
        try:
            # Rediriger les sorties pendant l'initialisation
            sys.stdout = NullWriter()
            sys.stderr = NullWriter()
            
            # Utiliser votre classe OptimFinanceChatbot existante
            from chatbot import OptimFinanceChatbot
            
            # Créer l'instance du chatbot en mode silencieux
            self.chatbot = OptimFinanceChatbot(silent_mode=True)
            
            # Initialiser le chatbot (cette opération coûteuse ne se fait qu'une fois)
            self.chatbot.initialize()
            
            # Restaurer les sorties
            sys.stdout = self.original_stdout
            sys.stderr = self.original_stderr
            
            self.is_initialized = True
            initialization_time = time.time() - self.initialization_start
            
            # Signaler à Node.js que nous sommes prêts
            sys.stderr.write(f"READY - Initialized in {initialization_time:.2f}s\n")
            sys.stderr.flush()
            
            return True
            
        except Exception as e:
            # Restaurer les sorties en cas d'erreur
            sys.stdout = self.original_stdout
            sys.stderr = self.original_stderr
            
            sys.stderr.write(f"Initialization error: {str(e)}\n")
            sys.stderr.flush()
            return False
    
    def process_message(self, message: str) -> Dict[str, Any]:
        """Traiter un message - rapide car le chatbot est déjà initialisé"""
        if not self.is_initialized or not self.chatbot:
            return {
                "success": False,
                "error": "Chatbot not initialized"
            }
        
        try:
            start_time = time.time()
            
            # Rediriger temporairement les sorties pour éviter le spam
            sys.stdout = NullWriter()
            sys.stderr = NullWriter()
            
            # Utiliser votre méthode process_query existante
            response = self.chatbot.process_query(
                user_query=message,
                search_type="hybrid",  # Vous pouvez ajuster selon vos besoins
                top_k=None
            )
            
            # Restaurer les sorties
            sys.stdout = self.original_stdout
            sys.stderr = self.original_stderr
            
            processing_time = time.time() - start_time
            
            # Extraire la réponse selon votre format existant
            if response.get('success', True) and not response.get('error'):
                return {
                    "success": True,
                    "response": response['response'],
                    "processing_time": processing_time,
                    "confidence": response.get('confidence', 'unknown'),
                    "intent": response.get('intent', 'unknown'),
                    "num_sources": response.get('num_sources', 0)
                }
            else:
                return {
                    "success": False,
                    "error": response.get('error', 'Unknown error'),
                    "response": response.get('response', 'Une erreur est survenue'),
                    "processing_time": processing_time
                }
                
        except Exception as e:
            # Restaurer les sorties en cas d'erreur
            sys.stdout = self.original_stdout
            sys.stderr = self.original_stderr
            
            error_msg = f"Processing error: {str(e)}"
            return {
                "success": False,
                "error": error_msg,
                "response": f"Désolé, une erreur est survenue. Veuillez contacter notre équipe à {Config.CONTACT_EMAIL if 'Config' in globals() else 'contact@optim-finance.com'}",
                "processing_time": time.time() - start_time if 'start_time' in locals() else 0
            }
    
    def run(self):
        """Boucle principale - écouter les requêtes sur stdin et répondre sur stdout"""
        sys.stderr.write("Starting OPTIM Finance Chatbot persistent process...\n")
        sys.stderr.flush()
        
        # Initialiser le chatbot une seule fois
        if not self.initialize():
            sys.stderr.write("Failed to initialize chatbot. Exiting.\n")
            sys.stderr.flush()
            sys.exit(1)
        
        sys.stderr.write("Chatbot ready to process requests\n")
        sys.stderr.flush()
        
        while True:
            try:
                # Lire la requête depuis stdin
                line = sys.stdin.readline()
                if not line:
                    break  # EOF
                
                line = line.strip()
                if not line:
                    continue
                
                # Parser la requête JSON
                try:
                    request = json.loads(line)
                    request_id = request.get('requestId', 'unknown')
                    message = request.get('message', '').strip()
                    
                    if not message:
                        response = {
                            "requestId": request_id,
                            "error": "Empty message"
                        }
                    else:
                        # Traiter le message avec votre chatbot
                        result = self.process_message(message)
                        
                        if result["success"]:
                            response = {
                                "requestId": request_id,
                                "result": result["response"],
                                "processing_time": result["processing_time"],
                                "confidence": result.get("confidence", "unknown"),
                                "intent": result.get("intent", "unknown"),
                                "num_sources": result.get("num_sources", 0)
                            }
                        else:
                            response = {
                                "requestId": request_id,
                                "error": result["error"],
                                "result": result.get("response", "Une erreur est survenue")
                            }
                
                except json.JSONDecodeError as e:
                    response = {
                        "requestId": "unknown",
                        "error": f"Invalid JSON: {str(e)}"
                    }
                
                # Envoyer la réponse
                sys.stdout.write(json.dumps(response, ensure_ascii=False) + '\n')
                sys.stdout.flush()
                
            except KeyboardInterrupt:
                sys.stderr.write("Received interrupt signal\n")
                sys.stderr.flush()
                break
            except Exception as e:
                sys.stderr.write(f"Unexpected error in main loop: {str(e)}\n")
                sys.stderr.flush()
                
                # Essayer d'envoyer une réponse d'erreur
                try:
                    error_response = {
                        "requestId": "unknown",
                        "error": f"Unexpected error: {str(e)}",
                        "result": "Une erreur technique est survenue"
                    }
                    sys.stdout.write(json.dumps(error_response, ensure_ascii=False) + '\n')
                    sys.stdout.flush()
                except:
                    pass
        
        sys.stderr.write("OPTIM Finance Chatbot persistent process ending\n")
        sys.stderr.flush()

if __name__ == "__main__":
    # Vérifier si on est en mode persistant ou en mode unique
    if len(sys.argv) == 1:
        # Mode persistant - nouvelle approche optimisée
        chatbot = PersistentOptimFinanceChatbot()
        chatbot.run()
    else:
        # Mode unique - compatibilité avec votre code existant
        question = sys.argv[1]
        
        # Importer votre classe originale
        from chatbot import OptimFinanceChatbot
        
        # Sauvegarder les références originales
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        
        try:
            # Rediriger TOUTES les sorties vers null pendant l'initialisation et le traitement
            sys.stdout = NullWriter()
            sys.stderr = NullWriter()
            
            # Créer le chatbot en mode silencieux (votre code original)
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