// detail.js - Page de détail des stocks

document.addEventListener('DOMContentLoaded', function() {
    const ticker = window.TICKER;
    const staticUrl = window.STATIC_URL;
    const selectedDate = window.SELECTED_DATE;
    
    console.log(`🏷️ Chargement des données pour ${ticker}`);
    
    // Utilise la date passée en paramètre ou la date d'aujourd'hui
    const dateToUse = selectedDate || new Date().toISOString().split('T')[0];
    console.log(`📅 Date utilisée: ${dateToUse}`);
    
    loadStockDetails(ticker, dateToUse);
});

async function loadStockDetails(ticker, date = null) {
    try {
        console.log(`📊 Récupération des détails pour ${ticker}...`);
        
        // Affiche l'état de chargement
        showLoadingState();
        
        // Construit l'URL de l'API
        let apiUrl = `/api/stock/${ticker}`;
        if (date) {
            apiUrl += `?date=${date}`;
        }
        
        const response = await fetch(apiUrl);
        const data = await response.json();
        
        if (data.success) {
            console.log(`✅ Données reçues pour ${ticker}`);
            displayStockDetails(data.stock);
        } else {
            console.error(`❌ Erreur API: ${data.error}`);
            showErrorState(data.error);
        }
        
    } catch (error) {
        console.error('❌ Erreur réseau:', error);
        showErrorState('Network error while loading stock details');
    }
}

function displayStockDetails(stock) {
    // Met à jour les informations de base
    updateBasicInfo(stock);
    
    // Met à jour la confiance
    updateConfidence(stock);
    
    // Met à jour le prix et le changement
    updatePriceInfo(stock);
    
    // Met à jour les features
    updateFeatures(stock);
    
    // Affiche l'historique si disponible (optionnel)
    if (stock.history && stock.history.length > 0) {
        console.log(`📈 Historique de ${stock.ticker}: ${stock.history.length} jours`);
        // Vous pouvez ajouter un graphique ici plus tard
    }
}

function updateBasicInfo(stock) {
    // Logo et nom de l'entreprise
    const stockLogo = document.getElementById('stock-logo');
    const stockName = document.getElementById('stock-name');
    const stockTicker = document.getElementById('stock-ticker');
    
    if (stockLogo) {
        stockLogo.src = stock.logo_path;
        stockLogo.alt = `${stock.name} Logo`;
        stockLogo.onerror = function() {
            this.src = `${window.STATIC_URL}images/logos/default.png`;
        };
    }
    
    if (stockName) {
        stockName.textContent = stock.name;
    }
    
    if (stockTicker) {
        stockTicker.textContent = stock.ticker;
    }
}

function updateConfidence(stock) {
    const confidenceDot = document.getElementById('confidence-dot');
    const confidenceText = document.getElementById('confidence-text');
    
    if (confidenceDot) {
        confidenceDot.className = `confidence-dot ${stock.confidence}`;
    }
    
    if (confidenceText) {
        const confidenceLevel = stock.confidence.charAt(0).toUpperCase() + stock.confidence.slice(1);
        const confidenceScore = stock.confidence_score || '';
        confidenceText.textContent = `${confidenceLevel} Confidence ${confidenceScore ? `(${confidenceScore}/10)` : ''}`;
    }
}

function updatePriceInfo(stock) {
    const stockPrice = document.getElementById('stock-price');
    const stockChange = document.getElementById('stock-change');
    const changeText = document.getElementById('change-text');
    const changeIcon = document.getElementById('change-icon');
    
    if (stockPrice) {
        stockPrice.textContent = `${stock.price} USD`;
    }
    
    if (changeText && changeIcon && stockChange) {
        const isPositive = stock.change >= 0;
        
        changeText.textContent = `${isPositive ? '+' : ''}${stock.change.toFixed(1)}%`;
        stockChange.className = `stock-change ${isPositive ? 'positive' : 'negative'}`;
        changeIcon.src = `${window.STATIC_URL}images/${isPositive ? 'up' : 'down'}-logo.png`;
        changeIcon.alt = isPositive ? 'Up' : 'Down';
    }
}

function updateFeatures(stock) {
    const featureList = document.getElementById('feature-list');
    
    if (featureList && stock.features) {
        if (stock.features.length === 0) {
            featureList.innerHTML = '<div class="feature-item">• No specific features available</div>';
        } else {
            featureList.innerHTML = stock.features.map(feature => 
                `<div class="feature-item">• ${feature}</div>`
            ).join('');
        }
    }
}

function showLoadingState() {
    // Affiche l'état de chargement
    const elements = [
        { id: 'stock-name', text: 'Loading...' },
        { id: 'stock-price', text: '-- USD' },
        { id: 'confidence-text', text: 'Loading...' },
        { id: 'change-text', text: '--' }
    ];
    
    elements.forEach(({ id, text }) => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = text;
        }
    });
    
    const featureList = document.getElementById('feature-list');
    if (featureList) {
        featureList.innerHTML = '<div style="text-align: center; color: #ccc;">Loading features...</div>';
    }
}

function showErrorState(errorMessage) {
    // Affiche l'état d'erreur
    const stockName = document.getElementById('stock-name');
    const stockPrice = document.getElementById('stock-price');
    const confidenceText = document.getElementById('confidence-text');
    const featureList = document.getElementById('feature-list');
    
    if (stockName) {
        stockName.textContent = 'Error loading data';
        stockName.style.color = '#ff4444';
    }
    
    if (stockPrice) {
        stockPrice.textContent = '-- USD';
    }
    
    if (confidenceText) {
        confidenceText.textContent = 'N/A';
    }
    
    if (featureList) {
        featureList.innerHTML = `
            <div style="text-align: center; color: #ff4444; padding: 20px;">
                <p>Failed to load stock details</p>
                <p style="font-size: 12px; opacity: 0.7;">${errorMessage}</p>
                <button onclick="location.reload()" style="margin-top: 10px; padding: 8px 16px; background: #2196F3; color: white; border: none; border-radius: 4px; cursor: pointer;">
                    Try Again
                </button>
            </div>
        `;
    }
}

function goBackToDiscovery() {
    // Fonction pour le bouton retour
    window.history.back();
}

// Fonction pour charger les données d'une date spécifique (pour usage futur)
function loadStockForDate(date) {
    const ticker = window.TICKER;
    loadStockDetails(ticker, date);
}

// Rend les fonctions disponibles globalement
window.goBackToDiscovery = goBackToDiscovery;
window.loadStockForDate = loadStockForDate;