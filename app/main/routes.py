import json
import os
import subprocess
from flask import Blueprint, current_app, render_template, redirect, url_for, jsonify, request
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from app.services.stock_service import stock_service
from scripts.csv_functions_aipredictions import get_weekly_predictions, get_weekly_historical

# Create the main blueprint
main_bp = Blueprint('main', __name__, template_folder='../templates')

@main_bp.route('/')
def index():
    """Root route - redirect based on authentication status"""
    if current_user.is_authenticated:
        return redirect(url_for('main.discover'))
    else:
        return redirect(url_for('auth.login'))
    
def load_stock_data():
    """Charge les données depuis le JSON généré"""
    try:
        with open('app/static/data/stocks.json', 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        print("❌ Fichier stocks.json non trouvé")
        # Données de fallback pour développement
        return {
            "daily_picks": {},
            "stock_history": {},
            "metadata": {"total_dates": 0, "total_stocks": 0}
        }
    


def get_available_dates():
    """Retourne les dates disponibles triées (plus récent en premier)"""
    data = load_stock_data()
    available_dates = list(data['daily_picks'].keys())
    return sorted(available_dates, reverse=True)  # Plus récent en premier

def get_today_date():
    """Retourne la date d'aujourd'hui ou la plus récente disponible"""
    available_dates = get_available_dates()
    today = datetime.now().strftime('%Y-%m-%d')
    
    if today in available_dates:
        return today
    elif available_dates:
        return available_dates[0]  # Date la plus récente
    else:
        return today
    
def get_latest_available_date():
    """Retourne la date la plus récente dans les données (pas forcément aujourd'hui)"""
    available_dates = get_available_dates()
    if available_dates:
        latest_date = available_dates[0]  # Premier = plus récent
        print(f"📅 Date la plus récente dans les données : {latest_date}")
        return latest_date
    else:
        # Fallback si aucune donnée
        fallback_date = datetime.now().strftime('%Y-%m-%d')
        print(f"⚠️  Aucune donnée disponible, fallback sur : {fallback_date}")
        return fallback_date

### DISCOVER ROUTES
@main_bp.route('/discover')
@login_required
def discover():
    """Main screen - Smart Picks"""
    try:
        today = get_today_date()
        data = load_stock_data()

        # Fetch today's stocks for first display
        initial_stocks = data['daily_picks'].get(today, [])

        return render_template('discover.html', initial_stocks=initial_stocks, current_date=today)
    
    except Exception as e:
        print(f"Error in discovery: {e}")
        return render_template('discover.html', initial_stocks=[], current_date=get_today_date())
    
@main_bp.route('/stock-detail/<ticker>')
@login_required
def stock_detail(ticker):
    """Detail page for one specific stock"""
    return render_template('stock_detail.html', ticker=ticker.upper())

# ================
# API ENDPOINTS
# ===============

# Load the stock names lookup once when the module loads
def load_stock_info_lookup():
    """Load stock ticker -> {name, logo_url} mapping from JSON file"""
    try:
        # Path to your JSON file relative to the app root
        json_path = os.path.join('content', 'stocks_list.json')
        
        with open(json_path, 'r') as f:
            stock_list = json.load(f)
        
        # Convert list to dictionary for O(1) lookup - include both name and logo
        lookup = {
            stock['ticker']: {
                'name': stock['name'],
                'logo_url': stock['logo_url']
            } for stock in stock_list
        }
        print(f"Loaded {len(lookup)} stock info entries from {json_path}")
        return lookup
    
    except Exception as e:
        print(f"Warning: Could not load stock info JSON: {e}")
        return {}

# Load once when module imports
STOCK_INFO_LOOKUP = load_stock_info_lookup()

@main_bp.route('/api/stocks')
@login_required
def api_get_stocks():
    """API : Fetches stocks for a given date"""
    # Récupère la date depuis les paramètres URL (?date=2025-08-20)
    requested_date = request.args.get('date')
    
    if not requested_date:
        requested_date = get_today_date()
    
    try:
        data = load_stock_data()
        
        if requested_date not in data['daily_picks']:
            return jsonify({
                "success": False,
                "error": f"No stocks available for {requested_date}",
                "available_dates": get_available_dates()
            }), 404
        
        stocks_for_date = data['daily_picks'][requested_date]

        # Fix the name and logo fields using the JSON lookup
        for stock in stocks_for_date:
            ticker = stock['ticker']
            if ticker in STOCK_INFO_LOOKUP:
                stock['name'] = STOCK_INFO_LOOKUP[ticker]['name']
                stock['logo_url'] = STOCK_INFO_LOOKUP[ticker]['logo_url']
                stock['logo_path'] = STOCK_INFO_LOOKUP[ticker]['logo_url']  # Update both fields
            # If not found in lookup, keep the original values

        return jsonify({
            "success": True,
            "date": requested_date,
            "stocks": stocks_for_date,
            "available_dates": get_available_dates()
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Failed to load stocks: {str(e)}"
        }), 500

@main_bp.route('/api/stock/<ticker>')
@login_required
def api_get_stock_detail(ticker):
    """API : Fetches stock details with history (past days)"""
    requested_date = request.args.get('date', get_today_date())
    ticker = ticker.upper()
    
    try:
        data = load_stock_data()
        
        # Trouve le stock pour la date demandée
        if requested_date not in data['daily_picks']:
            return jsonify({
                "success": False,
                "error": f"No data available for {requested_date}"
            }), 404
        
        stock = next((s for s in data['daily_picks'][requested_date] 
                     if s['ticker'] == ticker), None)
        
        if not stock:
            return jsonify({
                "success": False,
                "error": f"Stock {ticker} not found for {requested_date}"
            }), 404
        
        # Adds the history for the past 7 days
        history = []
        if ticker in data['stock_history']:
            history = data['stock_history'][ticker][:7]  # past 7 days

        # Fix the name and logo fields using the JSON lookup
        company_name = stock["name"]
        logo_url = stock.get("logo_path", stock.get("logo_url", ""))
        
        response_data = {
            "success": True,
            "stock": {
                "ticker": stock["ticker"],
                "name": company_name,
                "logo_path": stock["logo_path"],
                "price": stock["price"],
                "change": stock["change"],
                "confidence": stock["confidence"],
                "confidence_score": stock.get("confidence_score", 5),
                "features": stock["features"],
                "date": requested_date,
                "history": history
            }
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Internal server error: {str(e)}"
        }), 500

