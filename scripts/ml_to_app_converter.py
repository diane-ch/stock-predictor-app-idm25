import pandas as pd
import json
import os
from datetime import datetime, timedelta
import glob

def convert_ml_predictions_to_app_format():
    """
    Convertit les prédictions ML (CSV) en format JSON pour l'application Flask
    """
    try:
        # Chemins des fichiers
        ml_output_dir = 'ml_pipeline/output'
        app_data_dir = 'app/static/data'
        
        # Créer le dossier de destination s'il n'existe pas
        os.makedirs(app_data_dir, exist_ok=True)
        
        # Trouve le fichier de prédictions le plus récent
        prediction_files = glob.glob(os.path.join(ml_output_dir, 'predictions_newswire_*.csv'))
        
        if not prediction_files:
            print("❌ Aucun fichier de prédictions trouvé dans ml_pipeline/output/")
            return False
        
        # Prend le plus récent
        latest_file = max(prediction_files, key=os.path.getctime)
        print(f"📊 Conversion du fichier : {latest_file}")
        
        # Charge les prédictions ML
        df = pd.read_csv(latest_file)
        
        # Validation des colonnes requises
        required_cols = ['date', 'ticker', 'name', 'price', 'change', 'confidence']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            print(f"❌ Colonnes manquantes dans le CSV : {missing_cols}")
            return False
        
        # Convertit en format app
        app_data = convert_dataframe_to_app_format(df)
        
        # Sauvegarde le JSON
        output_file = os.path.join(app_data_dir, 'stocks.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(app_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Conversion réussie ! Fichier créé : {output_file}")
        print(f"📈 {app_data['metadata']['total_stocks']} stocks sur {app_data['metadata']['total_dates']} dates")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la conversion : {e}")
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
            
            print(f"📸 {len(logo_mapping)} logos chargés depuis stocks_list.json")
            return logo_mapping
            
        except FileNotFoundError:
            print("⚠️  Fichier content/stocks_list.json non trouvé, utilisation du fallback")
            return {}
        except Exception as e:
            print(f"⚠️  Erreur lors du chargement des logos : {e}")
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
    
    print("🔄 CONVERTISSEUR - Début de conversion...")
    
    # Groupe par date
    for date, group in df.groupby('date'):
        date_str = str(date)
        print(f"📅 Traitement de la date {date_str} avec {len(group)} stocks")
        
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
        print(f"   ✅ {len(daily_stocks)} pour daily_picks, {len(all_stocks)} pour all_predictions")
    
    # Crée l'historique des stocks
    create_stock_history(df, app_data)
    
    # Met à jour les métadonnées
    app_data["metadata"]["total_dates"] = len(app_data["daily_picks"])
    app_data["metadata"]["total_stocks"] = sum(len(stocks) for stocks in app_data["daily_picks"].values())
    app_data["metadata"]["total_predictions"] = sum(len(stocks) for stocks in app_data["all_predictions"].values())
    
    print(f"🎉 CONVERSION TERMINÉE:")
    print(f"   📊 {app_data['metadata']['total_predictions']} prédictions totales")
    print(f"   📈 {app_data['metadata']['total_stocks']} dans daily_picks")
    
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
                },
                {
                    "ticker": "MSFT",
                    "name": "Microsoft Corporation",
                    "logo_path": "https://logo.clearbit.com/microsoft.com",
                    "logo_url": "https://logo.clearbit.com/microsoft.com",
                    "price": 287.12,
                    "change": 2.1,
                    "confidence": "high",
                    "confidence_score": 9,
                    "features": ["Azure growth momentum", "AI integration across products", "Strong enterprise demand", "Cloud market expansion"],
                    "prediction_date": "2025-08-21"
                },
                {
                    "ticker": "TSLA",
                    "name": "Tesla Inc.",
                    "logo_path": "https://logo.clearbit.com/tesla.com",
                    "logo_url": "https://logo.clearbit.com/tesla.com",
                    "price": 198.67,
                    "change": -0.8,
                    "confidence": "medium",
                    "confidence_score": 6,
                    "features": ["EV market competition", "Autopilot improvements", "Energy business growth", "Production efficiency gains"],
                    "prediction_date": "2025-08-21"
                }
            ]
        },
        "stock_history": {
            "AAPL": [
                {"date": "2025-08-21", "price": 152.45, "change": 1.5, "confidence_score": 8, "predicted": True},
                {"date": "2025-08-20", "price": 150.20, "change": 0.8, "confidence_score": 7, "predicted": True}
            ]
        },
        "metadata": {
            "last_updated": datetime.now().isoformat(),
            "total_dates": 1,
            "total_stocks": 3
        }
    }
    
    os.makedirs('app/static/data', exist_ok=True)
    with open('app/static/data/stocks.json', 'w') as f:
        json.dump(sample_data, f, indent=2)
    
    print("✅ Données d'exemple créées dans app/static/data/stocks.json")

if __name__ == "__main__":
    print("🔄 Démarrage de la conversion ML → App...")
    
    # Essaie la conversion depuis ML
    success = convert_ml_predictions_to_app_format()
    
    if not success:
        print("⚠️  Conversion ML échouée, création de données d'exemple...")
        create_sample_data()
    
    print("🎉 Conversion terminée !")