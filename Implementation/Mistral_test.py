#!/usr/bin/env python3
"""
Script de test standalone pour Mistral API
Utilise ce script pour tester si Mistral fonctionne avant d'intégrer dans ton chatbot
"""

import os
from mistralai import Mistral
import time
import traceback

# Configuration directe (remplace par tes vraies valeurs)
MISTRAL_API_KEY = "your_mistral_api_key_here"  # Remplace par ta vraie clé
TEST_MODEL = "mistral-large-latest"  # ou "mistral-medium-latest" pour plus de vitesse

def test_mistral_basic():
    """Test de base pour vérifier si Mistral API fonctionne"""
    
    print("=== TEST MISTRAL API ===")
    print(f"Clé API: {MISTRAL_API_KEY[:10]}...")
    print(f"Modèle: {TEST_MODEL}")
    
    try:
        # Créer le client
        print("\n1. Initialisation du client...")
        client = Mistral(api_key=MISTRAL_API_KEY)
        print("✅ Client initialisé")
        
        # Test simple
        print("\n2. Test de requête simple...")
        start_time = time.time()
        
        messages = [
            {"role": "user", "content": "Dis juste 'Bonjour'"}
        ]
        
        response = client.chat.complete(
            model=TEST_MODEL,
            messages=messages,
            max_tokens=10,
            temperature=0.1
        )
        
        end_time = time.time()
        response_time = end_time - start_time
        
        print(f"✅ Réponse reçue en {response_time:.2f} secondes")
        print(f"Contenu: '{response.choices[0].message.content}'")
        
        return True, response_time
        
    except Exception as e:
        print(f"❌ ERREUR: {e}")
        print(f"Type: {type(e).__name__}")
        traceback.print_exc()
        return False, 0

def test_different_models():
    """Teste différents modèles pour voir lesquels fonctionnent"""
    
    models = [
        "mistral-large-latest",
        "mistral-medium-latest",
        "mistral-small-latest",
        "open-mistral-7b",
        "open-mixtral-8x7b",
        "open-mixtral-8x22b"
    ]
    
    print("\n=== TEST DE DIFFÉRENTS MODÈLES ===")
    
    client = Mistral(api_key=MISTRAL_API_KEY)
    results = {}
    
    for model in models:
        print(f"\nTest: {model}")
        try:
            start_time = time.time()
            
            messages = [{"role": "user", "content": "Test"}]
            
            response = client.chat.complete(
                model=model,
                messages=messages,
                max_tokens=5
            )
            
            end_time = time.time()
            response_time = end_time - start_time
            
            results[model] = {
                'success': True,
                'time': response_time,
                'response': response.choices[0].message.content
            }
            
            print(f"✅ {model}: {response_time:.2f}s - '{response.choices[0].message.content}'")
            
        except Exception as e:
            results[model] = {
                'success': False,
                'error': str(e)
            }
            print(f"❌ {model}: {e}")
    
    return results

def test_chatbot_like_query():
    """Test avec une requête similaire à ton chatbot"""
    
    print("\n=== TEST REQUÊTE CHATBOT ===")
    
    try:
        client = Mistral(api_key=MISTRAL_API_KEY)
        
        # Simuler une requête de chatbot
        messages = [
            {
                "role": "system", 
                "content": "Tu es un assistant virtuel professionnel."
            },
            {
                "role": "user", 
                "content": "Quels sont vos services pour les freelances IT?"
            }
        ]
        
        start_time = time.time()
        
        response = client.chat.complete(
            model=TEST_MODEL,
            messages=messages,
            max_tokens=200,
            temperature=0.3
        )
        
        end_time = time.time()
        response_time = end_time - start_time
        
        print(f"✅ Réponse générée en {response_time:.2f} secondes")
        print(f"Longueur: {len(response.choices[0].message.content)} caractères")
        print(f"Contenu:\n{response.choices[0].message.content}")
        
        return True, response_time
        
    except Exception as e:
        print(f"❌ ERREUR: {e}")
        traceback.print_exc()
        return False, 0

if __name__ == "__main__":
    print("🔍 DIAGNOSTIC MISTRAL API")
    print("=" * 50)
    
    # Vérifier la configuration
    if MISTRAL_API_KEY == "your_mistral_api_key_here":
        print("❌ ERREUR: Remplace MISTRAL_API_KEY par ta vraie clé!")
        print("Va sur https://console.mistral.ai/ pour obtenir une clé")
        exit(1)
    
    # Test de base
    success, response_time = test_mistral_basic()
    
    if success:
        print(f"\n🎉 MISTRAL API FONCTIONNE!")
        print(f"Temps de réponse: {response_time:.2f}s")
        
        # Tests supplémentaires
        print("\n" + "=" * 50)
        model_results = test_different_models()
        
        print("\n" + "=" * 50)
        chatbot_success, chatbot_time = test_chatbot_like_query()
        
        # Recommandations
        print("\n" + "=" * 50)
        print("🎯 RECOMMANDATIONS:")
        
        fastest_models = [
            (model, result['time']) 
            for model, result in model_results.items() 
            if result['success']
        ]
        fastest_models.sort(key=lambda x: x[1])
        
        if fastest_models:
            print(f"✅ Modèle le plus rapide: {fastest_models[0][0]} ({fastest_models[0][1]:.2f}s)")
            print(f"✅ Tu peux maintenant intégrer Mistral dans ton chatbot!")
        
    else:
        print("\n❌ MISTRAL API NE FONCTIONNE PAS")
        print("Vérifications à faire:")
        print("1. Ta clé API est-elle correcte?")
        print("2. As-tu des crédits sur ton compte Mistral?")
        print("3. Ton réseau bloque-t-il l'API?")