// Updated discovery.js with proper date centering functionality

document.addEventListener("DOMContentLoaded", function () {
  const dateListEl = document.querySelector('.date-list');
  const countdownEl = document.querySelector('.countdown-text');

  const today = new Date(); 
  let selectedDate = new Date(today); // Start with today selected

  // Generate dates: past days + today + tomorrow only
  function generateDates() {
    const dates = [];
    
    // Generate 7 days back to 1 day forward (tomorrow) from today
    for (let i = 7; i >= -1; i--) {
      const date = new Date(today);
      date.setDate(today.getDate() - i);
      dates.push(date);
    }
    
    return dates;
  }

  const allDates = generateDates();

  function renderDates() {
    const todayStr = today.toDateString();
    const tomorrowStr = new Date(today.getTime() + 24*60*60*1000).toDateString();
    const selectedStr = selectedDate.toDateString();

    // Find the index of selected date
    const selectedIndex = allDates.findIndex(date => date.toDateString() === selectedStr);
    
    // Always show 5 dates with selected one in the middle (index 2)
    // Calculate start index to center the selected date
    let startIndex = Math.max(0, selectedIndex - 2);
    let endIndex = Math.min(allDates.length - 1, selectedIndex + 2);
    
    // Adjust if we can't center properly due to array bounds
    if (selectedIndex < 2) {
      // Selected date is near the beginning, show first 5 dates
      startIndex = 0;
      endIndex = Math.min(allDates.length - 1, 4);
    } else if (selectedIndex >= allDates.length - 2) {
      // Selected date is near the end, show last 5 dates
      endIndex = allDates.length - 1;
      startIndex = Math.max(0, endIndex - 4);
    }
    
    const visibleDates = allDates.slice(startIndex, endIndex + 1);
    
    // Render visible dates
    dateListEl.innerHTML = visibleDates
      .map(date => {
        const dateStr = date.toDateString();
        const day = date.getDate();
        const month = date.toLocaleString('en-US', { month: 'short' });
        const isToday = dateStr === todayStr;
        const isTomorrow = dateStr === tomorrowStr;
        const isSelected = dateStr === selectedStr;
        
        // Determine styling classes
        let classes = 'date-item';
        if (isSelected) {
          classes += ' selected';
        }
        
        return `
          <span class="${classes}" 
                data-date="${date.toISOString()}"
                ${isToday ? 'data-is-today="true"' : ''}
                ${isTomorrow ? 'data-is-tomorrow="true"' : ''}>
            ${day}<br><small>${month}</small>
          </span>`;
      })
      .join('');

    // Update countdown display
    updateCountdownDisplay();
    
    // Add click handlers
    attachDateClickHandlers();
  }

  function updateCountdownDisplay() {
    const tomorrowStr = new Date(today.getTime() + 24*60*60*1000).toDateString();
    const selectedStr = selectedDate.toDateString();
    
    const isTomorrowSelected = selectedStr === tomorrowStr;
    
    if (isTomorrowSelected) {
      // Tomorrow is selected - show orange countdown with prediction loading
      countdownEl.style.backgroundColor = '#ff6b35';
      countdownEl.innerHTML = '<strong>Prediction</strong><br>loading...';
    } else {
      // Any other date selected - show regular countdown
      countdownEl.style.backgroundColor = '#ec7845';
      updateCountdown();
    }
  }

  function attachDateClickHandlers() {
    const dateItems = document.querySelectorAll('.date-item[data-date]');
    
    dateItems.forEach(item => {
      item.addEventListener('click', () => {
        const clickedDate = new Date(item.dataset.date);
        const tomorrowStr = new Date(today.getTime() + 24*60*60*1000).toDateString();
        const clickedStr = clickedDate.toDateString();
        
        // Update selected date
        selectedDate = clickedDate;
        
        // Re-render to center the newly selected date
        renderDates();
        
        // Handle special tomorrow click behavior
        if (clickedStr === tomorrowStr) {
          // Tomorrow clicked - don't fetch new data, just update countdown to orange
          console.log('Tomorrow clicked - showing prediction countdown');
          // Note: updateCountdownDisplay() is called by renderDates() above
        } else {
          // Regular date clicked - fetch stocks for that date
          fetchStocksForDate(clickedDate);
        }
      });
    });
  }

  function updateCountdown() {
    const tomorrowStr = new Date(today.getTime() + 24*60*60*1000).toDateString();
    const selectedStr = selectedDate.toDateString();
    
    if (selectedStr === tomorrowStr) {
      // Don't update countdown if tomorrow is selected (it shows "loading...")
      return;
    }
    
    const now = new Date();
    const next8am = new Date(now);
    
    // If it's past 8am today, next prediction is 8am tomorrow
    if (now.getHours() >= 8) {
      next8am.setDate(now.getDate() + 1);
    }
    next8am.setHours(8, 0, 0, 0);

    const msLeft = next8am - now;
    const hoursLeft = Math.ceil(msLeft / (1000 * 60 * 60));

    countdownEl.innerHTML = `<strong>${hoursLeft} hours</strong><br>until prediction`;
  }

  // Load stocks for selected date
  async function fetchStocksForDate(date) {
    const dateStr = date.toISOString().split('T')[0];
    
    try {
      const container = document.getElementById('stocks-container');
      container.innerHTML = '<div style="text-align: center; padding: 40px; color: #ccc;">Loading stocks...</div>';
      
      // For demo purposes, if no backend API, show sample data
      if (typeof fetch === 'undefined' || !window.location.href.includes('localhost')) {
        // Show sample data for demo
        setTimeout(() => {
          updateStockDisplay(getSampleStocks());
        }, 500);
        return;
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
      // Show sample data as fallback
      updateStockDisplay(getSampleStocks());
    }
  }

  // Sample stock data for demo
  function getSampleStocks() {
    return [
      {
        ticker: 'AAPL',
        name: 'Apple Inc.',
        price: '211.16',
        change: 2.3,
        confidence: 'high',
        logo_path: 'https://logo.clearbit.com/apple.com'
      },
      {
        ticker: 'GOOGL',
        name: 'Alphabet Inc.',
        price: '2840.32',
        change: -1.2,
        confidence: 'mid',
        logo_path: 'https://logo.clearbit.com/google.com'
      },
      {
        ticker: 'TSLA',
        name: 'Tesla Inc.',
        price: '313.51',
        change: -1.8,
        confidence: 'low',
        logo_path: 'https://logo.clearbit.com/tesla.com'
      }
    ];
  }

  // Update stock display (keeping original styling)
  function updateStockDisplay(stocks) {
    const container = document.getElementById('stocks-container');
    
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
  renderDates(); // This will center today's date initially
  
  // Load today's stocks initially
  fetchStocksForDate(selectedDate);
  
  // Update countdown every minute
  setInterval(() => {
    const tomorrowStr = new Date(today.getTime() + 24*60*60*1000).toDateString();
    const selectedStr = selectedDate.toDateString();
    
    // Only update countdown if we're not showing tomorrow's "loading..." state
    if (selectedStr !== tomorrowStr) {
      updateCountdown();
    }
  }, 60000);
});

// Keep your existing menu functions
function toggleMenu() {
  const menu = document.getElementById("logoutMenu");
  menu.style.display = (menu.style.display === "block") ? "none" : "block";
}

document.addEventListener("click", function(event) {
  const menu = document.getElementById("logoutMenu");
  const icon = document.querySelector(".menu-icon");
  if (!menu.contains(event.target) && !icon.contains(event.target)) {
    menu.style.display = "none";
  }
});

function addTransition() {
  localStorage.setItem("transitionDirection", "up");
}