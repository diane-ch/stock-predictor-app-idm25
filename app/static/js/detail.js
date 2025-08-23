// detail.js - Page de détail des stocks avec popups pour les features

document.addEventListener('DOMContentLoaded', function() {
    const ticker = window.TICKER;
    const staticUrl = window.STATIC_URL;
    const selectedDate = window.SELECTED_DATE;
    
    console.log(`🏷️ Chargement des données pour ${ticker}`);
    
    // Charger les explications des features en premier
    loadFeatureExplanations().then(() => {
        // Utilise la date passée en paramètre ou la date d'aujourd'hui
        const dateToUse = selectedDate || new Date().toISOString().split('T')[0];
        console.log(`📅 Date utilisée: ${dateToUse}`);
        
        loadStockDetails(ticker, dateToUse);
    });
});

// Variable pour stocker les explications des features
let featureExplanations = {};

// Charger les explications depuis le fichier JSON
async function loadFeatureExplanations() {
    try {
        const response = await fetch('/static/json/features-explanation.json');
        if (response.ok) {
            featureExplanations = await response.json();
            console.log('✅ Feature explanations loaded:', Object.keys(featureExplanations).length, 'features');
        } else {
            console.warn('⚠️ Could not load feature explanations, using defaults');
            loadDefaultExplanations();
        }
    } catch (error) {
        console.warn('⚠️ Error loading feature explanations:', error);
        loadDefaultExplanations();
    }
}

// Explications par défaut en cas d'erreur
function loadDefaultExplanations() {
    featureExplanations = {
        "Overnight drift": "This indicates that the stock tends to have predictable price movements between market close and the next day's open. This pattern suggests potential trading opportunities based on overnight price behavior.",
        "MA(5)": "Moving Average over 5 days - This shows the stock's short-term price trend. When the current price is above the 5-day average, it suggests recent upward momentum in the stock price.",
        "MA(20)": "Moving Average over 20 days - This represents the stock's medium-term trend. A price above the 20-day average indicates positive momentum over the past month, suggesting sustained investor interest.",
        "Prev sign": "Previous Signal - This refers to a positive signal from our AI model in recent trading sessions. The algorithm identified favorable conditions that historically lead to good performance."
    };
}

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
    
    // Met à jour les features avec popups
    updateFeaturesWithPopups(stock);
    
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
    const confidenceValue = document.querySelector('.confidence-value');
    
    if (confidenceValue) {
        const scoreValue = stock.confidence_score || '8.2';
        confidenceValue.textContent = `${scoreValue}/10`;
    }
}

function updatePriceInfo(stock) {
    const stockPrice = document.getElementById('stock-price');
    const stockChange = document.getElementById('stock-change');
    const changeText = document.getElementById('change-text');
    const changeIcon = document.getElementById('change-icon');
    
    if (stockPrice) {
        stockPrice.textContent = `$${stock.price}`;
    }
    
    if (changeText && changeIcon && stockChange) {
        const isPositive = stock.change >= 0;
        
        changeText.textContent = `${isPositive ? '+' : ''}${stock.change.toFixed(1)}%`;
        stockChange.className = `stock-change ${isPositive ? 'positive' : 'negative'}`;
        changeIcon.src = `${window.STATIC_URL}images/${isPositive ? 'up' : 'down'}-logo.png`;
        changeIcon.alt = isPositive ? 'Up' : 'Down';
    }
}

// Fonction pour gérer les features avec popups
function updateFeaturesWithPopups(stock) {
    const featureList = document.getElementById('feature-list');
    
    if (featureList && stock.features) {
        if (stock.features.length === 0) {
            featureList.innerHTML = '<div class="feature-item"><span class="feature-text">• No specific features available</span></div>';
        } else {
            featureList.innerHTML = stock.features.map((feature, index) => 
                `<div class="feature-item" onclick="openFeaturePopup('${escapeHtml(feature)}')" title="Click to learn more">
                    <span class="feature-text">• ${feature}</span>
                    <img src="${window.STATIC_URL}images/Frame200.png" alt="More info" class="info-icon">
                </div>`
            ).join('');
        }
    }
}

// Fonction pour ouvrir la popup avec l'explication
function openFeaturePopup(featureName) {
    const overlay = document.getElementById('feature-popup-overlay');
    const title = document.getElementById('popup-title');
    const description = document.getElementById('popup-description');
    
    // DEBUG: Log pour vérifier
    console.log('🔍 Feature cliquée:', `"${featureName}"`);
    console.log('📚 Features disponibles:', Object.keys(featureExplanations));
    console.log('🎯 Explication trouvée:', featureExplanations[featureName] ? 'OUI' : 'NON');
    
    // Cherche l'explication correspondante
    const explanation = featureExplanations[featureName];
    
    if (explanation) {
        title.textContent = featureName;
        description.textContent = explanation;
        console.log('✅ Explication affichée pour:', featureName);
    } else {
        // Fallback si la feature n'est pas trouvée
        title.textContent = featureName;
        description.textContent = "This is a technical indicator used by our AI model to evaluate investment opportunities. It contributes to the overall analysis of this stock's potential.";
        console.log('⚠️ Pas d\'explication trouvée pour:', `"${featureName}"`, '- utilisation du fallback');
    }
    
    // Affiche la popup
    overlay.classList.add('show');
    document.body.style.overflow = 'hidden';
    
    console.log(`ℹ️ Popup ouverte pour: ${featureName}`);
}

function closeFeaturePopup() {
    const overlay = document.getElementById('feature-popup-overlay');
    overlay.classList.remove('show');
    document.body.style.overflow = '';
}

// Fonction utilitaire pour échapper les caractères HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showLoadingState() {
    // Affiche l'état de chargement
    const elements = [
        { id: 'stock-name', text: 'Loading...' },
        { id: 'stock-price', text: '$--' },
        { id: 'change-text', text: '--' }
    ];
    
    elements.forEach(({ id, text }) => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = text;
        }
    });
    
    // Confidence loading state
    const confidenceValue = document.querySelector('.confidence-value');
    if (confidenceValue) {
        confidenceValue.textContent = '--/10';
    }
    
    const featureList = document.getElementById('feature-list');
    if (featureList) {
        featureList.innerHTML = '<div style="text-align: center; color: #ccc;">Loading features...</div>';
    }
}

function showErrorState(errorMessage) {
    // Affiche l'état d'erreur
    const stockName = document.getElementById('stock-name');
    const stockPrice = document.getElementById('stock-price');
    const confidenceValue = document.querySelector('.confidence-value');
    const featureList = document.getElementById('feature-list');
    
    if (stockName) {
        stockName.textContent = 'Error loading data';
        stockName.style.color = '#ff4444';
    }
    
    if (stockPrice) {
        stockPrice.textContent = '$--';
    }
    
    if (confidenceValue) {
        confidenceValue.textContent = '--/10';
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
window.openFeaturePopup = openFeaturePopup;
window.closeFeaturePopup = closeFeaturePopup;