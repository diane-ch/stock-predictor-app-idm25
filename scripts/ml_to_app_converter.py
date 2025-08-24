import pandas as pd
import json
import os
from datetime import datetime, timedelta
import glob

def convert_ml_predictions_to_app_format():
    """
    Convertit les prédictions ML (CSV unique cumulatif) en format JSON pour l'application Flask
    MODIFIÉ: Utilise un seul fichier CSV cumulatif au lieu de fichiers séparés par jour
    """
    try:
        # Chemins des fichiers
        ml_output_dir = 'ml_pipeline/output'
        app_data_dir = 'app/static/data'
        
        # Créer le dossier de destination s'il n'existe pas
        os.makedirs(app_data_dir, exist_ok=True)
        
        # Nom du fichier CSV cumulatif (vous pouvez ajuster ce nom)
        cumulative_csv_file = os.path.join(ml_output_dir, 'predictions_history.csv')
        
        # Vérifier si le fichier existe
        if not os.path.exists(cumulative_csv_file):
            print(f"❌ Fichier CSV cumulatif non trouvé : {cumulative_csv_file}")
            
            # Fallback: chercher s'il y a encore des fichiers individuels
            individual_files = glob.glob(os.path.join(ml_output_dir, 'predictions_newswire_*.csv'))
            if individual_files:
                print("📋 Fichiers individuels détectés, utilisation de l'ancienne méthode...")
                return convert_individual_files_to_app_format()
            else:
                print("❌ Aucun fichier de prédictions trouvé")
                return False
        
        print(f"📊 Traitement du fichier CSV cumulatif : {os.path.basename(cumulative_csv_file)}")
        
        # Charge le CSV cumulatif
        df = pd.read_csv(cumulative_csv_file)
        
        if df.empty:
            print(f"⚠️ Fichier CSV vide")
            return False
        
        # Validation des colonnes requises
        required_cols = ['date', 'ticker', 'name', 'price', 'change', 'confidence']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            print(f"❌ Colonnes manquantes : {missing_cols}")
            print(f"📋 Colonnes disponibles : {list(df.columns)}")
            return False
        
        print(f"📈 {len(df)} lignes trouvées dans le fichier")
        print(f"📅 Dates disponibles : {sorted(df['date'].unique())}")
        print(f"🏢 Tickers uniques : {len(df['ticker'].unique())}")
        
        # Convertit le DataFrame en format app
        app_data = convert_dataframe_to_app_format(df)
        
        # Sauvegarde le JSON
        output_file = os.path.join(app_data_dir, 'stocks.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(app_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n🎉 Conversion réussie ! Fichier créé : {output_file}")
        print(f"📈 {app_data['metadata']['total_predictions']} prédictions totales sur {app_data['metadata']['total_dates']} dates")
        print(f"📅 Dates disponibles : {sorted(app_data['daily_picks'].keys())}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la conversion : {e}")
        import traceback
        traceback.print_exc()
        return False

def convert_individual_files_to_app_format():
    """
    ANCIENNE MÉTHODE: Traite les fichiers individuels (fallback)
    Convertit les prédictions ML (CSV multiples) en format JSON pour l'application Flask
    """
    try:
        # Chemins des fichiers
        ml_output_dir = 'ml_pipeline/output'
        app_data_dir = 'app/static/data'
        
        # Créer le dossier de destination s'il n'existe pas
        os.makedirs(app_data_dir, exist_ok=True)
        
        # Trouve TOUS les fichiers de prédictions
        prediction_files = glob.glob(os.path.join(ml_output_dir, 'predictions_newswire_*.csv'))
        
        if not prediction_files:
            print("❌ Aucun fichier de prédictions trouvé dans ml_pipeline/output/")
            return False
        
        print(f"📊 Trouvé {len(prediction_files)} fichiers de prédictions:")
        for f in prediction_files:
            print(f"   - {os.path.basename(f)}")
        
        # Structure finale pour combiner tous les fichiers
        combined_data = {
            "daily_picks": {},
            "all_predictions": {},
            "stock_history": {},
            "metadata": {
                "last_updated": datetime.now().isoformat(),
                "total_dates": 0,
                "total_stocks": 0,
                "total_predictions": 0
            }
        }
        
        # Traite chaque fichier CSV
        for csv_file in prediction_files:
            print(f"\n📄 Traitement de {os.path.basename(csv_file)}")
            
            # Charge le CSV
            df = pd.read_csv(csv_file)
            
            if df.empty:
                print(f"⚠️ Fichier vide, ignoré")
                continue
            
            # Validation des colonnes requises
            required_cols = ['date', 'ticker', 'name', 'price', 'change', 'confidence']
            missing_cols = [col for col in required_cols if col not in df.columns]
            
            if missing_cols:
                print(f"❌ Colonnes manquantes dans {os.path.basename(csv_file)} : {missing_cols}")
                continue
            
            # Convertit ce CSV et l'ajoute aux données combinées
            file_data = convert_dataframe_to_app_format(df)
            
            # Fusionne avec les données combinées
            for date, stocks in file_data["daily_picks"].items():
                combined_data["daily_picks"][date] = stocks
                
            for date, stocks in file_data["all_predictions"].items():
                combined_data["all_predictions"][date] = stocks
                
            for ticker, history in file_data["stock_history"].items():
                if ticker not in combined_data["stock_history"]:
                    combined_data["stock_history"][ticker] = history
                else:
                    # Combine l'historique en évitant les doublons
                    existing_dates = {h["date"] for h in combined_data["stock_history"][ticker]}
                    for entry in history:
                        if entry["date"] not in existing_dates:
                            combined_data["stock_history"][ticker].append(entry)
            
            print(f"✅ {os.path.basename(csv_file)} traité avec succès")
        
        # Met à jour les métadonnées finales
        combined_data["metadata"]["total_dates"] = len(combined_data["daily_picks"])
        combined_data["metadata"]["total_stocks"] = sum(len(stocks) for stocks in combined_data["daily_picks"].values())
        combined_data["metadata"]["total_predictions"] = sum(len(stocks) for stocks in combined_data["all_predictions"].values())
        
        # Sauvegarde le JSON combiné
        output_file = os.path.join(app_data_dir, 'stocks.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(combined_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n🎉 Conversion réussie ! Fichier créé : {output_file}")
        print(f"📈 {combined_data['metadata']['total_predictions']} prédictions totales sur {combined_data['metadata']['total_dates']} dates")
        print(f"📅 Dates disponibles : {sorted(combined_data['daily_picks'].keys())}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la conversion : {e}")
        import traceback
        traceback.print_exc()
        return False

def convert_dataframe_to_app_format(df):
    """
    Convertit le DataFrame pandas en structure JSON pour l'app
    """
    
    # Charge les logos depuis stocks_list.json
    def load_stock_logos():
        """Charge les logos depuis content/stocks_list.json"""
        try:
            with open('content/stocks_list.json', 'r', encoding='utf-8') as f:
                stocks_list = json.load(f)
            
            # Crée un mapping ticker -> logo_url
            logo_mapping = {}
            for stock in stocks_list:
                ticker = stock.get('ticker', '').upper()
                logo_url = stock.get('logo_url', '')
                if ticker and logo_url:
                    logo_mapping[ticker] = logo_url
            
            return logo_mapping
            
        except FileNotFoundError:
            print("⚠️ Fichier content/stocks_list.json non trouvé, utilisation du fallback")
            return {}
        except Exception as e:
            print(f"⚠️ Erreur lors du chargement des logos : {e}")
            return {}
    
    # Charge les logos une seule fois
    logo_mapping = load_stock_logos()
    
    def get_logo_url(ticker):
        """Retourne l'URL du logo pour un ticker donné"""
        ticker = str(ticker).upper()
        return logo_mapping.get(ticker, '/static/images/logos/default.png')
    
    # Mapping des niveaux de confiance
    def get_confidence_level(score):
        """Convertit le score numérique en niveau textuel"""
        if pd.isna(score):
            return "medium"
        
        score = float(score)
        if score >= 8:
            return "high"
        elif score >= 6:
            return "medium"
        else:
            return "low"
    
    # Structure finale avec ALL_PREDICTIONS
    app_data = {
        "daily_picks": {},      # TOP 5 pour la page Discovery
        "all_predictions": {},  # TOUS les stocks pour AI Predictions  
        "stock_history": {},
        "metadata": {
            "last_updated": datetime.now().isoformat(),
            "total_dates": 0,
            "total_stocks": 0
        }
    }
    
    # Groupe par date
    for date, group in df.groupby('date'):
        date_str = str(date)
        
        # === 1. TOP 5 pour Discovery (trié par confiance) ===
        group_top5 = group.sort_values('confidence', ascending=False).head(5)
        
        daily_stocks = []
        for _, row in group_top5.iterrows():
            features = []
            for col in df.columns:
                if col.startswith('feature') and pd.notna(row[col]):
                    features.append(str(row[col]))
            
            stock_data = {
                "ticker": str(row['ticker']).upper(),
                "name": str(row['name']),
                "logo_path": get_logo_url(str(row['ticker']).upper()),
                "logo_url": get_logo_url(str(row['ticker']).upper()),
                "price": round(float(row['price']), 2),
                "change": round(float(row['change']), 1),
                "confidence": get_confidence_level(row['confidence']),
                "confidence_score": int(row['confidence']) if pd.notna(row['confidence']) else 5,
                "features": features,
                "prediction_date": date_str
            }
            daily_stocks.append(stock_data)
        
        app_data["daily_picks"][date_str] = daily_stocks
        
        # === 2. TOUS les stocks pour AI Predictions ===
        all_stocks = []
        for _, row in group.iterrows():
            features = []
            for col in df.columns:
                if col.startswith('feature') and pd.notna(row[col]):
                    features.append(str(row[col]))
            
            stock_data = {
                "ticker": str(row['ticker']).upper(),
                "name": str(row['name']),
                "logo_path": get_logo_url(str(row['ticker']).upper()),
                "logo_url": get_logo_url(str(row['ticker']).upper()),
                "price": round(float(row['price']), 2),
                "change": round(float(row['change']), 1),
                "confidence": get_confidence_level(row['confidence']),
                "confidence_score": int(row['confidence']) if pd.notna(row['confidence']) else 5,
                "features": features,
                "prediction_date": date_str
            }
            all_stocks.append(stock_data)
        
        app_data["all_predictions"][date_str] = all_stocks
    
    # Crée l'historique des stocks
    create_stock_history(df, app_data)
    
    # Met à jour les métadonnées
    app_data["metadata"]["total_dates"] = len(app_data["daily_picks"])
    app_data["metadata"]["total_stocks"] = sum(len(stocks) for stocks in app_data["daily_picks"].values())
    app_data["metadata"]["total_predictions"] = sum(len(stocks) for stocks in app_data["all_predictions"].values())
    
    return app_data

def create_stock_history(df, app_data):
    """
    Crée l'historique des stocks pour les pages de détail
    """
    
    for ticker, group in df.groupby('ticker'):
        ticker = str(ticker).upper()
        
        # Trie par date (plus récent en premier)
        history_data = []
        
        for _, row in group.sort_values('date', ascending=False).iterrows():
            history_entry = {
                "date": str(row['date']),
                "price": round(float(row['price']), 2),
                "change": round(float(row['change']), 1),
                "confidence_score": int(row['confidence']) if pd.notna(row['confidence']) else 5,
                "predicted": True  # Marque comme prédiction
            }
            history_data.append(history_entry)
        
        app_data["stock_history"][ticker] = history_data

def merge_individual_csvs_to_cumulative():
    """
    UTILITAIRE: Fusionne les fichiers CSV individuels existants en un seul fichier cumulatif
    Utile pour la migration depuis l'ancienne approche
    """
    try:
        ml_output_dir = 'ml_pipeline/output'
        
        # Trouve tous les fichiers individuels
        individual_files = glob.glob(os.path.join(ml_output_dir, 'predictions_newswire_*.csv'))
        
        if not individual_files:
            print("❌ Aucun fichier individuel trouvé pour la fusion")
            return False
        
        print(f"📋 Fusion de {len(individual_files)} fichiers individuels...")
        
        # DataFrame cumulatif
        all_data = []
        
        for csv_file in sorted(individual_files):  # Trie pour ordre chronologique
            print(f"📄 Lecture de {os.path.basename(csv_file)}")
            df = pd.read_csv(csv_file)
            if not df.empty:
                all_data.append(df)
        
        if not all_data:
            print("❌ Aucune donnée trouvée dans les fichiers")
            return False
        
        # Concatène tous les DataFrames
        cumulative_df = pd.concat(all_data, ignore_index=True)
        
        # Supprime les doublons potentiels (même date + ticker)
        cumulative_df = cumulative_df.drop_duplicates(subset=['date', 'ticker'], keep='last')
        
        # Trie par date puis ticker
        cumulative_df = cumulative_df.sort_values(['date', 'ticker'])
        
        # Sauvegarde le fichier cumulatif
        cumulative_file = os.path.join(ml_output_dir, 'predictions_history.csv')
        cumulative_df.to_csv(cumulative_file, index=False)
        
        print(f"✅ Fichier cumulatif créé : {cumulative_file}")
        print(f"📊 {len(cumulative_df)} lignes totales")
        print(f"📅 Dates : {sorted(cumulative_df['date'].unique())}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la fusion : {e}")
        import traceback
        traceback.print_exc()
        return False

def setup_ml_pipeline():
    """
    Crée la structure de dossiers nécessaire
    """
    directories = [
        'ml_pipeline/data',
        'ml_pipeline/output', 
        'app/static/data',
        'scripts'
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"📁 Dossier créé/vérifié : {directory}")

def create_sample_data():
    """
    Crée des données d'exemple pour le développement
    """
    sample_data = {
        "daily_picks": {
            "2025-08-21": [
                {
                    "ticker": "AAPL",
                    "name": "Apple Inc.",
                    "logo_path": "https://logo.clearbit.com/aapl.com",
                    "logo_url": "https://logo.clearbit.com/aapl.com",
                    "price": 152.45,
                    "change": 1.5,
                    "confidence": "high",
                    "confidence_score": 8,
                    "features": ["Strong iPhone 16 pre-orders", "Services revenue accelerating", "AI integration progress", "Solid cash position"],
                    "prediction_date": "2025-08-21"
                }
            ]
        },
        "all_predictions": {
            "2025-08-21": [
                {
                    "ticker": "AAPL",
                    "name": "Apple Inc.",
                    "logo_path": "https://logo.clearbit.com/aapl.com",
                    "logo_url": "https://logo.clearbit.com/aapl.com",
                    "price": 152.45,
                    "change": 1.5,
                    "confidence": "high",
                    "confidence_score": 8,
                    "features": ["Strong iPhone 16 pre-orders", "Services revenue accelerating", "AI integration progress", "Solid cash position"],
                    "prediction_date": "2025-08-21"
                }
            ]
        },
        "stock_history": {
            "AAPL": [
                {"date": "2025-08-21", "price": 152.45, "change": 1.5, "confidence_score": 8, "predicted": True}
            ]
        },
        "metadata": {
            "last_updated": datetime.now().isoformat(),
            "total_dates": 1,
            "total_stocks": 1,
            "total_predictions": 1
        }
    }
    
    os.makedirs('app/static/data', exist_ok=True)
    with open('app/static/data/stocks.json', 'w') as f:
        json.dump(sample_data, f, indent=2)
    
    print("✅ Données d'exemple créées dans app/static/data/stocks.json")

if __name__ == "__main__":
    print("📄 Démarrage de la conversion ML → App...")
    
    # Option 1: Fusionner les fichiers individuels existants (si nécessaire)
    # Décommentez cette ligne pour faire la migration une seule fois
    # merge_individual_csvs_to_cumulative()
    
    # Option 2: Conversion normale (fichier cumulatif ou fallback individuel)
    success = convert_ml_predictions_to_app_format()
    
    if not success:
        print("⚠️ Conversion ML échouée, création de données d'exemple...")
        create_sample_data()
    
    print("🎉 Conversion terminée !")