@main_bp.route('/api/dates')
@login_required
def api_get_dates():
    """API : Récupère toutes les dates disponibles"""
    try:
        dates = get_available_dates()
        return jsonify({
            "success": True,
            "dates": dates,
            "current_date": get_today_date()
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Failed to load dates: {str(e)}"
        }), 500

@main_bp.route('/api/stock-history/<ticker>')
@login_required
def api_get_stock_history(ticker):
    """API : Récupère l'historique complet d'un stock (pour graphiques)"""
    ticker = ticker.upper()
    days = request.args.get('days', 30, type=int)  # Par défaut 30 jours
    
    try:
        data = load_stock_data()
        
        if ticker not in data['stock_history']:
            return jsonify({
                "success": False,
                "error": f"No history found for {ticker}"
            }), 404
        
        # Limite l'historique au nombre de jours demandé
        history = data['stock_history'][ticker][:days]
        
        return jsonify({
            "success": True,
            "ticker": ticker,
            "history": history,
            "total_days": len(history)
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Failed to load history: {str(e)}"
        }), 500


### LEARNING HUB
@main_bp.route('/learning')
@login_required
def learning():
    """Learning tab - redirects to education section"""
    return redirect(url_for('education.education_home'))

### AI PREDICTIONS PAGE
@main_bp.route('/ai-predictions')
@login_required
def ai_predictions():
    """AI Predictions page - single page for now"""
    return render_template('aipredictions.html', user=current_user)


