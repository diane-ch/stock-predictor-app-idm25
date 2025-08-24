import pandas as pd
import os
from datetime import datetime
from flask import jsonify

# Configuration des chemins des fichiers CSV
CSV_BASE_PATH = "ml_pipeline/"
PREDICTED_CSV = os.path.join(CSV_BASE_PATH, "output/predictions_price_matrix.csv")
HISTORICAL_CSV = os.path.join(CSV_BASE_PATH, "data/historical_closing_prices.csv")

def load_csv_safely(file_path):
    """
    Charge un CSV de manière sécurisée avec gestion d'erreurs
    """
    try:
        if not os.path.exists(file_path):
            print(f"⚠️ CSV file not found: {file_path}")
            return None
        
        df = pd.read_csv(file_path)
        print(f"✅ CSV loaded successfully: {file_path} ({len(df)} rows)")
        return df
    
    except Exception as e:
        print(f"❌ Error loading CSV {file_path}: {str(e)}")
        return None

def validate_ticker(df, ticker):
    """
    Vérifie si le ticker existe dans les colonnes du DataFrame
    """
    if df is None:
        return False
    
    available_tickers = [col for col in df.columns if col != 'Date']
    return ticker.upper() in available_tickers

def format_date_for_display(date_str):
    """
    Formate une date pour l'affichage (ex: "2025-08-18" -> "Aug 18")
    """
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        return date_obj.strftime("%b %d")
    except:
        return date_str

