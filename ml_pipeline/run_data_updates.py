#!/usr/bin/env python3
"""
Runner personnalisé pour vos 8 scripts de données ML
Respecte l'ordre optimal et gère les dépendances
"""

import os
import sys
import subprocess
import time
from datetime import datetime

# Fix UTF-8 pour Windows
if sys.platform == "win32":
    try:
        os.system("chcp 65001 > nul")
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

def safe_print(message):
    """Print compatible Windows/Unix"""
    try:
        print(message)
    except UnicodeEncodeError:
        clean_msg = (message
                    .replace("🚀", "[START]")
                    .replace("✅", "[OK]")
                    .replace("❌", "[ERROR]")
                    .replace("📊", "[DATA]")
                    .replace("🔄", "[RUNNING]")
                    .replace("⚠️", "[WARN]")
                    .replace("🎉", "[SUCCESS]")
                    .replace("💾", "[SAVE]")
                    .replace("📈", "[CHART]")
                    .replace("🕐", "[TIME]")
                    .replace("📍", "[LOC]")
                    .replace("⏰", "[TIMEOUT]")
                    .replace("💥", "[CRASH]"))
        print(clean_msg)

def run_script(script_name, description, timeout_minutes=10):
    """Execute un script avec gestion d'erreurs adaptée"""
    
    safe_print(f"\n{'='*70}")
    safe_print(f"🔄 {description}")
    safe_print(f"📄 Script: {script_name}")
    safe_print(f"⏰ Début: {datetime.now().strftime('%H:%M:%S')}")
    safe_print(f"⏳ Timeout: {timeout_minutes} minutes")
    safe_print(f"{'='*70}")
    
    script_path = os.path.join('scripts', script_name)
    
    if not os.path.exists(script_path):
        safe_print(f"❌ Script non trouvé: {script_path}")
        return False
    
    # Définit le répertoire de travail pour le script
    # Les scripts doivent s'exécuter depuis ml_pipeline/data pour trouver les CSV
    script_working_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
    
    # Crée le dossier data s'il n'existe pas
    os.makedirs(script_working_dir, exist_ok=True)
    
    safe_print(f"📍 Répertoire de travail: {script_working_dir}")
    safe_print(f"📄 Script complet: {os.path.abspath(script_path)}")
    
    try:
        start_time = time.time()
        
        # Configuration environnement pour Windows
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        env['PYTHONLEGACYWINDOWSSTDIO'] = '0'
        
        # Lance le script depuis le dossier data
        process = subprocess.Popen(
            [sys.executable, '-u', os.path.abspath(script_path)],
            cwd=script_working_dir,  # 🎯 CHANGEMENT ICI: exécute depuis /data
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace',
            env=env,
            bufsize=1,
            universal_newlines=True
        )
        
        # Affiche l'output en temps réel
        output_lines = []
        while True:
            line = process.stdout.readline()
            if line:
                # Nettoie la ligne des caractères problématiques
                clean_line = line.strip()
                try:
                    print(f"   📤 {clean_line}")
                except:
                    clean_line = clean_line.encode('ascii', errors='ignore').decode('ascii')
                    print(f"   📤 {clean_line}")
                output_lines.append(clean_line)
            
            if process.poll() is not None:
                break
                
            # Check timeout
            if time.time() - start_time > timeout_minutes * 60:
                process.terminate()
                safe_print(f"⏰ TIMEOUT après {timeout_minutes} minutes")
                return False
        
        execution_time = time.time() - start_time
        return_code = process.returncode
        
        if return_code == 0:
            safe_print(f"✅ {description} - SUCCÈS ({execution_time:.1f}s)")
            
            # Affiche les dernières lignes importantes
            important_lines = [line for line in output_lines[-10:] 
                             if any(keyword in line.lower() 
                                   for keyword in ['success', 'complete', 'saved', 'ready', 'records'])]
            
            if important_lines:
                safe_print("📋 Résumé:")
                for line in important_lines[-3:]:  # Dernières 3 lignes importantes
                    safe_print(f"   💡 {line}")
            
            return True
        else:
            safe_print(f"❌ {description} - ÉCHEC (code: {return_code})")
            
            # Affiche les dernières lignes d'erreur
            error_lines = [line for line in output_lines[-10:] 
                          if any(keyword in line.lower() 
                                for keyword in ['error', 'failed', 'exception', 'traceback'])]
            
            if error_lines:
                safe_print("🚨 Erreurs détectées:")
                for line in error_lines[-3:]:
                    safe_print(f"   ❌ {line}")
            
            return False
            
    except Exception as e:
        safe_print(f"💥 Exception lors de l'exécution: {e}")
        return False