@main_bp.route('/api/stocks-list')
@login_required
def api_get_stocks_list():
    """API : Retourne la liste complète des stocks depuis stocks_list.json"""
    try:
        # Charge le fichier stocks_list.json
        stocks_list_path = os.path.join(current_app.root_path, '..', 'content', 'stocks_list.json')
        
        if not os.path.exists(stocks_list_path):
            return jsonify({
                "success": False,
                "error": "stocks_list.json not found"
            }), 404
        
        with open(stocks_list_path, 'r', encoding='utf-8') as f:
            stocks_list = json.load(f)
        
        return jsonify({
            "success": True,
            "stocks": stocks_list,
            "total": len(stocks_list)
        })
        
    except Exception as e:
        print(f"❌ Erreur lors du chargement de stocks_list.json : {e}")
        return jsonify({
            "success": False,
            "error": f"Failed to load stocks list: {str(e)}"
        }), 500


@main_bp.route('/prediction-detail')
@login_required
def prediction_detail():
    """Prediction detail page for a specific stock"""
    ticker = request.args.get('ticker', 'AAPL')
    return render_template('prediction_detail.html', ticker=ticker.upper())


@main_bp.route('/api/prediction-detail/<ticker>')
@login_required
def api_get_prediction_detail(ticker):
    """API : Détails de prédiction pour un ticker spécifique (cherche dans TOUTES les prédictions)"""
    requested_date = request.args.get('date', get_latest_available_date())
    ticker = ticker.upper()
    
    try:
        # 1. Charge les données de prédictions
        data = load_stock_data()
        # Dans api_get_prediction_detail, ajoutez ces logs après load_stock_data():
        print(f"🔍 Structure des données chargées:")
        print(f"   daily_picks dates: {list(data.get('daily_picks', {}).keys())}")
        print(f"   all_predictions dates: {list(data.get('all_predictions', {}).keys())}")

        if 'all_predictions' in data and requested_date in data['all_predictions']:
            print(f"   all_predictions pour {requested_date}: {len(data['all_predictions'][requested_date])} stocks")
            tickers = [s['ticker'] for s in data['all_predictions'][requested_date]]
            print(f"   Premiers tickers: {tickers[:10]}")
            print(f"   AAPL dans la liste: {'AAPL' in tickers}")
        
        print(f"🔍 API prediction detail - Recherche de {ticker} pour {requested_date}")
        
        # Vérifie d'abord dans all_predictions (tous les stocks)
        if requested_date in data.get('all_predictions', {}):
            stocks_for_date = data['all_predictions'][requested_date]
            stock = next((s for s in stocks_for_date if s['ticker'] == ticker), None)
            print(f"🎯 Recherche dans all_predictions : {len(stocks_for_date)} stocks disponibles")
        
        # Fallback vers daily_picks si pas trouvé
        elif requested_date in data.get('daily_picks', {}):
            stocks_for_date = data['daily_picks'][requested_date]
            stock = next((s for s in stocks_for_date if s['ticker'] == ticker), None)
            print(f"📋 Fallback vers daily_picks : {len(stocks_for_date)} stocks disponibles")
        
        else:
            return jsonify({
                "success": False,
                "error": f"No predictions available for {requested_date}",
                "available_dates": list(data.get('all_predictions', {}).keys()) or list(data.get('daily_picks', {}).keys())
            }), 404
        
        if not stock:
            available_tickers = [s['ticker'] for s in stocks_for_date]
            print(f"❌ {ticker} non trouvé. Disponibles : {available_tickers[:10]}...")
            return jsonify({
                "success": False,
                "error": f"Stock {ticker} not found for {requested_date}",
                "available_stocks": available_tickers[:20],  # Limite pour éviter un JSON trop gros
                "total_available": len(available_tickers)
            }), 404
        
        print(f"✅ Stock {ticker} trouvé pour {requested_date}")
        
        # 2. Charge les infos depuis stocks_list.json
        stocks_list_path = os.path.join(current_app.root_path, '..', 'content', 'stocks_list.json')
        company_info = {"name": ticker, "logo_url": "/static/images/logos/default.png"}
        
        if os.path.exists(stocks_list_path):
            with open(stocks_list_path, 'r', encoding='utf-8') as f:
                stocks_list = json.load(f)
                company_data = next((s for s in stocks_list if s['ticker'] == ticker), None)
                if company_data:
                    company_info = company_data
        
        # 3. Récupère l'historique si disponible
        history = []
        if ticker in data.get('stock_history', {}):
            history = data['stock_history'][ticker][:30]  # 30 derniers jours
        
        # 4. Génère des valeurs "réelles" statiques pour le moment
        predicted_price = float(stock["price"])
        predicted_change = float(stock["change"])
        
        # Valeurs réelles simulées (à remplacer par de vraies données plus tard)
        real_price = predicted_price * (1 + (predicted_change/100) * 0.8)  # 80% de la prédiction
        real_change = predicted_change * 0.6  # Change réel plus conservateur
        
        difference = predicted_price - real_price
        difference_pct = (difference / real_price) * 100 if real_price > 0 else 0
        
        response_data = {
            "success": True,
            "prediction": {
                "ticker": ticker,
                "name": company_info.get("name", ticker),
                "logo_url": company_info.get("logo_url", "/static/images/logos/default.png"),
                "date": requested_date,
                "confidence": stock["confidence"],
                "confidence_score": stock.get("confidence_score", 5),
                "features": stock.get("features", []),
                
                # Prédictions (depuis ML)
                "predicted_price": round(predicted_price, 2),
                "predicted_change": round(predicted_change, 1),
                
                # Réel (simulé pour l'instant)
                "real_price": round(real_price, 2),
                "real_change": round(real_change, 1),
                
                # Différence
                "difference": round(difference, 2),
                "difference_pct": round(difference_pct, 1),

                # Historique pour graphiques
                "history": history[:7],  # 7 derniers jours pour le graphique
                
                # Note: Les graphiques historiques sont maintenant chargés via /api/historical-prices
                "has_historical_data": True
                
            }
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"💥 Erreur dans api_get_prediction_detail : {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": f"Internal server error: {str(e)}"
        }), 500

