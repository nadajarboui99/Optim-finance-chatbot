#!/usr/bin/env python3
"""
Script pour tester et lister les modèles disponibles sur OpenRouter
"""
import requests
import os
from config import Config

def list_openrouter_models():
    """Lister tous les modèles disponibles sur OpenRouter"""
    try:
        headers = {
            'Authorization': f'Bearer {Config.OPENAI_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        print("🔍 Récupération des modèles OpenRouter...")
        response = requests.get(
            'https://openrouter.ai/api/v1/models',
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            models_data = response.json()
            all_models = models_data.get('data', [])
            
            print(f"Total des modèles disponibles: {len(all_models)}")
            
            # Filtrer les modèles gratuits
            free_models = []
            openchat_models = []
            
            for model in all_models:
                model_id = model.get('id', '')
                pricing = model.get('pricing', {})
                
                # Modèles gratuits
                if ':free' in model_id or (
                    isinstance(pricing.get('prompt'), str) and 
                    pricing.get('prompt') == '0' and 
                    pricing.get('completion') == '0'
                ):
                    free_models.append(model_id)
                
                # Modèles OpenChat
                if 'openchat' in model_id.lower():
                    openchat_models.append({
                        'id': model_id,
                        'name': model.get('name', ''),
                        'pricing': pricing
                    })
            
            print(f"\nMODÈLES GRATUITS ({len(free_models)}):")
            for model in sorted(free_models):
                print(f"  ✓ {model}")
            
            print(f"\nMODÈLES OPENCHAT ({len(openchat_models)}):")
            for model in openchat_models:
                status = "GRATUIT" if model['id'] in free_models else "PAYANT"
                print(f"  • {model['id']} - {status}")
                if model['name']:
                    print(f"    Nom: {model['name']}")
                print(f"    Pricing: {model['pricing']}")
                print()
            
            # Suggestions spécifiques
            print("SUGGESTIONS POUR VOTRE .env:")
            suggestions = [
                'openchat/openchat-7b:free',
                'openchat/openchat-7b', 
                'openchat/openchat-3.5-7b',
                'deepseek/deepseek-v3',
                'meta-llama/llama-3.2-3b-instruct:free'
            ]
            
            for suggestion in suggestions:
                if suggestion in [m['id'] for m in all_models]:
                    status = " DISPONIBLE"
                    if suggestion in free_models:
                        status += " (GRATUIT)"
                else:
                    status = " NON DISPONIBLE"
                print(f"  {suggestion} - {status}")
                
        else:
            print(f" Erreur HTTP {response.status_code}: {response.text}")
            
    except Exception as e:
        print(f" Erreur: {e}")

def test_specific_model(model_name):
    """Tester un modèle spécifique"""
    try:
        import openai
        
        client = openai.OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=Config.OPENAI_API_KEY,
        )
        
        print(f" Test du modèle: {model_name}")
        
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": "Bonjour"}],
            max_tokens=10,
            timeout=10
        )
        
        print(f" Modèle {model_name} fonctionne!")
        print(f"Réponse: {response.choices[0].message.content}")
        return True
        
    except Exception as e:
        print(f" Modèle {model_name} échoue: {e}")
        return False

if __name__ == "__main__":
    print(" Test des modèles OpenRouter\n")
    
    # Lister tous les modèles
    list_openrouter_models()
    
    # Tester des modèles spécifiques
    print("\n" + "="*50)
    print(" TESTS DE MODÈLES SPÉCIFIQUES")
    print("="*50)
    
    models_to_test = [
        "agentica-org/deepcoder-14b-preview:free",
            "arliai/qwq-32b-arliai-rpr-v1:free",
            "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
            "cognitivecomputations/dolphin3.0-mistral-24b:free",
            "cognitivecomputations/dolphin3.0-r1-mistral-24b:free",
            "deepseek/deepseek-chat-v3-0324:free",
            "deepseek/deepseek-r1-0528-qwen3-8b:free",
            "deepseek/deepseek-r1-0528:free",
            "deepseek/deepseek-r1-distill-llama-70b:free",
            "deepseek/deepseek-r1-distill-qwen-14b:free",
            "deepseek/deepseek-r1:free",
            "featherless/qwerky-72b:free",
            "google/gemini-2.0-flash-exp:free",
            "google/gemma-2-9b-it:free",
            "google/gemma-3-12b-it:free",
            "google/gemma-3-27b-it:free",
            "google/gemma-3-4b-it:free",
            "google/gemma-3n-e2b-it:free",
            "google/gemma-3n-e4b-it:free",
            "meta-llama/llama-3.1-405b-instruct:free",
            "meta-llama/llama-3.2-11b-vision-instruct:free",
            "meta-llama/llama-3.2-3b-instruct:free",
            "meta-llama/llama-3.3-70b-instruct:free",
            "microsoft/mai-ds-r1:free",
            "mistralai/devstral-small-2505:free",
            "mistralai/mistral-7b-instruct:free",
            "mistralai/mistral-nemo:free",
            "mistralai/mistral-small-24b-instruct-2501:free",
            "mistralai/mistral-small-3.1-24b-instruct:free",
            "mistralai/mistral-small-3.2-24b-instruct:free",
            "moonshotai/kimi-dev-72b:free",
            "moonshotai/kimi-k2:free",
            "moonshotai/kimi-vl-a3b-thinking:free",
            "nousresearch/deephermes-3-llama-3-8b-preview:free",
            "nvidia/llama-3.1-nemotron-ultra-253b-v1:free",
            "qwen/qwen-2.5-72b-instruct:free",
            "qwen/qwen-2.5-coder-32b-instruct:free",
            "qwen/qwen2.5-vl-32b-instruct:free",
            "qwen/qwen2.5-vl-72b-instruct:free",
            "qwen/qwen3-14b:free",
            "qwen/qwen3-235b-a22b-07-25:free",
            "qwen/qwen3-235b-a22b:free",
            "qwen/qwen3-30b-a3b:free",
            "qwen/qwen3-4b:free",
            "qwen/qwen3-8b:free",
            "qwen/qwen3-coder:free",
            "qwen/qwq-32b:free",
            "rekaai/reka-flash-3:free",
            "sarvamai/sarvam-m:free",
            "shisa-ai/shisa-v2-llama3.3-70b:free",
            "tencent/hunyuan-a13b-instruct:free",
            "thudm/glm-4-32b:free",
            "thudm/glm-z1-32b:free",
            "tngtech/deepseek-r1t-chimera:free",
            "tngtech/deepseek-r1t2-chimera:free"
    ]
    
    working_models = []
    for model in models_to_test:
        if test_specific_model(model):
            working_models.append(model)
        print()
    
    print("="*50)
    print(f" MODÈLES FONCTIONNELS ({len(working_models)}):")
    for model in working_models:
        print(f"  ✓ {model}")
    
    if working_models:
        print(f"\n Recommandation: Utilisez {working_models[0]} dans votre .env")
        print(f"LLM_MODEL={working_models[0]}")