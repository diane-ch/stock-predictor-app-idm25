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
  let selectedDate = fullDates[3]; // Default to today (last one)

  function renderDates() {
    dateListEl.innerHTML = fullDates
      .map(date => {
        const day = date.getDate();
        const month = date.toLocaleString('en-US', { month: 'short' });
        const isSelected = date.toDateString() === selectedDate.toDateString();
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
    const now = new Date();
    const next8am = new Date(now);
    next8am.setDate(now.getHours() >= 8 ? now.getDate() + 1 : now.getDate());
    next8am.setHours(8, 0, 0, 0);

    const msLeft = next8am - now;
    const hoursLeft = Math.ceil(msLeft / (1000 * 60 * 60));

    countdownEl.innerHTML = `<strong>${hoursLeft} hours</strong> until next prediction`;
  }

  // ✅ RÉCUPÉRATION DE LA FONCTIONNALITÉ DYNAMIQUE
  // New function to fetch stocks for a specific date
  async function fetchStocksForDate(date) {
    const dateStr = date.toISOString().split('T')[0];
    
    try {
        // Show loading state
        const container = document.getElementById('stocks-container');
        if (container) {
            container.innerHTML = '<div style="text-align: center; padding: 40px; color: #ccc;">Loading stocks...</div>';
        }
        
        const response = await fetch(`/api/stocks?date=${dateStr}`);
        const data = await response.json();
        
        if (data.success) {
            updateStockDisplay(data.stocks);
        } else {
            throw new Error(data.error || 'Failed to fetch stocks');
        }
    } catch (error) {
        console.error('Error fetching stocks:', error);
        const container = document.getElementById('stocks-container');
        if (container) {
            container.innerHTML = '<div style="text-align: center; padding: 40px; color: #ff4444;">Error loading stocks. Please try again.</div>';
        }
    }
  }

  // Function to update stock cards display
  function updateStockDisplay(stocks) {
    const container = document.getElementById('stocks-container');
    if (!container) return;
    
    container.innerHTML = stocks.map(stock => `
        <a href="detail.html?ticker=${stock.ticker}" class="card-link">
            <div class="stock-card">
                <div class="stock-left">
                    <div class="stock-top">
                        <img class="stock-logo" src="${stock.logo_path}" alt="${stock.name} Logo" 
                             onerror="this.src='/static/images/logos/default.png'">
                        <div class="stock-text">
                            <div class="stock-name">${stock.name}</div>
                            <div class="stock-ticker">${stock.ticker}</div>
                        </div>
                    </div>
                    <div class="stock-confidence">
                        <span class="confidence-dot ${stock.confidence}"></span>
                        <span class="confidence-text">${stock.confidence.charAt(0).toUpperCase() + stock.confidence.slice(1)} Confidence</span>
                    </div>
                </div>
                <div class="stock-right">
                    <div class="stock-price">${stock.price} USD</div>
                    <div class="stock-change ${stock.change >= 0 ? 'positive' : 'negative'}">
                        ${stock.change >= 0 ? '+' : ''}${stock.change.toFixed(1)}% 
                        <img class="arrow-icon" src="/static/images/${stock.change >= 0 ? 'up' : 'down'}-logo.png" 
                             alt="${stock.change >= 0 ? 'Up' : 'Down'}">
                    </div>
                </div>
            </div>
        </a>
    `).join('');
  }

  // Initialize
  renderDates();
  updateCountdown();
  
  // ✅ Load stocks for today on page load
  fetchStocksForDate(selectedDate);
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