def generate_date_labels(days, end_date):
    """Génère des labels de dates pour les graphiques"""
    try:
        end = datetime.strptime(end_date, '%Y-%m-%d')
        if days <= 7:
            # Format court pour 1 semaine
            labels = []
            for i in range(days):
                date = end - timedelta(days=days-1-i)
                labels.append(date.strftime('%b %d'))
            return labels
        elif days <= 30:
            # Format moyen pour 1 mois
            start = end - timedelta(days=days-1)
            return [start.strftime('%b %d'), end.strftime('%b %d')]
        else:
            # Format long pour 1 an
            start = end - timedelta(days=days-1)
            return [start.strftime("%b '%y"), end.strftime("%b '%y")]
    except:
        return ["Start", "End"]

def generate_price_series(base_price, days, target_change_pct):
    """Génère une série de prix simulée pour les graphiques"""
    import random
    
    # Crée une progression graduelle vers le prix cible
    prices = []
    start_price = base_price * (1 - target_change_pct/100)
    
    for i in range(days):
        # Progression linéaire + bruit aléatoire
        progress = i / (days - 1) if days > 1 else 1
        trend_price = start_price + (base_price - start_price) * progress
        
        # Ajoute un peu de volatilité (±2%)
        noise = random.uniform(-0.02, 0.02)
        final_price = trend_price * (1 + noise)
        
        prices.append(round(final_price, 2))
    
    return prices

# ========================================
# AI predictions - GRAPH
# ========================================
# Ajoutez cette route dans routes.py :

