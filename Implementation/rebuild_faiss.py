#!/usr/bin/env python3
"""
Script pour reconstruire l'index FAISS avec votre knowledge_base.json existant
"""

import os
import json
import numpy as np
import faiss
import pickle
from sentence_transformers import SentenceTransformer
from pathlib import Path

def load_existing_knowledge_base():
    """
    Charge votre fichier knowledge_base.json existant
    """
    kb_path = 'data/knowledge_base.json'
    
    if not os.path.exists(kb_path):
        print(f" Fichier {kb_path} non trouvé!")
        print(" Assurez-vous que le fichier existe dans le dossier 'data/'")
        return None
    
    try:
        with open(kb_path, 'r', encoding='utf-8') as f:
            knowledge_base = json.load(f)
        
        print(f" Fichier {kb_path} chargé avec succès")
        
        # Vérifier la structure
        if 'knowledge_base' in knowledge_base and 'chunks' in knowledge_base['knowledge_base']:
            chunks = knowledge_base['knowledge_base']['chunks']
            print(f" {len(chunks)} chunks trouvés dans votre base de connaissances")
            
            # Afficher quelques exemples
            print(" Premiers chunks:")
            for i, chunk in enumerate(chunks[:3]):
                print(f"   {i+1}. {chunk.get('id', 'NO_ID')} - {chunk.get('title', 'NO_TITLE')[:50]}...")
            
            return knowledge_base
        else:
            print(" Structure du fichier JSON incorrecte")
            print(" Le fichier doit contenir: {'knowledge_base': {'chunks': [...]}}")
            return None
            
    except json.JSONDecodeError as e:
        print(f" Erreur de format JSON: {e}")
        return None
    except Exception as e:
        print(f" Erreur lors du chargement: {e}")
        return None

def rebuild_faiss_index(knowledge_base):
    """
    Reconstruit l'index FAISS à partir de votre base existante
    """
    print("\n Reconstruction de l'index FAISS...")
    
    chunks = knowledge_base['knowledge_base']['chunks']
    
    # 1. Charger le modèle d'embedding
    print(" Chargement du modèle d'embedding...")
    try:
        # Utilisation d'un modèle plus fiable
        model = SentenceTransformer('all-MiniLM-L6-v2')
        print("    Modèle chargé")
    except Exception as e:
        print(f"    Erreur chargement modèle: {e}")
        print(" Essayez: pip install sentence-transformers")
        return False
    
    # 2. Préparer les textes pour l'embedding
    print(" Préparation des textes...")
    texts_for_embedding = []
    chunk_metadata = []
    
    for i, chunk in enumerate(chunks):
        try:
            # Créer le texte pour embedding
            title = chunk.get('title', f'Chunk {i}')
            content = chunk.get('content', '')
            
            if not content:
                print(f" Chunk {chunk.get('id', i)} sans contenu, ignoré")
                continue
            
            full_text = f"{title}: {content}"
            texts_for_embedding.append(full_text)
            
            # Préparer les métadonnées
            metadata = {
                'id': chunk.get('id', f'chunk_{i}'),
                'title': title,
                'content': content,
                'keywords': chunk.get('keywords', []),
                'category': chunk.get('category', 'general'),
                'intent': chunk.get('intent', ['general'])
            }
            chunk_metadata.append(metadata)
            
        except Exception as e:
            print(f"  Erreur chunk {i}: {e}")
            continue
    
    print(f"   {len(texts_for_embedding)} textes préparés")
    
    if len(texts_for_embedding) == 0:
        print(" Aucun texte valide trouvé!")
        return False
    
    # 3. Créer les embeddings
    print(" Création des embeddings...")
    try:
        embeddings = model.encode(texts_for_embedding, show_progress_bar=True)
        print(f"    Embeddings créés: {embeddings.shape}")
    except Exception as e:
        print(f"    Erreur création embeddings: {e}")
        return False
    
    # 4. Créer l'index FAISS
    print("🗃️ Création de l'index FAISS...")
    try:
        dimension = embeddings.shape[1]
        print(f"   Dimension des vecteurs: {dimension}")
        
        # Créer l'index FAISS
        index = faiss.IndexFlatIP(dimension)
        
        # Normaliser les embeddings pour la similarité cosinus
        embeddings_normalized = embeddings.copy().astype('float32')
        faiss.normalize_L2(embeddings_normalized)
        
        # Ajouter les vecteurs à l'index
        index.add(embeddings_normalized)
        
        print(f"   Index créé avec {index.ntotal} vecteurs")
        
    except Exception as e:
        print(f"    Erreur création index FAISS: {e}")
        return False
    
    # 5. Sauvegarder les fichiers
    print(" Sauvegarde...")
    try:
        # Créer le dossier data s'il n'existe pas
        os.makedirs('data', exist_ok=True)
        
        # Supprimer les anciens fichiers corrompus
        old_files = [
            'data/optim_finance_index.faiss',
            'data/optim_finance_chunks.pkl'
        ]
        
        for old_file in old_files:
            if os.path.exists(old_file):
                os.remove(old_file)
                print(f"    Ancien fichier supprimé: {old_file}")
        
        # Sauvegarder le nouvel index FAISS
        faiss.write_index(index, 'data/optim_finance_index.faiss')
        print("   Index FAISS sauvegardé")
        
        # Sauvegarder les métadonnées
        with open('data/optim_finance_chunks.pkl', 'wb') as f:
            pickle.dump(chunk_metadata, f)
        print("    Métadonnées sauvegardées")
        
        # Test de lecture pour vérifier l'intégrité
        test_index = faiss.read_index('data/optim_finance_index.faiss')
        print(f"   Test de lecture réussi: {test_index.ntotal} vecteurs")
        
        return True
        
    except Exception as e:
        print(f"   Erreur sauvegarde: {e}")
        return False