def main():
    """Execute tous vos scripts dans l'ordre optimal"""
    
    safe_print("🚀 MISE À JOUR COMPLÈTE DES DONNÉES ML")
    safe_print(f"📍 Dossier: {os.getcwd()}")
    safe_print(f"🕐 Début: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # ORDRE OPTIMAL basé sur vos scripts:
    # 1. Sources de base (prix, VIX)
    # 2. Calculs dérivés (GARCH, TA)
    # 3. Agrégations finales
    scripts_to_run = [
        # Phase 1: Données de base
        ("CLOSEREAL.py", "Reconstruction complète prix historiques", 15),
        ("VIXYFINANCE.py", "Mise à jour données VIX", 10),
        ("915spyfinal.py", "Prix SPY pré-marché 9h15", 10),
        ("SPY4PM.py", "Prix SPY 16h00", 10),
        
        # Phase 2: Données intraday
        ("openpy.py", "Prix d'ouverture", 10),
        ("polygon1030.py", "Prix 10h30 Polygon", 15),
        
        # Phase 3: Calculs techniques
        ("garch.py", "Modèles GARCH volatilité", 20),
        ("TA.py", "Analyse technique et features", 15),
    ]
    
    safe_print(f"📋 {len(scripts_to_run)} scripts à exécuter")
    safe_print("📊 Ordre d'exécution:")
    for i, (script, desc, timeout) in enumerate(scripts_to_run, 1):
        safe_print(f"   {i}. {script} - {desc} ({timeout}min)")
    
    # Vérifie l'existence des scripts
    scripts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scripts')
    missing_scripts = []
    
    for script_name, _, _ in scripts_to_run:
        script_path = os.path.join(scripts_dir, script_name)
        if not os.path.exists(script_path):
            missing_scripts.append(script_name)
    
    if missing_scripts:
        safe_print(f"⚠️  Scripts manquants: {missing_scripts}")
        safe_print("💡 Vérifiez que tous les scripts sont dans ml_pipeline/scripts/")
        
        # Continue avec les scripts disponibles
        scripts_to_run = [(name, desc, timeout) for name, desc, timeout in scripts_to_run 
                         if name not in missing_scripts]
        safe_print(f"▶️  Continuer avec {len(scripts_to_run)} scripts disponibles")
    
    # Exécution
    successful = 0
    failed = 0
    total_start_time = time.time()
    
    for i, (script_name, description, timeout) in enumerate(scripts_to_run, 1):
        safe_print(f"\n🎯 PHASE {i}/{len(scripts_to_run)}")
        
        if run_script(script_name, description, timeout):
            successful += 1
            safe_print(f"✅ Phase {i} terminée avec succès")
        else:
            failed += 1
            safe_print(f"❌ Phase {i} échouée")
            
            # Demande confirmation pour continuer
            safe_print(f"⚠️  Continuer malgré l'échec de {script_name}?")
            safe_print("   [o] Oui, continuer")
            safe_print("   [n] Non, arrêter")
            safe_print("   [s] Skip ce script seulement")
            
            try:
                choice = input("Votre choix (o/n/s): ").lower().strip()
                if choice in ['n', 'no', 'non']:
                    safe_print("🛑 Arrêt demandé par l'utilisateur")
                    break
                elif choice in ['s', 'skip']:
                    safe_print(f"⏭️  Script {script_name} ignoré")
                    continue
                # Sinon continue (choix 'o' ou autre)
            except KeyboardInterrupt:
                safe_print("\n🛑 Interruption clavier - Arrêt")
                break
    
    # Résumé final
    total_time = time.time() - total_start_time
    
    safe_print(f"\n{'='*70}")
    safe_print("📊 RÉSUMÉ FINAL")
    safe_print(f"{'='*70}")
    safe_print(f"✅ Scripts réussis: {successful}")
    safe_print(f"❌ Scripts échoués: {failed}")
    safe_print(f"🕐 Temps total: {total_time/60:.1f} minutes")
    safe_print(f"🕐 Fin: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if failed == 0:
        safe_print("\n🎉 TOUTES LES DONNÉES SONT À JOUR!")
        safe_print("✅ Prêt pour l'exécution du modèle ML")
        safe_print("💡 Prochaine étape: python bae.py")
        
        # Vérifie les fichiers générés
        data_dir = "data"
        if os.path.exists(data_dir):
            csv_files = [f for f in os.listdir(data_dir) if f.endswith('.csv')]
            safe_print(f"📁 {len(csv_files)} fichiers CSV générés dans /data")
            
        return True
    else:
        safe_print(f"\n⚠️  {failed} script(s) ont échoué")
        safe_print("🔧 Vérifiez les erreurs ci-dessus")
        safe_print("💡 Vous pouvez relancer uniquement les scripts échoués")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        safe_print("\n\n🛑 Arrêt par l'utilisateur")
        sys.exit(130)