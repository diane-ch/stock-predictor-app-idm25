// ===== Menu functionality =====
function toggleMenu() {
  const menu = document.getElementById("logoutMenu");
  menu.style.display = (menu.style.display === "block") ? "none" : "block";
}

function logout() { 
  alert("Logging out..."); 
}

document.addEventListener("click", (e) => {
  const menu = document.getElementById("logoutMenu");
  const icon = document.querySelector(".menu-icon");
  if (menu && icon && !menu.contains(e.target) && !icon.contains(e.target)) {
    menu.style.display = "none";
  }
});

// ===== Search functionality =====
let allStocks = [];

async function loadStocksForSearch() {
  try {
    const response = await fetch('/api/stocks-list');
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const result = await response.json();
    
    if (result.success) {
      // Transform to search format: "Company Name (TICKER)"
      allStocks = result.stocks.map(stock => ({
        display: `${stock.name} (${stock.ticker})`,
        ticker: stock.ticker,
        name: stock.name
      }));
      console.log(`📋 ${allStocks.length} stocks loaded for search`);
    }
  } catch (error) {
    console.error('❌ Error loading stocks for search:', error);
    allStocks = []; // Fallback to empty array
  }
}

function initializeSearch() {
  const searchInput = document.querySelector('.search-bar input');
  
  if (!searchInput) {
    console.log("Search input not found");
    return;
  }

  // Create dropdown container
  const searchContainer = document.querySelector('.search-bar');
  const dropdown = document.createElement('div');
  dropdown.className = 'search-dropdown';
  dropdown.style.cssText = `
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    background: white;
    border: 1px solid #ddd;
    border-top: none;
    border-radius: 0 0 8px 8px;
    max-height: 300px;
    overflow-y: auto;
    z-index: 1000;
    display: none;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
  `;
  
  searchContainer.style.position = 'relative';
  searchContainer.appendChild(dropdown);

  // Search functionality
  searchInput.addEventListener('input', (e) => {
    const query = e.target.value.toLowerCase().trim();
    
    if (query.length === 0) {
      dropdown.style.display = 'none';
      return;
    }

    // Filter stocks
    const filtered = allStocks.filter(stock => 
      stock.display.toLowerCase().includes(query) ||
      stock.ticker.toLowerCase().includes(query)
    ).slice(0, 10); // Show max 10 results

    // Populate dropdown
    if (filtered.length > 0) {
      dropdown.innerHTML = filtered.map(stock => `
        <div class="search-result-item" data-ticker="${stock.ticker}" style="
          padding: 12px 16px;
          cursor: pointer;
          border-bottom: 1px solid #eee;
          transition: background-color 0.2s;
        " onmouseover="this.style.backgroundColor='#f5f5f5'" 
           onmouseout="this.style.backgroundColor='white'">
          ${stock.display}
        </div>
      `).join('');
      dropdown.style.display = 'block';

      // Add click handlers
      dropdown.querySelectorAll('.search-result-item').forEach(item => {
        item.addEventListener('click', () => {
          const ticker = item.dataset.ticker;
          searchInput.value = item.textContent;
          dropdown.style.display = 'none';
          
          // Navigate to the selected stock's prediction detail
          window.location.href = `/prediction-detail?ticker=${encodeURIComponent(ticker)}`;
        });
      });
    } else {
      dropdown.innerHTML = `
        <div style="padding: 12px 16px; color: #666; text-align: center;">
          No stocks found for "${query}"
        </div>
      `;
      dropdown.style.display = 'block';
    }
  });

  // Hide dropdown when clicking outside
  document.addEventListener('click', (e) => {
    if (!searchContainer.contains(e.target)) {
      dropdown.style.display = 'none';
    }
  });

  // Hide dropdown on escape
  searchInput.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      dropdown.style.display = 'none';
      searchInput.blur();
    }
  });
}

// ===== Global data storage =====
let currentPredictionData = null;

// ===== Chart functionality avec vraies données historiques =====
function drawRealHistoricalChart(svgEl, data) {
  const w = 300, h = 120, pad = 10;
  svgEl.setAttribute("viewBox", `0 0 ${w} ${h}`);
  svgEl.innerHTML = "";

  if (!data || !data.prices || data.prices.length === 0) {
    // Affiche un message si pas de données
    const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
    text.setAttribute("x", w/2);
    text.setAttribute("y", h/2);
    text.setAttribute("text-anchor", "middle");
    text.setAttribute("fill", "#999");
    text.setAttribute("font-size", "12");
    text.textContent = "No historical data available";
    svgEl.appendChild(text);
    return;
  }

  const prices = data.prices;
  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const range = max - min || 1;
  const stepX = (w - pad * 2) / (prices.length - 1);

  // Crée les points
  const points = prices.map((price, i) => {
    const x = pad + i * stepX;
    const y = h - pad - ((price - min) / range) * (h - pad * 2);
    return [x, y];
  });

  // Dessine la ligne
  const d = points.map((p, i) => (i === 0 ? `M ${p[0]} ${p[1]}` : `L ${p[0]} ${p[1]}`)).join(" ");
  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  path.setAttribute("d", d);
  path.setAttribute("fill", "none");
  path.setAttribute("stroke", "#2196F3"); // Bleu pour prix réel
  path.setAttribute("stroke-width", "2");
  svgEl.appendChild(path);

  // Ajoute des points aux extrémités
  [points[0], points[points.length - 1]].forEach(point => {
    const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    circle.setAttribute("cx", point[0]);
    circle.setAttribute("cy", point[1]);
    circle.setAttribute("r", "3");
    circle.setAttribute("fill", "#2196F3");
    svgEl.appendChild(circle);
  });
}

