// ===== Menu functionality =====
function toggleMenu() {
  const menu = document.getElementById("logoutMenu");
  menu.style.display = (menu.style.display === "block") ? "none" : "block";
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
      allStocks = result.stocks.map(stock => ({
        display: `${stock.name} (${stock.ticker})`,
        ticker: stock.ticker,
        name: stock.name
      }));
      console.log(`📋 ${allStocks.length} stocks loaded for search`);
    }
  } catch (error) {
    console.error('⚠ Error loading stocks for search:', error);
    allStocks = [];
  }
}

function initializeSearch() {
  const searchInput = document.querySelector('.search-bar input');
  
  if (!searchInput) {
    console.log("Search input not found");
    return;
  }

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

  searchInput.addEventListener('input', (e) => {
    const query = e.target.value.toLowerCase().trim();
    
    if (query.length === 0) {
      dropdown.style.display = 'none';
      return;
    }

    const filtered = allStocks.filter(stock => 
      stock.display.toLowerCase().includes(query) ||
      stock.ticker.toLowerCase().includes(query)
    ).slice(0, 10);

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

      dropdown.querySelectorAll('.search-result-item').forEach(item => {
        item.addEventListener('click', () => {
          const ticker = item.dataset.ticker;
          searchInput.value = item.textContent;
          dropdown.style.display = 'none';
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

  document.addEventListener('click', (e) => {
    if (!searchContainer.contains(e.target)) {
      dropdown.style.display = 'none';
    }
  });

  searchInput.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      dropdown.style.display = 'none';
      searchInput.blur();
    }
  });
}

// ===== Logo validation utility =====
async function checkImageExists(url) {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => resolve(true);
    img.onerror = () => resolve(false);
    img.src = url;
  });
}

async function getValidLogoUrl(logoUrl, ticker) {
  const clearbitExists = await checkImageExists(logoUrl);
  
  if (clearbitExists) {
    console.log(`✅ Logo Clearbit disponible pour ${ticker}`);
    return logoUrl;
  } else {
    console.log(`⚠ Logo Clearbit 404 pour ${ticker}, utilisation du logo par défaut`);
    return '/static/images/logos/default.png';
  }
}

// ===== Global data storage (only for 1W) =====
let currentPredictionData = null;
let weeklyPredictionData = null;
let weeklyHistoricalData = null;
let currentDayIndex = 4;

// ===== UI HELPER FUNCTIONS =====
function createExplanationBlock() {
  const explanationDiv = document.createElement('div');
  explanationDiv.id = 'explanationBlock';
  explanationDiv.className = 'explanation-block';
  explanationDiv.style.cssText = `
    background: #f8f9fa;
    border: 1px solid #e9ecef;
    border-radius: 8px;
    padding: 16px;
    margin: 16px 0;
    color: #6c757d;
    font-size: 14px;
    line-height: 1.4;
    text-align: center;
  `;
  explanationDiv.innerHTML = `
    <div style="font-weight: 600; margin-bottom: 8px;">📈 Historical Price Data</div>
    <div>This view shows historical price movements over the selected period.<br><br>In future developments and as time passes, the prediction curve will also be available in the 1M and 1Y views.</div>
  `;
  return explanationDiv;
}

function hideMetricsAndDate() {
  const metricsDiv = document.querySelector('.metrics');
  const dateChip = document.getElementById('dateChip');
  
  if (metricsDiv) {
    metricsDiv.style.display = 'none';
  }
  if (dateChip) {
    dateChip.style.display = 'none';
  }
}

function showMetricsAndDate() {
  const metricsDiv = document.querySelector('.metrics');
  const dateChip = document.getElementById('dateChip');
  
  if (metricsDiv) {
    metricsDiv.style.display = 'block';
  }
  if (dateChip) {
    dateChip.style.display = 'block';
  }
}

function showExplanationBlock() {
  // Remove existing explanation block if any
  const existingBlock = document.getElementById('explanationBlock');
  if (existingBlock) {
    existingBlock.remove();
  }
  
  // Create and insert new explanation block
  const explanationBlock = createExplanationBlock();
  const chartWrap = document.querySelector('.chart-wrap');
  if (chartWrap) {
    chartWrap.parentNode.insertBefore(explanationBlock, chartWrap);
  }
}

function hideExplanationBlock() {
  const explanationBlock = document.getElementById('explanationBlock');
  if (explanationBlock) {
    explanationBlock.remove();
  }
}

// ===== 1W SPECIFIC FUNCTIONS =====
async function loadWeeklyPredictionData(ticker) {
  try {
    console.log(`📈 Loading weekly prediction data for ${ticker}...`);
    
    const response = await fetch(`/api/weekly-predictions/${ticker}`);
    const data = await response.json();
    
    if (data.success) {
      weeklyPredictionData = data.data;
      console.log(`✅ Weekly prediction data loaded: ${weeklyPredictionData.dates.length} days`);
      return weeklyPredictionData;
    } else {
      console.error(`⚠ API Error: ${data.error}`);
      return null;
    }
    
  } catch (error) {
    console.error('⚠ Network error loading weekly prediction data:', error);
    return null;
  }
}

async function loadWeeklyHistoricalData(ticker) {
  try {
    console.log(`📊 Loading weekly historical data for ${ticker}...`);
    
    const response = await fetch(`/api/weekly-historical/${ticker}`);
    const data = await response.json();
    
    if (data.success) {
      weeklyHistoricalData = data.data;
      console.log(`✅ Weekly historical data loaded: ${weeklyHistoricalData.dates.length} days`);
      return weeklyHistoricalData;
    } else {
      console.error(`⚠ API Error: ${data.error}`);
      return null;
    }
    
  } catch (error) {
    console.error('⚠ Network error loading weekly historical data:', error);
    return null;
  }
}

function calculateDynamicValues(dayIndex, ticker) {
  if (!weeklyPredictionData || !weeklyHistoricalData) {
    console.error('Weekly data not loaded');
    return null;
  }

  const predData = weeklyPredictionData;
  const histData = weeklyHistoricalData;
  
  if (dayIndex < 0 || dayIndex >= predData.dates.length) {
    console.error(`Invalid day index: ${dayIndex}`);
    return null;
  }

  const currentDate = predData.dates[dayIndex];
  const predicted_price = predData.prices[dayIndex];
  const real_price = histData.prices[dayIndex];
  
  let predicted_change = 0;
  let real_change = 0;
  
  if (dayIndex > 0) {
    // Pour les jours 1-4, utiliser le prix réel du jour précédent
    const prevRealPrice = histData.prices[dayIndex - 1];
    predicted_change = ((predicted_price - prevRealPrice) / prevRealPrice) * 100;
    real_change = ((real_price - prevRealPrice) / prevRealPrice) * 100;
  } else {
    // Pour le premier jour (index 0), utiliser le prix du jour précédent fourni par l'API
    if (histData.previous_day_price && histData.previous_day_price > 0) {
      const prevDayPrice = histData.previous_day_price;
      predicted_change = ((predicted_price - prevDayPrice) / prevDayPrice) * 100;
      real_change = ((real_price - prevDayPrice) / prevDayPrice) * 100;
    } else {
      // Fallback si pas de prix précédent disponible
      predicted_change = 0;
      real_change = 0;
    }
  }
  
  const difference = predicted_price - real_price;
  const difference_pct = (difference / real_price) * 100;

  return {
    date: currentDate,
    predicted_price: predicted_price,
    predicted_change: predicted_change,
    real_price: real_price,
    real_change: real_change,
    difference: Math.abs(difference),
    difference_pct: difference_pct
  };
}

function updateDisplayValues(dayIndex, ticker) {
  const values = calculateDynamicValues(dayIndex, ticker);
  
  if (!values) {
    console.error('Cannot calculate values for day index:', dayIndex);
    return;
  }

  // Check if we're on the last day (most recent) where real price might not be available
  const isLastDay = dayIndex === (weeklyPredictionData.dates.length - 1);
  const hasValidRealPrice = values.real_price && values.real_price > 0;

  document.getElementById("diffVal").textContent = `$${values.difference.toFixed(1)}`;
  document.getElementById("diffChange").textContent = `${values.difference_pct >= 0 ? '+' : ''}${values.difference_pct.toFixed(1)}%`;

  document.getElementById("predVal").textContent = `$${values.predicted_price.toFixed(2)}`;
  document.getElementById("predChange").textContent = `${values.predicted_change >= 0 ? "+" : ""}${values.predicted_change.toFixed(1)}%`;

  // Handle real price display based on availability
  if (isLastDay && !hasValidRealPrice) {
    document.getElementById("realVal").textContent = `Unknown`;
    document.getElementById("realPriceChange").textContent = `--`;
    
    // Also update difference to show it's unknown
    document.getElementById("diffVal").textContent = `Unknown`;
    document.getElementById("diffChange").textContent = `--`;
  } else {
    document.getElementById("realVal").textContent = `$${values.real_price.toFixed(2)}`;
    document.getElementById("realPriceChange").textContent = `${values.real_change >= 0 ? "+" : ""}${values.real_change.toFixed(1)}%`;
  }

  const dateObj = new Date(values.date + 'T00:00:00');
  const formattedDate = dateObj.toLocaleDateString('en-US', { 
    month: 'short', 
    day: 'numeric', 
    year: 'numeric' 
  });
  document.getElementById("dateChip").textContent = formattedDate;

  console.log(`📊 Updated values for day ${dayIndex + 1}/5 (${values.date})`);
  setTimeout(() => {
    // Récupérer les nouvelles valeurs affichées
    const predChangeText = document.getElementById("predChange").textContent;
    const realChangeText = document.getElementById("realPriceChange").textContent;
    
    console.log("🎚️ Slider moved - updating pills:");
    console.log("predChangeText:", predChangeText);
    console.log("realChangeText:", realChangeText);
    
    // Extraire les valeurs numériques
    const predValue = parseFloat(predChangeText.replace(/[+%]/g, ''));
    const realValue = parseFloat(realChangeText.replace(/[+%]/g, ''));
    
    console.log("🎚️ Parsed values - pred:", predValue, "real:", realValue);
    
    // Mettre à jour les flèches
    updatePillClasses(predValue, realValue);
  }, 50);
}

function drawWeeklyComparisonChart(svgEl, realData, predictedData) {
  const w = 300, h = 120, pad = 10;
  svgEl.setAttribute("viewBox", `0 0 ${w} ${h}`);
  svgEl.innerHTML = "";

  if (!realData || !realData.prices || realData.prices.length === 0) {
    const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
    text.setAttribute("x", w/2);
    text.setAttribute("y", h/2);
    text.setAttribute("text-anchor", "middle");
    text.setAttribute("fill", "#999");
    text.setAttribute("font-size", "12");
    text.textContent = "No weekly data available";
    svgEl.appendChild(text);
    return;
  }

  const realPrices = realData.prices;
  const predictedPrices = predictedData ? predictedData.prices : null;
  
  let allPrices = [...realPrices];
  if (predictedPrices) {
    allPrices = [...allPrices, ...predictedPrices];
  }
  
  const min = Math.min(...allPrices);
  const max = Math.max(...allPrices);
  const range = max - min || 1;
  const stepX = (w - pad * 2) / (realPrices.length - 1);

  const createPoints = (prices) => {
    return prices.map((price, i) => {
      const x = pad + i * stepX;
      const y = h - pad - ((price - min) / range) * (h - pad * 2);
      return [x, y];
    });
  };

  const realPoints = createPoints(realPrices);

  // Real prices line (gray)
  const realPath = realPoints.map((p, i) => (i === 0 ? `M ${p[0]} ${p[1]}` : `L ${p[0]} ${p[1]}`)).join(" ");
  const realLine = document.createElementNS("http://www.w3.org/2000/svg", "path");
  realLine.setAttribute("d", realPath);
  realLine.setAttribute("fill", "none");
  realLine.setAttribute("stroke", "#999999");
  realLine.setAttribute("stroke-width", "2");
  svgEl.appendChild(realLine);

  // Predicted prices line (green dashed)
  if (predictedPrices && predictedPrices.length === realPrices.length) {
    const predictedPoints = createPoints(predictedPrices);
    
    const predPath = predictedPoints.map((p, i) => (i === 0 ? `M ${p[0]} ${p[1]}` : `L ${p[0]} ${p[1]}`)).join(" ");
    const predLine = document.createElementNS("http://www.w3.org/2000/svg", "path");
    predLine.setAttribute("d", predPath);
    predLine.setAttribute("fill", "none");
    predLine.setAttribute("stroke", "#16CCA0");
    predLine.setAttribute("stroke-width", "2");
    predLine.setAttribute("stroke-dasharray", "5,5");
    svgEl.appendChild(predLine);

    predPointsList = [predictedPoints[0], predictedPoints[1], predictedPoints[2], predictedPoints[3], predictedPoints[4]];
    predPointsList.forEach(point => {
      const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      circle.setAttribute("cx", point[0]);
      circle.setAttribute("cy", point[1]);
      circle.setAttribute("r", "3");
      circle.setAttribute("fill", "#16CCA0");
      svgEl.appendChild(circle);
    });
  }

  [realPoints[0], realPoints[1], realPoints[2], realPoints[3], realPoints[realPoints.length - 1]].forEach(point => {
    const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    circle.setAttribute("cx", point[0]);
    circle.setAttribute("cy", point[1]);
    circle.setAttribute("r", "3");
    circle.setAttribute("fill", "#999999");
    svgEl.appendChild(circle);
  });
}

function setupWeeklySlider(ticker) {
  const track = document.getElementById("chartTrack");
  const knob = document.getElementById("chartKnob");
  const vGuide = document.getElementById("vGuide");
  const svg = document.getElementById("lineChart");
  const chartWrap = document.querySelector(".chart-wrap");

  if (!track || !knob || !vGuide || !chartWrap || !weeklyPredictionData) {
    console.log("Weekly slider setup failed - missing elements or data");
    return;
  }

  const positions = [0, 0.25, 0.5, 0.75, 1.0];
  
  function snapToNearestPosition(rawPercent) {
    let closest = 0;
    let minDistance = Math.abs(rawPercent - positions[0]);
    
    for (let i = 1; i < positions.length; i++) {
      const distance = Math.abs(rawPercent - positions[i]);
      if (distance < minDistance) {
        minDistance = distance;
        closest = i;
      }
    }
    
    return closest;
  }

  const pad = 10;

  function updateSliderPosition(dayIndex) {
    const pct = positions[dayIndex];
    const knobPct = (pad + pct * (300 - pad * 2)) / 300; // 300 = w dans drawWeeklyComparisonChart
    knob.style.left = `${knobPct * 100}%`;
    knob.setAttribute("aria-valuenow", Math.round(pct * 100));

    const svgRect = svg.getBoundingClientRect();
    const wrapRect = chartWrap.getBoundingClientRect();
    const guideLeft = svgRect.left - wrapRect.left + pad + pct * (svgRect.width - pad * 2);
    vGuide.style.left = `${guideLeft}px`;
    
    currentDayIndex = dayIndex;
    updateDisplayValues(currentDayIndex, ticker);
    
    console.log(`🎯 Slider moved to day ${dayIndex + 1}/5`);
  }

  function pointerToPercent(clientX) {
    const rect = track.getBoundingClientRect();
    return Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
  }

  track.addEventListener("pointerdown", (e) => {
    track.setPointerCapture(e.pointerId);
    const rawPct = pointerToPercent(e.clientX);
    const dayIndex = snapToNearestPosition(rawPct);
    updateSliderPosition(dayIndex);
  });

  knob.addEventListener("pointerdown", (e) => {
    knob.setPointerCapture(e.pointerId);
    
    const move = (ev) => {
      const rawPct = pointerToPercent(ev.clientX);
      const dayIndex = snapToNearestPosition(rawPct);
      updateSliderPosition(dayIndex);
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
    if (e.key === "ArrowLeft" && currentDayIndex > 0) {
      updateSliderPosition(currentDayIndex - 1);
    }
    if (e.key === "ArrowRight" && currentDayIndex < positions.length - 1) {
      updateSliderPosition(currentDayIndex + 1);
    }
    if (e.key === "Home") {
      updateSliderPosition(4);
    }
    if (e.key === "End") {
      updateSliderPosition(positions.length - 1);
    }
  });

  window.addEventListener("resize", () => {
    updateSliderPosition(currentDayIndex);
  });

  updateSliderPosition(4);
}

// ===== 1M/1Y SPECIFIC FUNCTIONS =====
async function loadHistoricalData(ticker, period) {
  try {
    console.log(`📈 Loading historical data for ${ticker}, period: ${period}`);
    
    const response = await fetch(`/api/historical-prices/${ticker}?period=${period}`);
    const data = await response.json();
    
    if (data.success) {
      console.log(`✅ Historical data loaded: ${data.data.total_points} points`);
      return data.data;
    } else {
      console.error(`⚠ API Error: ${data.error}`);
      return null;
    }
    
  } catch (error) {
    console.error('⚠ Network error loading historical data:', error);
    return null;
  }
}

function drawStaticChart(svgEl, data) {
  const w = 300, h = 120, pad = 10;
  svgEl.setAttribute("viewBox", `0 0 ${w} ${h}`);
  svgEl.innerHTML = "";

  if (!data || !data.prices || data.prices.length === 0) {
    const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
    text.setAttribute("x", w/2);
    text.setAttribute("y", h/2);
    text.setAttribute("text-anchor", "middle");
    text.setAttribute("fill", "#999");
    text.setAttribute("font-size", "12");
    text.textContent = "No data available";
    svgEl.appendChild(text);
    return;
  }

  const prices = data.prices;
  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const range = max - min || 1;
  const stepX = (w - pad * 2) / (prices.length - 1);

  // Trouver les indices des valeurs min et max
  const minIndex = prices.indexOf(min);
  const maxIndex = prices.indexOf(max);

  const points = prices.map((price, i) => {
    const x = pad + i * stepX;
    const y = h - pad - ((price - min) / range) * (h - pad * 2);
    return [x, y];
  });

  // Dessiner la ligne principale
  const d = points.map((p, i) => (i === 0 ? `M ${p[0]} ${p[1]}` : `L ${p[0]} ${p[1]}`)).join(" ");
  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  path.setAttribute("d", d);
  path.setAttribute("fill", "none");
  path.setAttribute("stroke", "#999999");
  path.setAttribute("stroke-width", "2");
  svgEl.appendChild(path);

  // Points de début et fin (comme avant)
  [points[0], points[points.length - 1]].forEach(point => {
    const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    circle.setAttribute("cx", point[0]);
    circle.setAttribute("cy", point[1]);
    circle.setAttribute("r", "3");
    circle.setAttribute("fill", "#999999");
    svgEl.appendChild(circle);
  });

  // === NOUVEAUTÉ : Points et labels min/max ===
  
  // Point minimum (rouge)
  const minPoint = points[minIndex];
  const minCircle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
  minCircle.setAttribute("cx", minPoint[0]);
  minCircle.setAttribute("cy", minPoint[1]);
  minCircle.setAttribute("r", "4");
  minCircle.setAttribute("fill", "#999999");
  minCircle.setAttribute("stroke", "white");
  minCircle.setAttribute("stroke-width", "1");
  svgEl.appendChild(minCircle);

  // Label minimum
  const minText = document.createElementNS("http://www.w3.org/2000/svg", "text");
  minText.setAttribute("x", minPoint[0]);
  minText.setAttribute("y", minPoint[1] + 14); // En-dessous du point
  minText.setAttribute("text-anchor", "middle");
  minText.setAttribute("fill", "#999999");
  minText.setAttribute("font-size", "10");
  minText.setAttribute("font-weight", "bold");
  minText.textContent = `$${min.toFixed(2)}`;
  svgEl.appendChild(minText);

  // Point maximum (vert)
  const maxPoint = points[maxIndex];
  const maxCircle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
  maxCircle.setAttribute("cx", maxPoint[0]);
  maxCircle.setAttribute("cy", maxPoint[1]);
  maxCircle.setAttribute("r", "4");
  maxCircle.setAttribute("fill", "#999999");
  maxCircle.setAttribute("stroke", "white");
  maxCircle.setAttribute("stroke-width", "1");
  svgEl.appendChild(maxCircle);

  // Label maximum
  const maxText = document.createElementNS("http://www.w3.org/2000/svg", "text");
  maxText.setAttribute("x", maxPoint[0]);
  maxText.setAttribute("y", maxPoint[1] - 10); // Au-dessus du point
  maxText.setAttribute("text-anchor", "middle");
  maxText.setAttribute("fill", "#999999");
  maxText.setAttribute("font-size", "10");
  maxText.setAttribute("font-weight", "bold");
  maxText.textContent = `$${max.toFixed(2)}`;
  svgEl.appendChild(maxText);

  console.log(`📊 Static chart drawn with min: $${min.toFixed(2)} at index ${minIndex}, max: $${max.toFixed(2)} at index ${maxIndex}`);
}

// ===== MAIN CHART HANDLER =====
function setRangeWithData(period, ticker) {
  if (!ticker) {
    console.error('No ticker provided');
    return;
  }
  
  // 🔥 RESET CACHE when changing ticker/period
  weeklyPredictionData = null;
  weeklyHistoricalData = null;
  currentDayIndex = 4;
  
  const svgEl = document.getElementById("lineChart");
  const slider = document.getElementById("chartSlider");
  const vGuide = document.getElementById("vGuide");
  
  // Show loading
  svgEl.innerHTML = `
    <text x="150" y="60" text-anchor="middle" fill="#999" font-size="12">
      Loading data...
    </text>
  `;
  
  if (period === '1W') {
    // Show UI elements for 1W
    showMetricsAndDate();
    hideExplanationBlock();
    if (slider) slider.style.display = 'block';
    if (vGuide) vGuide.style.display = 'block';
    
    // Load weekly data with predictions and interactive slider
    Promise.all([
      loadWeeklyHistoricalData(ticker),
      loadWeeklyPredictionData(ticker)
    ]).then(([histData, predData]) => {
      if (histData && predData) {
        console.log(`🔍 DEBUG - Historical data for ${ticker}:`, histData.prices);
        console.log(`🔍 DEBUG - Prediction data for ${ticker}:`, predData.prices);
        
        document.getElementById("startLabel").textContent = histData.dates[0];
        document.getElementById("endLabel").textContent = histData.dates[histData.dates.length - 1];
        
        drawWeeklyComparisonChart(svgEl, histData, predData);
        
        currentDayIndex = 4;
        updateDisplayValues(currentDayIndex, ticker);
        
        // 🆕 NOUVEAU : Mettre à jour les flèches après updateDisplayValues
        setTimeout(() => {
          // Récupérer les valeurs actuellement affichées
          const predChangeText = document.getElementById("predChange").textContent;
          const realChangeText = document.getElementById("realPriceChange").textContent;
          
          console.log("🔄 1W Period - Current displayed values:");
          console.log("predChangeText:", predChangeText);
          console.log("realChangeText:", realChangeText);
          
          // Extraire les valeurs numériques (enlever +, -, %)
          const predValue = parseFloat(predChangeText.replace(/[+%]/g, ''));
          const realValue = parseFloat(realChangeText.replace(/[+%]/g, ''));
          
          console.log("🔄 Parsed values - pred:", predValue, "real:", realValue);
          
          // Mettre à jour les classes des pills
          updatePillClasses(predValue, realValue);
        }, 100); // Petit délai pour s'assurer que updateDisplayValues a fini
        
        setupWeeklySlider(ticker);
      } else {
        svgEl.innerHTML = `
          <text x="150" y="60" text-anchor="middle" fill="#ff4444" font-size="12">
            Error loading weekly data
          </text>
        `;
      }
    });
    
  } else {
    // Hide UI elements for 1M/1Y and show explanation
    hideMetricsAndDate();
    showExplanationBlock();
    if (slider) slider.style.display = 'none';
    if (vGuide) vGuide.style.display = 'none';
    
    // Simple historical data loading for 1M/1Y
    loadHistoricalData(ticker, period).then(data => {
      if (data) {
        // TODO: You'll want to load predicted data too for 1M/1Y later
        // and modify drawStaticChart to handle 2 curves
        drawStaticChart(svgEl, data);
        
        // Update date labels if available
        if (data.date_labels && data.date_labels.length >= 2) {
          document.getElementById("startLabel").textContent = data.date_labels[0];
          document.getElementById("endLabel").textContent = data.date_labels[data.date_labels.length - 1];
        }
        
        // 🆕 NOUVEAU : Pour 1M/1Y, on peut réinitialiser les flèches ou les cacher
        // car il n'y a pas de données de prédiction
        console.log("🔄 Non-weekly period:", period, "- hiding or resetting pills");
        
        // Option 1: Cacher les flèches pour 1M/1Y
        const predChangeElement = document.getElementById("predChange");
        const realPriceChangeElement = document.getElementById("realPriceChange");
        if (predChangeElement) predChangeElement.className = "pill prediction";
        if (realPriceChangeElement) realPriceChangeElement.className = "pill real";
        
        // Option 2: Ou utiliser les valeurs statiques initiales si disponibles
        // updatePillClasses(initialPredValue, initialRealValue);
        
      } else {
        svgEl.innerHTML = `
          <text x="150" y="60" text-anchor="middle" fill="#ff4444" font-size="12">
            Error loading data
          </text>
        `;
      }
    });
  }
}

// ===== Load prediction data from API =====
async function loadPredictionData(ticker, date = null) {
  try {
    console.log(`📊 Loading prediction data for ${ticker}...`);
    
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
      console.error(`⚠ API Error: ${data.error}`);
      showErrorState(data.error);
    }
    
  } catch (error) {
    console.error('⚠ Network error:', error);
    showErrorState('Network error while loading prediction data');
  }
}


// Nouvelle fonction séparée pour mettre à jour les pills
function updatePillClasses(predChangeValue, realChangeValue) {
  console.log("🔄 UPDATING PILLS:");
  console.log("predChangeValue:", predChangeValue, "type:", typeof predChangeValue);
  console.log("realChangeValue:", realChangeValue, "type:", typeof realChangeValue);
  
  const predChangeElement = document.getElementById("predChange");
  const realPriceChangeElement = document.getElementById("realPriceChange");
  
  if (!predChangeElement || !realPriceChangeElement) {
    console.error("❌ Pills elements not found!");
    return;
  }
  
  // Convertir en nombres pour être sûr
  const predParsed = parseFloat(predChangeValue);
  const realParsed = parseFloat(realChangeValue);
  
  // Test des conditions
  const predIsUp = predParsed >= 0;
  const realIsUp = realParsed >= 0;
  
  console.log("predIsUp:", predIsUp, "realIsUp:", realIsUp);
  
  // Mettre à jour predChange
  predChangeElement.className = "pill prediction";
  predChangeElement.classList.add(predIsUp ? "up" : "down");
  
  // Mettre à jour realPriceChange  
  realPriceChangeElement.className = "pill real";
  realPriceChangeElement.classList.add(realIsUp ? "up" : "down");
  
  console.log("✅ Pills updated - pred:", predChangeElement.className, "real:", realPriceChangeElement.className);
}

// Fonction displayPredictionData modifiée
async function displayPredictionData(prediction) {
  // Update header info
  document.getElementById("companyName").textContent = prediction.name;
  document.getElementById("tickerSymbol").textContent = prediction.ticker;
     
  // Logo validation and fallback
  const validLogoUrl = await getValidLogoUrl(prediction.logo_url, prediction.ticker);
  const logoElement = document.getElementById("companyLogo");
  logoElement.src = validLogoUrl;
  logoElement.alt = prediction.name;
  logoElement.setAttribute('onerror', "this.src='/static/images/logos/default.png'");
     
  // Format date nicely
  const dateObj = new Date(prediction.date + 'T00:00:00');
  const formattedDate = dateObj.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  });
  document.getElementById("dateChip").textContent = formattedDate;
   
  // Initial static values (will be replaced by dynamic values for 1W)
  const { difference, difference_pct, predicted_price, predicted_change, real_price, real_change } = prediction;
     
  document.getElementById("diffVal").textContent = `${Math.abs(difference).toFixed(1)}`;
  document.getElementById("diffChange").textContent = `${difference_pct >= 0 ? '+' : ''}${difference_pct.toFixed(1)}%`;
   
  document.getElementById("predVal").textContent = `${predicted_price}`;
  document.getElementById("predChange").textContent = `${predicted_change >= 0 ? "+" : ""}${predicted_change.toFixed(1)}%`;
    
  document.getElementById("realVal").textContent = `${real_price}`;
  document.getElementById("realPriceChange").textContent = `${real_change >= 0 ? "+" : ""}${real_change.toFixed(1)}%`;
    
  // Utiliser la nouvelle fonction pour les pills
  updatePillClasses(predicted_change, real_change);
     
  // Set up chart (default to 1W)
  const ticker = prediction.ticker;
  setRangeWithData("1W", ticker);
     
  // Add event listeners for range buttons
  document.querySelectorAll(".range-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".range-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
             
      const period = btn.dataset.range;
      setRangeWithData(period, ticker);
    });
  });
     
  console.log("📈 Prediction data displayed");
}

function showLoadingState() {
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
  document.getElementById("companyName").textContent = 'Error loading data';
  document.getElementById("companyName").style.color = '#ff4444';
  console.error("Error state:", errorMessage);
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
  
  const urlParams = new URLSearchParams(window.location.search);
  const ticker = (urlParams.get("ticker") || "AAPL").toUpperCase();
  const date = urlParams.get("date");
  
  console.log(`🎯 Loading prediction for: ${ticker}${date ? ` on ${date}` : ''}`);
  
  loadStocksForSearch();
  initializeSearch();
  loadPredictionData(ticker, date);
  initializeTutorial();
  
  console.log("✅ Prediction Detail page initialized");
});