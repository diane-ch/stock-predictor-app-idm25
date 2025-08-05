# app/services/stock_service.py - Create this new file
import pandas as pd
import os
from datetime import datetime
from flask import current_app

class StockDataService:
    """Service to handle stock prediction data from CSV files"""
    
    def __init__(self):
        self.csv_path = None  # Will be set when app context is available
        self._data = None
    
    def _get_csv_path(self):
        """Get CSV path with proper app context"""
        if self.csv_path is None:
            # Only access current_app when actually needed
            self.csv_path = os.path.join(current_app.root_path, '..', 'data', 'stock_predictions.csv')
        return self.csv_path
    
    def load_data(self):
        """Load CSV data into memory"""
        try:
            csv_path = self._get_csv_path()
            self._data = pd.read_csv(csv_path)
            self._data['date'] = pd.to_datetime(self._data['date'])
            return True
        except FileNotFoundError:
            print(f"Warning: Stock data file not found at {self._get_csv_path()}")
            self._create_fallback_data()
            return False
        except Exception as e:
            print(f"Error loading stock data: {e}")
            self._create_fallback_data()
            return False
    
    def _create_fallback_data(self):
        """Create fallback data if CSV is not available"""
        fallback_data = [
            {
                'date': '2025-01-28',
                'ticker': 'AAPL',
                'company_name': 'Apple Inc.',
                'current_price': 211.16,
                'predicted_change': 2.3,
                'confidence_score': 0.85,
                'ml_rank': 1
            },
            {
                'date': '2025-01-28',
                'ticker': 'TSLA',
                'company_name': 'Tesla Inc.',
                'current_price': 313.51,
                'predicted_change': -1.8,
                'confidence_score': 0.72,
                'ml_rank': 2
            },
            # Add more fallback data...
        ]
        self._data = pd.DataFrame(fallback_data)
        self._data['date'] = pd.to_datetime(self._data['date'])
    
    def get_top_stocks_for_date(self, date_str, limit=5):
        """Get top N stocks for a specific date"""
        if self._data is None:
            self.load_data()
        
        try:
            target_date = pd.to_datetime(date_str)
            day_data = self._data[self._data['date'].dt.date == target_date.date()]
            
            if day_data.empty:
                # If no data for this date, return the most recent data
                latest_date = self._data['date'].max()
                day_data = self._data[self._data['date'] == latest_date]
            
            # Sort by ML rank and take top N
            top_stocks = day_data.nsmallest(limit, 'ml_rank')
            
            return self._format_stock_data(top_stocks)
        
        except Exception as e:
            print(f"Error getting stocks for date {date_str}: {e}")
            return self._get_default_stocks()
    
    def _format_stock_data(self, df):
        """Format dataframe into the structure expected by frontend"""
        stocks = []
        
        for _, row in df.iterrows():
            # Convert confidence score to high/mid/low
            confidence = self._get_confidence_level(row['confidence_score'])
            
            # Generate logo path
            logo_path = f"/static/images/logos/{row['ticker'].lower()}.png"
            
            stock_data = {
                'ticker': row['ticker'],
                'name': row['company_name'],
                'price': f"{row['current_price']:.2f}",
                'change': row['predicted_change'],
                'confidence': confidence,
                'logo_path': logo_path,
                'ml_rank': row['ml_rank']
            }
            stocks.append(stock_data)
        
        return stocks
    
    def _get_confidence_level(self, score):
        """Convert confidence score to high/mid/low"""
        if score >= 0.8:
            return 'high'
        elif score >= 0.7:
            return 'mid'
        else:
            return 'low'
    
    def _get_default_stocks(self):
        """Return default stocks if everything fails"""
        return [
            {
                'ticker': 'AAPL',
                'name': 'Apple Inc.',
                'price': '211.16',
                'change': 2.3,
                'confidence': 'high',
                'logo_path': '/static/images/logos/aapl.png',
                'ml_rank': 1
            },
            {
                'ticker': 'TSLA', 
                'name': 'Tesla Inc.',
                'price': '313.51',
                'change': -1.8,
                'confidence': 'mid',
                'logo_path': '/static/images/logos/tsla.png',
                'ml_rank': 2
            }
        ]

# Create global instance
stock_service = StockDataService()