def test_rebuilt_index():
    """
    Test rapide du nouvel index
    """
    print("\n Test de l'index reconstruit...")
    
    try:
        # Charger l'index
        index = faiss.read_index('data/optim_finance_index.faiss')
        
        # Charger les métadonnées
        with open('data/optim_finance_chunks.pkl', 'rb') as f:
            chunks = pickle.load(f)
        
        # Charger le modèle
        model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Tests avec différentes requêtes
        test_queries = [
            "Combien coûte le portage salarial ?",
            "Contact OPTIM Finance",
            "Différence auto-entreprise et société"
        ]
        
        for query in test_queries:
            print(f"\n Test: '{query}'")
            
            # Encoder la requête
            query_embedding = model.encode([query]).astype('float32')
            faiss.normalize_L2(query_embedding)
            
            # Recherche
            scores, indices = index.search(query_embedding, 2)
            
            # Afficher les résultats
            for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                if idx != -1:  # -1 signifie pas de résultat
                    chunk = chunks[idx]
                    print(f"   {i+1}. [{score:.3f}] {chunk['title']}")
                    print(f"      Catégorie: {chunk['category']}")
        
        print("\n Tous les tests réussis!")
        return True
        
    except Exception as e:
        print(f" Erreur lors du test: {e}")
        return False

def main():
    """
    Fonction principale
    """
    print(" Reconstruction de l'index FAISS avec votre knowledge_base.json\n")
    
    # 1. Charger votre base de connaissances existante
    knowledge_base = load_existing_knowledge_base()
    if not knowledge_base:
        return
    
    # 2. Reconstruire l'index FAISS
    if rebuild_faiss_index(knowledge_base):
        print("\n Index FAISS reconstruit avec succès!")
        
        # 3. Tester le nouvel index
        if test_rebuilt_index():
            print("\n Reconstruction terminée avec succès!")
            print("\n Fichiers mis à jour:")
            print("   - data/optim_finance_index.faiss (nouvel index)")
            print("   - data/optim_finance_chunks.pkl (métadonnées)")
            print("   - data/knowledge_base.json (votre fichier inchangé)")
            print("\n  Vous pouvez maintenant relancer votre chatbot!")
            print("   python3 -m src.chatbot")
        else:
            print("\n  Index créé mais problème lors du test")
    else:
        print("\n Échec de la reconstruction")

if __name__ == "__main__":
    main()