@main_bp.route('/api/historical-prices/<ticker>')
@login_required
def api_get_historical_prices(ticker):
    """API : Retourne les prix historiques d'un ticker depuis le CSV"""
    ticker = ticker.upper()
    period = request.args.get('period', '1Y')  # 1W, 1M, 1Y
    
    try:
        import pandas as pd
        from datetime import datetime, timedelta
        
        # Charge le CSV des prix historiques
        csv_path = 'ml_pipeline/data/historical_closing_prices.csv'
        
        if not os.path.exists(csv_path):
            return jsonify({
                "success": False,
                "error": "Historical prices CSV not found"
            }), 404
        
        # Lit le CSV
        df = pd.read_csv(csv_path)
        
        # Vérifie que le ticker existe
        if ticker not in df.columns:
            available_tickers = [col for col in df.columns if col != 'Date']
            return jsonify({
                "success": False,
                "error": f"Ticker {ticker} not found in historical data",
                "available_tickers": available_tickers[:20]
            }), 404
        
        # Parse les dates
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.sort_values('Date')
        
        # Filtre selon la période demandée
        end_date = df['Date'].max()
        
        if period == '1W':
            start_date = end_date - timedelta(weeks=1)
        elif period == '1M':
            start_date = end_date - timedelta(days=30)
        elif period == '1Y':
            start_date = end_date - timedelta(days=365)
        else:
            start_date = end_date - timedelta(days=365)  # Default to 1 year
        
        # Filtre les données
        mask = (df['Date'] >= start_date) & (df['Date'] <= end_date)
        filtered_df = df.loc[mask, ['Date', ticker]].copy()
        
        # Supprime les valeurs NaN
        filtered_df = filtered_df.dropna()
        
        if filtered_df.empty:
            return jsonify({
                "success": False,
                "error": f"No historical data found for {ticker} in period {period}"
            }), 404
        
        # Convertit en format JSON
        dates = filtered_df['Date'].dt.strftime('%Y-%m-%d').tolist()
        prices = filtered_df[ticker].round(2).tolist()
        
        # Calcule les labels de dates pour l'affichage
        if period == '1W':
            date_labels = filtered_df['Date'].dt.strftime('%b %d').tolist()
        elif period == '1M':
            # Prend le premier et dernier jour
            date_labels = [
                filtered_df['Date'].iloc[0].strftime('%b %d'),
                filtered_df['Date'].iloc[-1].strftime('%b %d')
            ] if len(filtered_df) > 1 else [filtered_df['Date'].iloc[0].strftime('%b %d')]
        else:  # 1Y
            date_labels = [
                filtered_df['Date'].iloc[0].strftime("%b '%y"),
                filtered_df['Date'].iloc[-1].strftime("%b '%y")
            ] if len(filtered_df) > 1 else [filtered_df['Date'].iloc[0].strftime("%b '%y")]
        
        return jsonify({
            "success": True,
            "ticker": ticker,
            "period": period,
            "data": {
                "dates": dates,
                "prices": prices,
                "date_labels": date_labels,
                "start_date": dates[0] if dates else None,
                "end_date": dates[-1] if dates else None,
                "total_points": len(dates)
            }
        })
        
    except Exception as e:
        print(f"💥 Erreur dans api_get_historical_prices : {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": f"Internal server error: {str(e)}"
        }), 500

