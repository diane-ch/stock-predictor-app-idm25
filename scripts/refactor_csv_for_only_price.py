import pandas as pd
import numpy as np
import os

def convert_predictions_to_pivot_format(
    input_file='ml_pipeline/output/predictions_history.csv',
    output_file='ml_pipeline/output/predictions_price_matrix.csv'
):
    """
    Convertit le fichier predictions_history.csv (format long) 
    vers un format pivot avec seulement les prix (format large)
    
    Input format:  date,ticker,name,price,change,confidence,feature1,feature2,feature3,feature4
    Output format: Date,AAPL,MSFT,NVDA,AMZN,... (une colonne par ticker)
    
    Args:
        input_file (str): Chemin vers predictions_history.csv
        output_file (str): Chemin de sortie pour le fichier pivot
    """
    try:
        print(f"📊 Lecture du fichier de prédictions : {input_file}")
        
        # Vérifie si le fichier existe
        if not os.path.exists(input_file):
            print(f"❌ Fichier non trouvé : {input_file}")
            return False
        
        # Lit le fichier CSV
        df_predictions = pd.read_csv(input_file)
        
        print(f"📄 {len(df_predictions)} lignes trouvées")
        print(f"📅 Dates uniques : {sorted(df_predictions['date'].unique())}")
        print(f"🏢 Tickers uniques : {len(df_predictions['ticker'].unique())}")
        
        # Vérifie les colonnes requises
        required_columns = ['date', 'ticker', 'price']
        missing_columns = [col for col in required_columns if col not in df_predictions.columns]
        
        if missing_columns:
            print(f"❌ Colonnes manquantes : {missing_columns}")
            print(f"📋 Colonnes disponibles : {list(df_predictions.columns)}")
            return False
        
        # Affiche quelques infos sur les données
        print(f"💰 Prix min : {df_predictions['price'].min():.2f}")
        print(f"💰 Prix max : {df_predictions['price'].max():.2f}")
        
        # Crée le pivot table
        print(f"🔄 Création du format pivot...")
        
        # Utilise pivot_table pour gérer les doublons potentiels (prend la moyenne)
        df_pivot = df_predictions.pivot_table(
            index='date',           # Les dates deviennent les lignes
            columns='ticker',       # Les tickers deviennent les colonnes
            values='price',         # Les valeurs sont les prix
            aggfunc='mean'          # En cas de doublons, prend la moyenne
        )
        
        # Réinitialise l'index pour avoir 'date' comme colonne
        df_pivot = df_pivot.reset_index()
        
        # Renomme la colonne 'date' en 'Date' pour correspondre au format attendu
        df_pivot = df_pivot.rename(columns={'date': 'Date'})
        
        # Arrondit les prix à 2 décimales
        numeric_columns = df_pivot.select_dtypes(include=[np.number]).columns
        df_pivot[numeric_columns] = df_pivot[numeric_columns].round(2)
        
        # Trie par date
        df_pivot = df_pivot.sort_values('Date')
        
        # Affiche les informations sur le résultat
        print(f"📊 Format pivot créé :")
        print(f"   - {len(df_pivot)} lignes (dates)")
        print(f"   - {len(df_pivot.columns) - 1} colonnes de tickers")
        print(f"   - Tickers : {list(df_pivot.columns[1:])}")
        
        # Crée le dossier de sortie si nécessaire
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # Sauvegarde le fichier
        df_pivot.to_csv(output_file, index=False)
        
        print(f"\n✅ Conversion réussie !")
        print(f"📄 Fichier créé : {output_file}")
        
        # Affiche un aperçu
        print(f"\n📋 Aperçu des premières lignes :")
        print(df_pivot.head())
        
        # Affiche des statistiques sur les données manquantes
        missing_data = df_pivot.isnull().sum()
        missing_tickers = missing_data[missing_data > 0]
        
        if len(missing_tickers) > 0:
            print(f"\n⚠️ Données manquantes par ticker :")
            for ticker, missing_count in missing_tickers.items():
                if ticker != 'Date':
                    print(f"   - {ticker}: {missing_count} dates manquantes")
        else:
            print(f"\n✅ Aucune donnée manquante détectée")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la conversion : {e}")
        import traceback
        traceback.print_exc()
        return False

