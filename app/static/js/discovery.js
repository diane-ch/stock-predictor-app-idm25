document.addEventListener("DOMContentLoaded", function () {
  const dateListEl = document.querySelector('.date-list');
  const countdownEl = document.querySelector('.countdown-text');

  const today = new Date();
  today.setHours(0, 0, 0, 0); // Clear time part

  function getDates() {
    const base = new Date(today);
    const dates = [];
    for (let i = -3; i <= 0; i++) { // Show today and 3 previous days
      const d = new Date(base);
      d.setDate(base.getDate() + i);
      dates.push(d);
    }
    return dates;
  }

  let fullDates = getDates(); // 4 dates total
  let selectedDate = null; // ✅ On ne sélectionne plus automatiquement aujourd'hui

  function renderDates() {
    dateListEl.innerHTML = fullDates
      .map(date => {
        const day = date.getDate();
        const month = date.toLocaleString('en-US', { month: 'short' });
        const isSelected = selectedDate && date.toDateString() === selectedDate.toDateString();
        return `
          <span class="date-item ${isSelected ? 'selected' : ''}" data-date="${date.toISOString()}">
            ${day}<br><small>${month}</small>
          </span>`;
      })
      .join('');

    // Add click events to date items
    const items = document.querySelectorAll('.date-item[data-date]');
    items.forEach(item => {
      item.addEventListener('click', () => {
        const clickedDate = new Date(item.dataset.date);
        selectedDate = clickedDate;
        renderDates(); // Re-render dates
        fetchStocksForDate(clickedDate); // ✅ Load new stock data
      });
    });
  }

  function updateCountdown() {
    // Heure actuelle en Irlande
    const nowIrish = new Date().toLocaleString("en-US", {timeZone: "Europe/Dublin"});
    const nowIrishDate = new Date(nowIrish);
    
    // Prochaine occurrence de 14h30 heure irlandaise
    const next230pm = new Date(nowIrishDate);
    next230pm.setHours(14, 30, 0, 0); // 14h30 exactement
    
    // Si on a dépassé 14h30 aujourd'hui, prendre demain 14h30
    if (nowIrishDate.getTime() >= next230pm.getTime()) {
        next230pm.setDate(next230pm.getDate() + 1);
    }
    
    // Gestion des weekends - reporter au lundi si c'est weekend
    const dayOfWeek = next230pm.getDay();
    if (dayOfWeek === 0) { // Dimanche → Lundi
        next230pm.setDate(next230pm.getDate() + 1);
    } else if (dayOfWeek === 6) { // Samedi → Lundi
        next230pm.setDate(next230pm.getDate() + 2);
    }
    
    // Calcul du temps restant
    const msLeft = next230pm.getTime() - nowIrishDate.getTime();
    const hoursLeft = Math.ceil(msLeft / (1000 * 60 * 60));
    const minutesLeft = Math.ceil(msLeft / (1000 * 60));
    
    // Affichage adapté selon le temps restant
    let timeDisplay;
    if (hoursLeft > 1) {
        timeDisplay = `${hoursLeft} hours`;
    } else if (minutesLeft > 60) {
        timeDisplay = `1 hour`;
    } else {
        timeDisplay = `${minutesLeft} minutes`;
    }
    
    countdownEl.innerHTML = `<strong>${timeDisplay}</strong> until next<br>prediction`;    
    // Debug (vous pouvez retirer ces logs après test)
    console.log(`🕐 Maintenant (Dublin): ${nowIrishDate.toLocaleString('en-IE')}`);
    console.log(`⏰ Prochaine prédiction: ${next230pm.toLocaleString('en-IE')}`);
}

  // ✅ Nouvelle fonction pour trouver automatiquement la meilleure date
  async function findValidDateAndLoad() {
    console.log("🔍 Recherche de la meilleure date avec des données...");
    
    // Tester les dates dans l'ordre inverse (aujourd'hui → hier → avant-hier → etc.)
    const datesToTest = [...fullDates].reverse(); // Commence par aujourd'hui
    
    for (let i = 0; i < datesToTest.length; i++) {
      const dateToTest = datesToTest[i];
      console.log(`📅 Test de la date: ${dateToTest.toDateString()}`);
      
      try {
        const year = dateToTest.getFullYear();
        const month = String(dateToTest.getMonth() + 1).padStart(2, '0');
        const day = String(dateToTest.getDate()).padStart(2, '0');
        const dateStr = `${year}-${month}-${day}`;
        
        const response = await fetch(`/api/stocks?date=${dateStr}`);
        const data = await response.json();
        
        if (data.success && data.stocks && data.stocks.length > 0) {
          console.log(`✅ Date valide trouvée: ${dateStr} avec ${data.stocks.length} stocks`);
          selectedDate = dateToTest;
          renderDates(); // Met à jour l'affichage des dates avec la sélection
          updateStockDisplay(data.stocks);
          return; // On s'arrête dès qu'on trouve une date valide
        } else {
          console.log(`❌ Pas de données pour ${dateStr}`);
        }
      } catch (error) {
        console.log(`❌ Erreur pour ${dateToTest.toDateString()}:`, error.message);
      }
    }
    
    // Si aucune date n'a de données, sélectionner la plus récente par défaut
    console.log("⚠️ Aucune date avec des données trouvée, sélection de la date la plus récente");
    selectedDate = fullDates[fullDates.length - 1]; // Aujourd'hui
    renderDates();
    
    // Afficher l'image d'erreur
    const container = document.getElementById('stocks-container');
    if (container) {
        container.innerHTML = '<div style="text-align: center; padding: 40px;"><img src="/static/images/market_asleep.png" alt="Market is still asleep!" style="max-width: 100%; height: auto;"></div>';
    }
  }

  // Function to fetch stocks for a specific date
  async function fetchStocksForDate(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const dateStr = `${year}-${month}-${day}`; // Format YYYY-MM-DD sans conversion timezone
    
    try {
        console.log(`📊 Chargement des stocks pour ${dateStr}...`);

        // Show loading state
        const container = document.getElementById('stocks-container');
        if (container) {
            container.innerHTML = '<div style="text-align: center; padding: 40px; color: #ccc;">Loading stocks...</div>';
        }
        
        const response = await fetch(`/api/stocks?date=${dateStr}`);
        const data = await response.json();
        
        if (data.success) {
            console.log(`✅ ${data.stocks.length} stocks chargés pour ${dateStr}`);
            updateStockDisplay(data.stocks);
        } else {
            throw new Error(data.error || 'Failed to fetch stocks');
        }
    } catch (error) {
        console.error('❌ Error fetching stocks:', error);
        const container = document.getElementById('stocks-container');
        if (container) {
            container.innerHTML = '<div style="text-align: center; padding: 40px;"><img src="/static/images/market_asleep.png" alt="Market is still asleep!" style="max-width: 100%; height: auto;"></div>';
        }
    }
  }

  // ✅ Fonction utilitaire pour vérifier si une image existe
  async function checkImageExists(url) {
    return new Promise((resolve) => {
      const img = new Image();
      img.onload = () => resolve(true);
      img.onerror = () => resolve(false);
      img.src = url;
    });
  }

  // ✅ Fonction pour obtenir l'URL du logo avec fallback
  async function getLogoUrl(stock) {
    // Vérifier si le logo Clearbit existe
    const clearbitExists = await checkImageExists(stock.logo_url);
    
    if (clearbitExists) {
      console.log(`✅ Logo Clearbit disponible pour ${stock.ticker}`);
      return stock.logo_url;
    } else {
      console.log(`❌ Logo Clearbit 404 pour ${stock.ticker}, utilisation du logo par défaut`);
      return '/static/images/logos/default.png';
    }
  }

  // Function to update stock cards display
  async function updateStockDisplay(stocks) {
    const container = document.getElementById('stocks-container');
    if (!container) return;

    if (!stocks || stocks.length === 0) {
        container.innerHTML = `
            <div style="text-align: center; padding: 40px; color: #999;">
                <p>No stocks available for this date</p>
            </div>
        `;
        return;
    }
    
    // CORRECTION : Utilise la même méthode que fetchStocksForDate pour éviter le décalage
    const year = selectedDate.getFullYear();
    const month = String(selectedDate.getMonth() + 1).padStart(2, '0');
    const day = String(selectedDate.getDate()).padStart(2, '0');
    const currentDate = `${year}-${month}-${day}`;
    
    console.log("🔗 Génération des liens pour les stocks:", stocks.map(s => s.ticker));
    console.log("📅 Date sélectionnée (objet):", selectedDate.toDateString());
    console.log("📅 Date formatée pour URL:", currentDate);
    
    // ✅ Vérification des logos en parallèle pour de meilleures performances
    const stocksWithValidLogos = await Promise.all(
      stocks.map(async (stock) => {
        const validLogoUrl = await getLogoUrl(stock);
        return { ...stock, validLogoUrl };
      })
    );
    
    container.innerHTML = stocksWithValidLogos.map(stock => {
        const detailUrl = `/stock-detail/${stock.ticker}?date=${currentDate}`;
        console.log(`🎯 Lien généré pour ${stock.ticker}: ${detailUrl}`);
        
        return `
        <a href="${detailUrl}" class="card-link">
            <div class="stock-card">
                <div class="stock-left">
                    <div class="stock-top">
                        <img class="stock-logo" src="${stock.validLogoUrl}" alt="${stock.name} Logo" 
                             onerror="this.src='/static/images/logos/default.png'">
                        <div class="stock-text">
                            <div class="stock-name">${stock.name}</div>
                            <div class="stock-ticker">${stock.ticker}</div>
                        </div>
                    </div>
                    <div class="stock-confidence">
                        <img class="confidence-logo" src="../../static/images/confidenceicon.png" alt="Logo">
                        <span class="confidence-value">${stock.confidence_score || '8.2'}/10</span>
                        <span class="confidence-label">Confidence</span>
                    </div>
                </div>
                <div class="stock-right">
                    <div class="stock-price">$${stock.price}</div>
                    <div class="stock-change ${stock.change >= 0 ? 'positive' : 'negative'}">
                        ${stock.change >= 0 ? '+' : ''}${stock.change.toFixed(1)}% 
                        <img class="arrow-icon" src="/static/images/${stock.change >= 0 ? 'up' : 'down'}-logo.png" 
                             alt="${stock.change >= 0 ? 'Up' : 'Down'}">
                    </div>
                </div>
            </div>
        </a>
    `;
    }).join('');
}

  // ✅ Initialize - modifié pour utiliser la nouvelle logique
  renderDates();
  updateCountdown();
  
  // ✅ Au lieu de charger aujourd'hui automatiquement, trouver la meilleure date
  findValidDateAndLoad();

  // 匹配 HTML 中实际存在的 ID
  const tutorialBtn = document.getElementById("tutorialBtn");
  const tutorialModal = document.getElementById("tutorialModal");
  const tutorialCloseBtn = document.getElementById("tutorialCloseBtn");
  const logoutMenu = document.getElementById("logoutMenu");

  if (!tutorialBtn || !tutorialModal || !tutorialCloseBtn) return;

  // 打开：显示为 flex 才能触发弹窗的居中布局
  tutorialBtn.addEventListener("click", function (e) {
    e.stopPropagation();                // 防止冒泡到"点击空白关闭菜单"的监听
    tutorialModal.style.display = "flex";
    if (logoutMenu) logoutMenu.style.display = "none"; // 顺手把右上角菜单收起
  });

  // 关闭按钮
  tutorialCloseBtn.addEventListener("click", function () {
    tutorialModal.style.display = "none";
  });

  // 点击遮罩关闭（只在点到遮罩本身时关闭）
  tutorialModal.addEventListener("click", function (e) {
    if (e.target === tutorialModal) {
      tutorialModal.style.display = "none";
    }
  });
});

// Menu functionality
function toggleMenu() {
  const menu = document.getElementById("logoutMenu");
  if (menu) {
    menu.style.display = (menu.style.display === "block") ? "none" : "block";
  }
}

// Optional: Close menu when clicking elsewhere
document.addEventListener("click", function(event) {
  const menu = document.getElementById("logoutMenu");
  const icon = document.querySelector(".menu-icon");
  if (menu && icon && !menu.contains(event.target) && !icon.contains(event.target)) {
    menu.style.display = "none";
  }
});

// Transition animation direction
function addTransition() {
  localStorage.setItem("transitionDirection", "up");
}