@main_bp.route('/api/predicted-prices/<ticker>')
@login_required
def api_get_predicted_prices(ticker):
    """API : Retourne les prix prédits d'un ticker depuis le CSV"""
    ticker = ticker.upper()
    period = request.args.get('period', '1W')  # Seulement 1W supporté pour l'instant
    
    try:
        import pandas as pd
        from datetime import datetime, timedelta
        
        # Charge le CSV des prix prédits
        csv_path = 'ml_pipeline/data/predicted_prices_5days.csv'
        
        if not os.path.exists(csv_path):
            return jsonify({
                "success": False,
                "error": "Predicted prices CSV not found"
            }), 404
        
        # Lit le CSV
        df = pd.read_csv(csv_path)
        
        # Vérifie que le ticker existe
        if ticker not in df.columns:
            available_tickers = [col for col in df.columns if col != 'Date']
            return jsonify({
                "success": False,
                "error": f"Ticker {ticker} not found in predicted data",
                "available_tickers": available_tickers[:20]
            }), 404
        
        # Parse les dates
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.sort_values('Date')
        
        # Pour l'instant, on ne supporte que 1W (les 5 derniers jours)
        if period != '1W':
            return jsonify({
                "success": False,
                "error": "Only 1W period is supported for predicted prices"
            }), 400
        
        # Prend tous les jours disponibles (5 jours)
        filtered_df = df[['Date', ticker]].copy()
        
        # Supprime les valeurs NaN
        filtered_df = filtered_df.dropna()
        
        if filtered_df.empty:
            return jsonify({
                "success": False,
                "error": f"No predicted data found for {ticker}"
            }), 404
        
        # Convertit en format JSON
        dates = filtered_df['Date'].dt.strftime('%Y-%m-%d').tolist()
        prices = filtered_df[ticker].round(2).tolist()
        
        # Calcule les labels de dates pour l'affichage (format 1W)
        date_labels = filtered_df['Date'].dt.strftime('%b %d').tolist()
        
        return jsonify({
            "success": True,
            "ticker": ticker,
            "period": period,
            "data": {
                "dates": dates,
                "prices": prices,
                "date_labels": date_labels,
                "start_date": dates[0] if dates else None,
                "end_date": dates[-1] if dates else None,
                "total_points": len(dates)
            }
        })
        
    except Exception as e:
        print(f"💥 Erreur dans api_get_predicted_prices : {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": f"Internal server error: {str(e)}"
        }), 500
    
@main_bp.route('/api/weekly-predictions/<ticker>')
def weekly_predictions_endpoint(ticker):
    return get_weekly_predictions(ticker)

@main_bp.route('/api/weekly-historical/<ticker>')
def weekly_historical_endpoint(ticker):
    return get_weekly_historical(ticker)


### ONBOARDING
@main_bp.route('/onboarding')
@login_required
def onboarding():
    """Onboarding slideshow for new users"""
    return redirect(url_for('main.onboard0'))

@main_bp.route('/onboard/0')
@login_required
def onboard0():
    return render_template('onboarding/onboard0.html')

@main_bp.route('/onboard/1')
@login_required
def onboard1():
    return render_template('onboarding/onboard1.html')

@main_bp.route('/onboard/2')
@login_required
def onboard2():
    return render_template('onboarding/onboard2.html')

@main_bp.route('/onboard/3')
@login_required
def onboard3():
    return render_template('onboarding/onboard3.html')

@main_bp.route('/onboard/4')
@login_required
def onboard4():
    return render_template('onboarding/onboard4.html')

@main_bp.route('/onboard/5')
@login_required
def onboard5():
    return render_template('onboarding/onboard5.html')

@main_bp.route('/onboard/6')
@login_required
def onboard6():
    return render_template('onboarding/onboard6.html')

@main_bp.route('/onboarding/skip')
@login_required
def onboarding_skip():
    """Skip onboarding and go to discover"""
    return redirect(url_for('main.discover'))


# ===========================
# ML MODEL
# ===========================