def create_sample_predictions_history():
    """
    Crée un fichier d'exemple predictions_history.csv pour tester
    """
    sample_data = [
        ['2025-08-19', 'AAPL', 'AAPL', 230.8, 0.3, 0.9, 'Overnight drift', 'Ret(1d)', 'MA(5)', 'MA(20)'],
        ['2025-08-19', 'ABBV', 'ABBV', 210.76, 2.0, 1.3, 'Overnight drift', 'Ret(1d)', 'MA(5)', 'Prev intraday ret'],
        ['2025-08-19', 'ACN', 'ACN', 258.6, 3.6, 1.5, 'Overnight drift', 'Ret(1d)', 'MA(20)', 'MA(5)'],
        ['2025-08-19', 'MSFT', 'MSFT', 429.5, 1.2, 0.8, 'Volume spike', 'RSI signal', 'MA(20)', 'Support level'],
        ['2025-08-20', 'AAPL', 'AAPL', 232.1, 0.5, 1.1, 'Market momentum', 'Ret(1d)', 'MA(5)', 'MA(20)'],
        ['2025-08-20', 'ABBV', 'ABBV', 212.3, 0.7, 0.9, 'Technical breakout', 'Ret(1d)', 'MA(5)', 'Volume spike'],
        ['2025-08-20', 'ACN', 'ACN', 261.2, 1.0, 1.2, 'Earnings beat', 'Ret(1d)', 'MA(20)', 'MA(5)'],
        ['2025-08-20', 'MSFT', 'MSFT', 431.8, 0.5, 0.6, 'Analyst upgrade', 'RSI signal', 'MA(20)', 'News sentiment'],
        ['2025-08-21', 'AAPL', 'AAPL', 228.9, -1.4, 0.7, 'Resistance break', 'Ret(1d)', 'MA(5)', 'MA(20)'],
        ['2025-08-21', 'ABBV', 'ABBV', 209.1, -1.5, 0.8, 'Options flow', 'Ret(1d)', 'MA(5)', 'MACD crossover'],
        ['2025-08-21', 'ACN', 'ACN', 259.8, -0.5, 1.0, 'Sector rotation', 'Ret(1d)', 'MA(20)', 'MA(5)'],
        ['2025-08-21', 'MSFT', 'MSFT', 434.6, 0.6, 0.9, 'Support level', 'RSI signal', 'MA(20)', 'Volume spike']
    ]
    
    columns = ['date', 'ticker', 'name', 'price', 'change', 'confidence', 'feature1', 'feature2', 'feature3', 'feature4']
    df_sample = pd.DataFrame(sample_data, columns=columns)
    
    # Crée le dossier si nécessaire
    os.makedirs('ml_pipeline/output', exist_ok=True)
    
    # Sauvegarde
    sample_file = 'ml_pipeline/output/predictions_history.csv'
    df_sample.to_csv(sample_file, index=False)
    
    print(f"✅ Fichier d'exemple créé : {sample_file}")
    print(f"📊 {len(df_sample)} lignes d'exemple")
    
    return sample_file

def main():
    """
    Fonction principale pour tester le convertisseur
    """
    print("🔄 Convertisseur Predictions → Format Pivot")
    print("=" * 50)
    
    # Chemin du fichier d'entrée
    input_file = 'ml_pipeline/output/predictions_history.csv'
    
    # Vérifie si le fichier existe, sinon crée un exemple
    if not os.path.exists(input_file):
        print(f"⚠️ Fichier {input_file} non trouvé")
        print("📝 Création d'un fichier d'exemple...")
        create_sample_predictions_history()
    
    # Conversion
    success = convert_predictions_to_pivot_format(
        input_file=input_file,
        output_file='ml_pipeline/output/predictions_price_matrix.csv'
    )
    
    if success:
        print("\n🎉 Conversion terminée avec succès !")
    else:
        print("\n❌ Échec de la conversion")

if __name__ == "__main__":
    main()