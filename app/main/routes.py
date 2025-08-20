import json
import os
from flask import Blueprint, current_app, render_template, redirect, url_for, jsonify, request
from flask_login import login_required, current_user
from datetime import datetime
from app.services.stock_service import stock_service

# Create the main blueprint
main_bp = Blueprint('main', __name__, template_folder='../templates')

@main_bp.route('/')
def index():
    """Root route - redirect based on authentication status"""
    if current_user.is_authenticated:
        return redirect(url_for('main.discover'))
    else:
        return redirect(url_for('auth.login'))

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


### DISCOVER PAGE
@main_bp.route('/discover')
@login_required
def discover():
    """Discover page - main content with dynamic stock data (landing page after login/register)"""
    today = datetime.now().strftime('%Y-%m-%d')
    initial_stocks = stock_service.get_top_stocks_for_date(today)
    
    return render_template('discover.html', 
                         user=current_user,
                         initial_stocks=initial_stocks,
                         selected_date=today)

@main_bp.route('/stock-detail/<ticker>')
def stock_detail(ticker):
    """Detail page for a specific stock"""
    return render_template('stock_detail.html', ticker=ticker.upper())

@main_bp.route('/api/stocks')
@login_required
def api_stocks():
    """API endpoint to get stocks for a specific date"""
    date_str = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    
    try:
        stocks = stock_service.get_top_stocks_for_date(date_str)
        return jsonify({
            'success': True,
            'stocks': stocks,
            'date': date_str
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'stocks': []
        }), 500
    
@main_bp.route('/api/stocks-list')
@login_required
def api_stocks_list():
    """API endpoint to get the list of all stocks"""
    try:
        # Path to the JSON file with the list of all the stocks
        json_path = os.path.join(current_app.root_path, '..', 'content', 'stocks_list.json')
        
        with open(json_path, 'r', encoding='utf-8') as f:
            stocks_data = json.load(f)
        
        return jsonify({
            'success': True,
            'stocks': stocks_data
        })
    except FileNotFoundError:
        return jsonify({
            'success': False,
            'error': 'Stocks list file not found',
            'stocks': []
        }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'stocks': []
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


@main_bp.route('/prediction-detail')
@login_required
def prediction_detail():
    """Prediction detail page for a specific stock"""
    ticker = request.args.get('ticker', 'AAPL')
    return render_template('prediction_detail.html', ticker=ticker.upper())



####################################################################
@main_bp.route('/debug-routes')
def debug_routes():
    from flask import current_app
    routes = []
    for rule in current_app.url_map.iter_rules():
        routes.append(f"{rule.endpoint}: {rule}")
    return "<br>".join(routes)