@main_bp.route('/admin/run-ml-predictions')
@login_required
def run_ml_predictions():
    """Route admin pour exécuter les prédictions ML"""
    try:
        # Change vers le dossier ML
        ml_dir = os.path.join(os.getcwd(), 'ml_pipeline')
        
        if not os.path.exists(ml_dir):
            return jsonify({
                "success": False,
                "error": "ML pipeline directory not found",
                "help": "Run setup first"
            }), 404
        
        # Exécute le script ML
        print("🤖 Démarrage des prédictions ML...")
        result = subprocess.run(
            ['python', 'bae.py'], 
            cwd=ml_dir,
            capture_output=True, 
            text=True,
            timeout=300  # 5 minutes max
        )
        
        if result.returncode == 0:
            # ML réussi, maintenant convertit pour l'app
            from scripts.ml_to_app_converter import convert_ml_predictions_to_app_format
            
            conversion_success = convert_ml_predictions_to_app_format()
            
            if conversion_success:
                return jsonify({
                    "success": True,
                    "message": "ML predictions generated and integrated successfully",
                    "ml_output": result.stdout[-500:],  # Dernières 500 chars
                    "timestamp": datetime.now().isoformat()
                })
            else:
                return jsonify({
                    "success": False,
                    "error": "ML succeeded but conversion to app format failed",
                    "ml_output": result.stdout[-500:]
                }), 500
        else:
            return jsonify({
                "success": False,
                "error": "ML script failed",
                "ml_error": result.stderr[-500:],
                "ml_output": result.stdout[-500:]
            }), 500
            
    except subprocess.TimeoutExpired:
        return jsonify({
            "success": False,
            "error": "ML script timed out (>5 minutes)"
        }), 500
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }), 500

@main_bp.route('/admin/ml-status')
@login_required 
def ml_status():
    """Vérifie le statut du système ML"""
    ml_dir = 'ml_pipeline'
    data_dir = os.path.join(ml_dir, 'data')
    output_dir = os.path.join(ml_dir, 'output')
    
    # Fichiers requis pour le ML
    required_files = [
        'stock_prices_1030_wide_format.csv',
        'stock_prices_0900_wide_format.csv', 
        'historical_closing_prices_wide_format.csv'
    ]
    
    status = {
        "ml_directory_exists": os.path.exists(ml_dir),
        "data_directory_exists": os.path.exists(data_dir),
        "output_directory_exists": os.path.exists(output_dir),
        "bae_script_exists": os.path.exists(os.path.join(ml_dir, 'bae.py')),
        "required_files": {},
        "latest_predictions": None
    }
    
    # Vérifie les fichiers requis
    for file in required_files:
        file_path = os.path.join(data_dir, file)
        status["required_files"][file] = {
            "exists": os.path.exists(file_path),
            "size_mb": round(os.path.getsize(file_path) / 1024 / 1024, 2) if os.path.exists(file_path) else 0
        }
    
    # Vérifie les prédictions les plus récentes
    if os.path.exists(output_dir):
        prediction_files = [f for f in os.listdir(output_dir) 
                           if f.startswith('predictions_newswire_') and f.endswith('.csv')]
        if prediction_files:
            latest = max(prediction_files)
            status["latest_predictions"] = {
                "filename": latest,
                "date": latest.replace('predictions_newswire_', '').replace('.csv', ''),
                "size_kb": round(os.path.getsize(os.path.join(output_dir, latest)) / 1024, 2)
            }
    
    status["ready_to_run"] = (
        status["ml_directory_exists"] and 
        status["bae_script_exists"] and
        all(info["exists"] for info in status["required_files"].values())
    )
    
    return jsonify(status)

@main_bp.route('/admin/setup-ml')
@login_required
def setup_ml():
    """Configure la structure ML"""
    try:
        from scripts.ml_to_app_converter import setup_ml_pipeline
        setup_ml_pipeline()
        
        return jsonify({
            "success": True,
            "message": "ML pipeline structure created",
            "next_steps": [
                "1. Place your data files in ml_pipeline/data/",
                "2. Check /admin/ml-status for requirements",
                "3. Run /admin/run-ml-predictions when ready"
            ]
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


####################################################################
@main_bp.route('/debug-routes')
def debug_routes():
    from flask import current_app
    routes = []
    for rule in current_app.url_map.iter_rules():
        routes.append(f"{rule.endpoint}: {rule}")
    return "<br>".join(routes)

