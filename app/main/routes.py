# app/main/routes.py - Simplified version
from flask import Blueprint, render_template, redirect, url_for, jsonify, request
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

@main_bp.route('/ai-predictions')
@login_required
def ai_predictions():
    """AI Predictions page - single page for now"""
    return render_template('ai_predictions.html', user=current_user)

@main_bp.route('/learning')
@login_required
def learning():
    """Learning tab - redirects to education section"""
    # This redirects to your existing education home page
    return redirect(url_for('education.education_home'))

@main_bp.route('/onboarding')
@login_required
def onboarding():
    """Onboarding slideshow for new users"""
    return redirect(url_for('main.onboard1'))

@main_bp.route('/onboard/1')
@login_required
def onboard1():
    return render_template('onboard1.html')

@main_bp.route('/onboard/2')
@login_required
def onboard2():
    return render_template('onboard2.html')

@main_bp.route('/onboard/3')
@login_required
def onboard3():
    return render_template('onboard3.html')

@main_bp.route('/onboard/4')
@login_required
def onboard4():
    return render_template('onboard4.html')

@main_bp.route('/onboard/5')
@login_required
def onboard5():
    return render_template('onboard5.html')

@main_bp.route('/onboard/6')
@login_required
def onboard6():
    return render_template('onboard6.html')

@main_bp.route('/onboarding/skip')
@login_required
def onboarding_skip():
    """Skip onboarding and go to discover"""
    return redirect(url_for('main.discover'))


@main_bp.route('/debug-routes')
def debug_routes():
    from flask import current_app
    routes = []
    for rule in current_app.url_map.iter_rules():
        routes.append(f"{rule.endpoint}: {rule}")
    return "<br>".join(routes)