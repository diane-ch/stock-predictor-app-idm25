from flask import Flask, jsonify, request

app = Flask(__name__)

@app.route('/')
def home():
    return "Stock Predictor API is running!"

@app.route('/predict', methods=['POST'])
def predict():
    # Placeholder response
    # Later: receive input features, load model, return prediction
    return jsonify({
        "prediction": None,
        "message": "Prediction endpoint ready, waiting for model."
    })

@app.route('/stats')
def stats():
    import pandas as pd
    df = pd.read_csv('stock_data.csv', index_col=0, parse_dates=True)
    latest_date = df.index[-1].strftime('%Y-%m-%d')
    return jsonify({
        "tickers": list(df.columns),
        "latest_date": latest_date,
        "rows": len(df)
    })


if __name__ == '__main__':
    app.run(debug=True)
