#!/usr/bin/env python3
"""
Script master pour mettre à jour tous les CSV de données
"""

import os
import sys
import subprocess
import time
from datetime import datetime

# Fix pour Windows et emojis
if sys.platform == "win32":
    try:
        os.system("chcp 65001 > nul")
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

def safe_print(message):
    """Print qui fonctionne sur Windows et Unix"""
    try:
        print(message)
    except UnicodeEncodeError:
        # Remplace les emojis par des caractères ASCII
        safe_message = (message
                       .replace("🚀", "[*]")
                       .replace("✅", "[OK]")
                       .replace("❌", "[ERROR]")
                       .replace("📊", "[DATA]")
                       .replace("🔄", "[LOADING]")
                       .replace("⚠️", "[WARNING]")
                       .replace("💾", "[SAVE]")
                       .replace("📈", "[CHART]")
                       .replace("🎯", "[TARGET]")
                       .replace("🔍", "[SEARCH]")
                       .replace("📍", "[LOCATION]")
                       .replace("🕐", "[TIME]")
                       .replace("📤", "[OUTPUT]")
                       .replace("🚨", "[ALERT]")
                       .replace("💥", "[CRASH]")
                       .replace("⏰", "[TIMEOUT]")
                       .replace("💡", "[INFO]")
                       .replace("🛑", "[STOP]")
                       .replace("🎉", "[SUCCESS]")
                       .replace("🔧", "[DEBUG]"))
        print(safe_message)

# Ajoute le dossier parent au PATH pour les imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_script(script_name, description):
    """Execute un script et gère les erreurs"""
    safe_print(f"\n{'='*60}")
    safe_print(f"🔄 {description}")
    safe_print(f"📄 Script: {script_name}")
    safe_print(f"⏰ Début: {datetime.now().strftime('%H:%M:%S')}")
    safe_print(f"{'='*60}")
    
    script_path = os.path.join('scripts', script_name)
    
    try:
        start_time = time.time()
        
        # Execute le script avec encodage forcé pour Windows
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        env['PYTHONLEGACYWINDOWSSTDIO'] = '0'
        
        # Sur Windows, force l'encodage explicitement
        if sys.platform == "win32":
            result = subprocess.run(
                [sys.executable, '-u', script_path],  # -u pour unbuffered
                cwd=os.path.dirname(os.path.abspath(__file__)),
                capture_output=True,
                text=True,
                timeout=300,
                env=env,
                encoding='utf-8',
                errors='replace'  # Remplace les caractères problématiques
            )
        else:
            result = subprocess.run(
                [sys.executable, script_path],
                cwd=os.path.dirname(os.path.abspath(__file__)),
                capture_output=True,
                text=True,
                timeout=300,
                env=env
            )
        
        execution_time = time.time() - start_time
        
        if result.returncode == 0:
            safe_print(f"✅ {description} - SUCCÈS ({execution_time:.1f}s)")
            if result.stdout:
                # Nettoie la sortie des caractères problématiques
                clean_output = result.stdout.encode('ascii', errors='ignore').decode('ascii')
                safe_print(f"📤 Output: {clean_output[-200:]}")
        else:
            safe_print(f"❌ {description} - ÉCHEC (code: {result.returncode})")
            if result.stderr:
                clean_error = result.stderr.encode('ascii', errors='ignore').decode('ascii')
                safe_print(f"🚨 Erreur: {clean_error}")
            return False
            
    except subprocess.TimeoutExpired:
        safe_print(f"⏰ {description} - TIMEOUT (>5 minutes)")
        return False
    except Exception as e:
        safe_print(f"💥 {description} - EXCEPTION: {e}")
        return False
    
    return True

def main():
    """Execute tous les scripts de mise à jour dans l'ordre"""
    
    safe_print("🚀 DÉMARRAGE DE LA MISE À JOUR DES DONNÉES ML")
    safe_print(f"📍 Dossier de travail: {os.getcwd()}")
    safe_print(f"🕐 Heure de début: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Liste des scripts à exécuter dans l'ordre
    # ADAPTEZ CETTE LISTE À VOS VRAIS NOMS DE FICHIERS
    scripts_to_run = [
        ("915spyfinal.py", "Mise à jour des prix SPY 9h15"),
        ("CLOSEREAL.py", "Mise à jour des prix de clôture"),
        # Ajoutez vos autres scripts ici avec leurs vrais noms
        # ("autre_script.py", "Description du script"),
    ]
    
    # Vérifie que le dossier scripts/ existe
    scripts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scripts')
    if not os.path.exists(scripts_dir):
        safe_print(f"❌ Dossier {scripts_dir} non trouvé")
        safe_print("💡 Créez le dossier ml_pipeline/scripts/ et placez-y vos 8 scripts")
        return False
    
    # Vérifie que les scripts existent
    missing_scripts = []
    for script_name, _ in scripts_to_run:
        script_path = os.path.join(scripts_dir, script_name)
        if not os.path.exists(script_path):
            missing_scripts.append(script_name)
    
    if missing_scripts:
        safe_print(f"⚠️  Scripts manquants: {missing_scripts}")
        safe_print("💡 Adaptez la liste 'scripts_to_run' avec vos vrais noms de fichiers")
        
        # Continue avec les scripts qui existent
        scripts_to_run = [(name, desc) for name, desc in scripts_to_run 
                         if name not in missing_scripts]
    
    # Execute tous les scripts
    successful = 0
    failed = 0
    
    for script_name, description in scripts_to_run:
        if run_script(script_name, description):
            successful += 1
        else:
            failed += 1
            safe_print(f"⚠️  Continuer malgré l'échec de {script_name}? (o/n): ")
            try:
                response = input()
                if response.lower() not in ['o', 'oui', 'y', 'yes', '']:
                    safe_print("🛑 Arrêt demandé par l'utilisateur")
                    break
            except:
                break
    
    # Résumé final
    safe_print(f"\n{'='*60}")
    safe_print("📊 RÉSUMÉ DE LA MISE À JOUR")
    safe_print(f"{'='*60}")
    safe_print(f"✅ Scripts réussis: {successful}")
    safe_print(f"❌ Scripts échoués: {failed}")
    safe_print(f"🕐 Heure de fin: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if failed == 0:
        safe_print("\n🎉 TOUTES LES DONNÉES SONT À JOUR!")
        safe_print("💡 Vous pouvez maintenant lancer le modèle ML avec:")
        safe_print("   python bae.py")
        return True
    else:
        safe_print(f"\n⚠️  {failed} script(s) ont échoué")
        safe_print("🔧 Vérifiez les erreurs ci-dessus avant de continuer")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)