async function loadHistoricalData(ticker, period) {
  try {
    console.log(`📈 Loading historical data for ${ticker}, period: ${period}`);
    
    const response = await fetch(`/api/historical-prices/${ticker}?period=${period}`);
    const data = await response.json();
    
    if (data.success) {
      console.log(`✅ Historical data loaded: ${data.data.total_points} points`);
      return data.data;
    } else {
      console.error(`❌ API Error: ${data.error}`);
      return null;
    }
    
  } catch (error) {
    console.error('❌ Network error loading historical data:', error);
    return null;
  }
}

function setRangeWithHistoricalData(period, ticker) {
  if (!ticker) {
    console.error('No ticker provided for historical data');
    return;
  }
  
  // Show loading state
  const svgEl = document.getElementById("lineChart");
  svgEl.innerHTML = `
    <text x="150" y="60" text-anchor="middle" fill="#999" font-size="12">
      Loading historical data...
    </text>
  `;
  
  // Load and display historical data
  loadHistoricalData(ticker, period).then(data => {
    if (data) {
      // Update date labels
      if (data.date_labels && data.date_labels.length >= 2) {
        document.getElementById("startLabel").textContent = data.date_labels[0];
        document.getElementById("endLabel").textContent = data.date_labels[data.date_labels.length - 1];
      } else if (data.start_date && data.end_date) {
        document.getElementById("startLabel").textContent = data.start_date;
        document.getElementById("endLabel").textContent = data.end_date;
      }
      
      // Draw the chart
      drawRealHistoricalChart(svgEl, data);
    } else {
      // Error state
      svgEl.innerHTML = `
        <text x="150" y="60" text-anchor="middle" fill="#ff4444" font-size="12">
          Error loading historical data
        </text>
      `;
    }
  });
}

// ===== Load prediction data from API =====
async function loadPredictionData(ticker, date = null) {
  try {
    console.log(`📊 Loading prediction data for ${ticker}...`);
    
    // Show loading state
    showLoadingState();
    
    let apiUrl = `/api/prediction-detail/${ticker}`;
    if (date) {
      apiUrl += `?date=${date}`;
    }
    
    const response = await fetch(apiUrl);
    const data = await response.json();
    
    if (data.success) {
      console.log(`✅ Prediction data loaded for ${ticker}`);
      currentPredictionData = data.prediction;
      displayPredictionData(data.prediction);
    } else {
      console.error(`❌ API Error: ${data.error}`);
      showErrorState(data.error);
    }
    
  } catch (error) {
    console.error('❌ Network error:', error);
    showErrorState('Network error while loading prediction data');
  }
}

function displayPredictionData(prediction) {
  // 1. Update header info
  document.getElementById("companyName").textContent = prediction.name;
  document.getElementById("tickerSymbol").textContent = prediction.ticker;
  document.getElementById("companyLogo").src = prediction.logo_url;
  document.getElementById("companyLogo").alt = prediction.name;
  
  // Format date nicely
  const dateObj = new Date(prediction.date + 'T00:00:00');
  const formattedDate = dateObj.toLocaleDateString('en-US', { 
    month: 'short', 
    day: 'numeric', 
    year: 'numeric' 
  });
  document.getElementById("dateChip").textContent = formattedDate;

  // 2. Update metrics
  const { difference, difference_pct, predicted_price, predicted_change, real_price, real_change } = prediction;
  
  document.getElementById("diffVal").textContent = `${Math.abs(difference).toFixed(1)}`;
  document.getElementById("diffChange").textContent = `${difference_pct >= 0 ? '+' : ''}${difference_pct.toFixed(1)}%`;

  document.getElementById("predVal").textContent = `${predicted_price}`;
  document.getElementById("predChange").textContent = `${predicted_change >= 0 ? "+" : ""}${predicted_change.toFixed(1)}%`;
  document.getElementById("predChange").className = `pill ${predicted_change >= 0 ? "up" : "down"}`;

  document.getElementById("realVal").textContent = `${real_price}`;
  document.getElementById("realPriceChange").textContent = `${real_change >= 0 ? "+" : ""}${real_change.toFixed(1)}%`;
  document.getElementById("realPriceChange").className = `pill ${real_change >= 0 ? "up" : "down"}`;

  // 3. Set up chart with historical data (default to 1W)
  const ticker = prediction.ticker;
  setRangeWithHistoricalData("1W", ticker);
  
  // Add event listeners for range buttons with historical data
  document.querySelectorAll(".range-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".range-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      
      // Load historical data for the selected period
      const period = btn.dataset.range;
      setRangeWithHistoricalData(period, ticker);
    });
  });
  
  console.log("📈 Prediction data displayed with historical chart");
}

