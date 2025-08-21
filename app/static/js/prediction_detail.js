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

// ===== Global data storage =====
let currentPredictionData = null;

// ===== Chart functionality =====
function drawLine(svgEl, data) {
  const w = 300, h = 120, pad = 10;
  svgEl.setAttribute("viewBox", `0 0 ${w} ${h}`);
  svgEl.innerHTML = "";

  if (!data || data.length === 0) return;

  const min = Math.min(...data), max = Math.max(...data);
  const range = max - min || 1;
  const stepX = (w - pad * 2) / (data.length - 1);

  const points = data.map((v, i) => {
    const x = pad + i * stepX;
    const y = h - pad - ((v - min) / range) * (h - pad * 2);
    return [x, y];
  });

  const d = points.map((p, i) => (i === 0 ? `M ${p[0]} ${p[1]}` : `L ${p[0]} ${p[1]}`)).join(" ");
  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  path.setAttribute("d", d);
  path.setAttribute("fill", "none");
  path.setAttribute("stroke", "#0aa07f");
  path.setAttribute("stroke-width", "2");
  svgEl.appendChild(path);
}

function setRange(range, series) {
  if (!series || !series[range]) {
    console.error(`No data for range: ${range}`);
    return;
  }
  
  const { dates, values } = series[range];
  document.getElementById("startLabel").textContent = dates[0] || "Start";
  document.getElementById("endLabel").textContent = dates[dates.length - 1] || "End";
  drawLine(document.getElementById("lineChart"), values);
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
  
  document.getElementById("diffVal").textContent = `$${Math.abs(difference).toFixed(1)}`;
  document.getElementById("diffChange").textContent = `${difference_pct >= 0 ? '+' : ''}${difference_pct.toFixed(1)}%`;

  document.getElementById("predVal").textContent = `$${predicted_price}`;
  document.getElementById("predChange").textContent = `${predicted_change >= 0 ? "+" : ""}${predicted_change.toFixed(1)}%`;
  document.getElementById("predChange").className = `pill ${predicted_change >= 0 ? "up" : "down"}`;

  document.getElementById("realVal").textContent = `$${real_price}`;
  document.getElementById("realPriceChange").textContent = `${real_change >= 0 ? "+" : ""}${real_change.toFixed(1)}%`;
  document.getElementById("realPriceChange").className = `pill ${real_change >= 0 ? "up" : "down"}`;

  // 3. Set up chart with default range
  if (prediction.series) {
    setRange("1W", prediction.series);
    
    // Add event listeners for range buttons
    document.querySelectorAll(".range-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".range-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        setRange(btn.dataset.range, prediction.series);
      });
    });
  }
  
  console.log("📈 Prediction data displayed successfully");
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
  
  // 2. Load prediction data
  loadPredictionData(ticker, date);
  
  // 3. Initialize other functionality
  initializeSlider();
  initializeTutorial();
  
  console.log("✅ Prediction Detail page initialized");
});