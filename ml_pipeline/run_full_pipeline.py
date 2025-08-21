#!/usr/bin/env python3
"""
Pipeline complet : Mise à jour données → ML → Conversion pour app
"""

import os
import sys
import subprocess
from datetime import datetime

def run_command(command, description, cwd=None):
    """Execute une commande et affiche le résultat"""
    print(f"\n🔄 {description}")
    print(f"💻 Commande: {' '.join(command)}")
    
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=600  # 10 minutes max
        )
        
        if result.returncode == 0:
            print(f"✅ {description} - SUCCÈS")
            if result.stdout:
                print(f"📤 Output: {result.stdout[-300:]}")
            return True
        else:
            print(f"❌ {description} - ÉCHEC")
            print(f"🚨 Erreur: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏰ {description} - TIMEOUT")
        return False
    except Exception as e:
        print(f"💥 {description} - EXCEPTION: {e}")
        return False

def main():
    """Pipeline complet"""
    print("🚀 PIPELINE COMPLET ML → APP")
    print(f"🕐 Début: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Étape 1: Mise à jour des données
    print("\n" + "="*60)
    print("📊 ÉTAPE 1: MISE À JOUR DES DONNÉES")
    print("="*60)
    
    step1 = run_command(
        [sys.executable, "run_all_updates.py"],
        "Mise à jour de tous les CSV",
        cwd="ml_pipeline"
    )
    
    if not step1:
        print("❌ Échec de la mise à jour des données")
        return False
    
    # Étape 2: Exécution du modèle ML
    print("\n" + "="*60)
    print("🤖 ÉTAPE 2: EXÉCUTION DU MODÈLE ML")
    print("="*60)
    
    step2 = run_command(
        [sys.executable, "bae.py"],
        "Génération des prédictions ML",
        cwd="ml_pipeline"
    )
    
    if not step2:
        print("❌ Échec du modèle ML")
        return False
    
    # Étape 3: Conversion pour l'app
    print("\n" + "="*60)
    print("🔄 ÉTAPE 3: CONVERSION POUR L'APP")
    print("="*60)
    
    step3 = run_command(
        [sys.executable, "scripts/ml_to_app_converter.py"],
        "Conversion ML → App format",
        cwd="."
    )
    
    if not step3:
        print("❌ Échec de la conversion")
        return False
    
    # Succès total
    print("\n" + "="*60)
    print("🎉 PIPELINE COMPLET - SUCCÈS!")
    print("="*60)
    print("✅ Données mises à jour")
    print("✅ Prédictions ML générées") 
    print("✅ App Flask mise à jour")
    print(f"🕐 Fin: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n💡 Votre app Flask affiche maintenant les dernières prédictions!")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)