function showLoadingState() {
  // Show loading indicators
  const elements = [
    { id: 'companyName', text: 'Loading...' },
    { id: 'tickerSymbol', text: '...' },
    { id: 'predVal', text: '$--' },
    { id: 'realVal', text: '$--' },
    { id: 'diffVal', text: '$--' }
  ];
  
  elements.forEach(({ id, text }) => {
    const element = document.getElementById(id);
    if (element) {
      element.textContent = text;
    }
  });
}

function showErrorState(errorMessage) {
  // Show error state
  document.getElementById("companyName").textContent = 'Error loading data';
  document.getElementById("companyName").style.color = '#ff4444';
  
  console.error("Error state:", errorMessage);
}

// ===== Slider functionality =====
function initializeSlider() {
  const svg = document.getElementById("lineChart");
  const track = document.getElementById("chartTrack");
  const knob = document.getElementById("chartKnob");
  const vGuide = document.getElementById("vGuide");
  const chartWrap = document.querySelector(".chart-wrap");

  if (!track || !knob || !vGuide || !chartWrap) {
    console.log("Slider elements not found, skipping slider initialization");
    return;
  }

  let pct = 0.5;

  function clamp(x, min=0, max=1){ 
    return Math.max(min, Math.min(max, x)); 
  }

  function placeByPercent(p) {
    const rect = track.getBoundingClientRect();
    knob.style.left = `${p * 100}%`;
    knob.setAttribute("aria-valuenow", Math.round(p * 100));

    const svgRect = svg.getBoundingClientRect();
    const wrapRect = chartWrap.getBoundingClientRect();
    const guideLeft = svgRect.left - wrapRect.left + p * svgRect.width;
    vGuide.style.left = `${guideLeft}px`;
  }

  function pointerToPercent(clientX){
    const rect = track.getBoundingClientRect();
    return clamp((clientX - rect.left) / rect.width);
  }

  track.addEventListener("pointerdown", (e) => {
    track.setPointerCapture(e.pointerId);
    pct = pointerToPercent(e.clientX);
    placeByPercent(pct);
  });

  knob.addEventListener("pointerdown", (e) => {
    knob.setPointerCapture(e.pointerId);
    const move = (ev) => {
      pct = pointerToPercent(ev.clientX);
      placeByPercent(pct);
    };
    const up = (ev) => {
      knob.releasePointerCapture(e.pointerId);
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
  });

  knob.addEventListener("keydown", (e) => {
    const step = 0.02;
    if (e.key === "ArrowLeft") { pct = clamp(pct - step); placeByPercent(pct); }
    if (e.key === "ArrowRight") { pct = clamp(pct + step); placeByPercent(pct); }
    if (e.key === "Home") { pct = 0; placeByPercent(pct); }
    if (e.key === "End") { pct = 1; placeByPercent(pct); }
  });

  window.addEventListener("resize", () => placeByPercent(pct));
  placeByPercent(pct);
}

// ===== Tutorial functionality =====
function initializeTutorial() {
  const tutorialBtn = document.getElementById("tutorialBtn");
  const tutorialModal = document.getElementById("tutorialModal");
  const tutorialCloseBtn = document.getElementById("tutorialCloseBtn");
  const logoutMenu = document.getElementById("logoutMenu");

  if (!tutorialBtn || !tutorialModal || !tutorialCloseBtn) {
    console.log("Tutorial elements not found");
    return;
  }

  tutorialBtn.addEventListener("click", function (e) {
    e.stopPropagation();
    tutorialModal.style.display = "flex";
    if (logoutMenu) logoutMenu.style.display = "none";
  });

  tutorialCloseBtn.addEventListener("click", function () {
    tutorialModal.style.display = "none";
  });

  tutorialModal.addEventListener("click", function (e) {
    if (e.target === tutorialModal) {
      tutorialModal.style.display = "none";
    }
  });
}

// ===== Main initialization =====
document.addEventListener("DOMContentLoaded", () => {
  console.log("🚀 Prediction Detail page loaded");
  
  // 1. Get ticker from URL parameters
  const urlParams = new URLSearchParams(window.location.search);
  const ticker = (urlParams.get("ticker") || "AAPL").toUpperCase();
  const date = urlParams.get("date"); // Optional date parameter
  
  console.log(`🎯 Loading prediction for: ${ticker}${date ? ` on ${date}` : ''}`);
  
  // 2. Load stocks for search functionality
  loadStocksForSearch();
  
  // 3. Initialize search functionality
  initializeSearch();
  
  // 4. Load prediction data
  loadPredictionData(ticker, date);
  
  // 5. Initialize other functionality
  initializeSlider();
  initializeTutorial();
  
  console.log("✅ Prediction Detail page initialized");
});