def get_weekly_predictions(ticker):
    """
    Endpoint pour obtenir les prédictions des 5 derniers jours
    """
    try:
        # Charger le CSV des prédictions
        df = load_csv_safely(PREDICTED_CSV)
        
        if df is None:
            return jsonify({
                'success': False,
                'error': 'Could not load predicted prices CSV file'
            }), 500
        
        # Vérifier si le ticker existe
        ticker = ticker.upper()
        if not validate_ticker(df, ticker):
            available_tickers = [col for col in df.columns if col != 'Date'][:10]  # Premiers 10 pour l'exemple
            return jsonify({
                'success': False,
                'error': f'Ticker {ticker} not found. Available tickers include: {", ".join(available_tickers)}...'
            }), 404
        
        # Prendre les 5 dernières lignes
        last_5_rows = df.tail(5).copy()
        
        if len(last_5_rows) == 0:
            return jsonify({
                'success': False,
                'error': 'No prediction data available'
            }), 404
        
        # Extraire les dates et les prix pour le ticker demandé
        dates = last_5_rows['Date'].tolist()
        prices = last_5_rows[ticker].tolist()
        
        # Vérifier qu'on a bien des valeurs numériques
        prices = [float(price) if pd.notna(price) else 0.0 for price in prices]
        
        # Formater les dates pour l'affichage
        formatted_dates = [format_date_for_display(date) for date in dates]
        
        response_data = {
            'success': True,
            'data': {
                'ticker': ticker,
                'dates': dates,  # Dates originales pour calculs
                'formatted_dates': formatted_dates,  # Dates formatées pour affichage
                'prices': prices,
                'total_days': len(prices),
                'date_range': {
                    'start': dates[0] if dates else None,
                    'end': dates[-1] if dates else None
                }
            }
        }
        
        print(f"📈 Weekly predictions loaded for {ticker}: {len(prices)} days")
        return jsonify(response_data)
    
    except Exception as e:
        print(f"❌ Error in get_weekly_predictions: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }), 500

def get_weekly_historical(ticker):
    """
    Endpoint pour obtenir les données historiques des 5 derniers jours + le jour précédent
    On récupère 6 lignes pour pouvoir calculer le changement du premier jour
    """
    try:
        # Charger le CSV historique
        df = load_csv_safely(HISTORICAL_CSV)
        
        if df is None:
            return jsonify({
                'success': False,
                'error': 'Could not load historical prices CSV file'
            }), 500
        
        # Vérifier si le ticker existe
        ticker = ticker.upper()
        if not validate_ticker(df, ticker):
            available_tickers = [col for col in df.columns if col != 'Date'][:10]  # Premiers 10 pour l'exemple
            return jsonify({
                'success': False,
                'error': f'Ticker {ticker} not found. Available tickers include: {", ".join(available_tickers)}...'
            }), 404
        
        # Prendre les 6 dernières lignes (pour avoir le jour précédent au calcul des changements)
        last_6_rows = df.tail(6).copy()
        
        if len(last_6_rows) < 2:
            return jsonify({
                'success': False,
                'error': 'Not enough historical data available (need at least 2 days)'
            }), 404
        
        # Extraire toutes les données (6 lignes)
        all_dates = last_6_rows['Date'].tolist()
        all_prices = last_6_rows[ticker].tolist()
        
        # Vérifier qu'on a bien des valeurs numériques
        all_prices = [float(price) if pd.notna(price) else 0.0 for price in all_prices]
        
        # Séparer les 5 derniers jours (pour l'affichage) du jour précédent (pour les calculs)
        previous_day_price = all_prices[0]  # Le prix du jour précédent (J-6)
        dates = all_dates[1:]  # Les 5 derniers jours
        prices = all_prices[1:]  # Les 5 derniers prix
        
        # Formater les dates pour l'affichage
        formatted_dates = [format_date_for_display(date) for date in dates]
        
        response_data = {
            'success': True,
            'data': {
                'ticker': ticker,
                'dates': dates,  # Dates des 5 derniers jours
                'formatted_dates': formatted_dates,  # Dates formatées pour affichage
                'prices': prices,  # Prix des 5 derniers jours
                'previous_day_price': previous_day_price,  # Prix du jour précédent pour calculs
                'total_days': len(prices),
                'date_range': {
                    'start': dates[0] if dates else None,
                    'end': dates[-1] if dates else None
                }
            }
        }
        
        print(f"📊 Weekly historical data loaded for {ticker}: {len(prices)} days + 1 previous day")
        print(f"    Previous day price: ${previous_day_price:.2f}")
        print(f"    First day price: ${prices[0]:.2f}")
        return jsonify(response_data)
    
    except Exception as e:
        print(f"❌ Error in get_weekly_historical: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }), 500

def get_csv_info():
    """
    Fonction utilitaire pour obtenir des informations sur les fichiers CSV
    """
    try:
        info = {
            'predicted_csv': {
                'path': PREDICTED_CSV,
                'exists': os.path.exists(PREDICTED_CSV),
                'rows': 0,
                'tickers': []
            },
            'historical_csv': {
                'path': HISTORICAL_CSV,
                'exists': os.path.exists(HISTORICAL_CSV),
                'rows': 0,
                'tickers': []
            }
        }
        
        # Info sur le CSV des prédictions
        if info['predicted_csv']['exists']:
            df_pred = pd.read_csv(PREDICTED_CSV)
            info['predicted_csv']['rows'] = len(df_pred)
            info['predicted_csv']['tickers'] = [col for col in df_pred.columns if col != 'Date'][:10]  # Premiers 10
        
        # Info sur le CSV historique
        if info['historical_csv']['exists']:
            df_hist = pd.read_csv(HISTORICAL_CSV)
            info['historical_csv']['rows'] = len(df_hist)
            info['historical_csv']['tickers'] = [col for col in df_hist.columns if col != 'Date'][:10]  # Premiers 10
        
        return jsonify({
            'success': True,
            'info': info
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

# Test functions (optionnel, pour debug)
def test_functions():
    """
    Fonction de test pour vérifier le bon fonctionnement
    """
    print("🧪 Testing CSV functions...")
    
    # Test avec AAPL
    print("\n--- Testing weekly predictions for AAPL ---")
    result = get_weekly_predictions('AAPL')
    print(result[0].get_json() if hasattr(result[0], 'get_json') else result)
    
    print("\n--- Testing weekly historical for AAPL ---")
    result = get_weekly_historical('AAPL')
    print(result[0].get_json() if hasattr(result[0], 'get_json') else result)
    
    print("\n--- Testing CSV info ---")
    result = get_csv_info()
    print(result.get_json() if hasattr(result, 'get_json') else result)

if __name__ == "__main__":
    test_functions()