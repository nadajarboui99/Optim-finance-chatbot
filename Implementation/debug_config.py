import os
from dotenv import load_dotenv

# Script de débogage pour vérifier la configuration
def debug_config():
    print("=== DEBUG CONFIGURATION ===")
    
    # 1. Vérifier si le fichier .env existe
    env_file = ".env"
    if os.path.exists(env_file):
        print(f"Fichier .env trouvé: {os.path.abspath(env_file)}")
    else:
        print(f"Fichier .env non trouvé dans: {os.getcwd()}")
        return
    
    # 2. Charger les variables d'environnement
    load_dotenv()
    
    # 3. Vérifier les variables importantes
    api_key = os.getenv('OPENAI_API_KEY')
    model = os.getenv('LLM_MODEL')
    
    print(f"\n=== VARIABLES D'ENVIRONNEMENT ===")
    print(f"OPENAI_API_KEY présente: {'yes' if api_key else 'no'}")
    if api_key:
        # Masquer la clé pour la sécurité, juste montrer le début et la longueur
        masked_key = api_key[:10] + "*" * (len(api_key) - 10) if len(api_key) > 10 else "***"
        print(f"OPENAI_API_KEY (masquée): {masked_key}")
        print(f"Longueur de la clé: {len(api_key)} caractères")
        
        # Vérifier le format de la clé OpenRouter
        if api_key.startswith('sk-or-v1-'):
            print(" Format de clé OpenRouter correct")
        elif api_key.startswith('sk-'):
            print("  Semble être une clé OpenAI, pas OpenRouter")
        else:
            print(" Format de clé non reconnu")
    
    print(f"LLM_MODEL: {model if model else ' Non définie'}")
    
    # 4. Tester l'import de config
    try:
        from config import Config
        print(f"\n=== CONFIG.PY ===")
        print(f"Config.OPENAI_API_KEY présente: {'yes' if hasattr(Config, 'OPENAI_API_KEY') and Config.OPENAI_API_KEY else 'no'}")
        print(f"Config.LLM_MODEL: {Config.LLM_MODEL if hasattr(Config, 'LLM_MODEL') else ' Non définie'}")
        
        if hasattr(Config, 'OPENAI_API_KEY') and Config.OPENAI_API_KEY:
            masked_config_key = Config.OPENAI_API_KEY[:10] + "*" * (len(Config.OPENAI_API_KEY) - 10)
            print(f"Config.OPENAI_API_KEY (masquée): {masked_config_key}")
        
    except Exception as e:
        print(f"Erreur lors de l'import de config: {e}")
    
    # 5. Test direct de connexion
    print(f"\n=== TEST DE CONNEXION DIRECT ===")
    if api_key and model:
        try:
            import openai
            
            client = openai.OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=api_key,
            )
            
            print("Tentative de connexion à OpenRouter...")
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "Test"}],
                max_tokens=5
            )
            print("Connexion réussie!")
            
        except Exception as e:
            print(f" Erreur de connexion: {e}")
    else:
        print(" Impossible de tester - clé API ou modèle manquant")

if __name__ == "__main__":
    debug_config()