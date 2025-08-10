// ===== 顶部菜单 =====
function toggleMenu() {
  const menu = document.getElementById("logoutMenu");
  menu.style.display = (menu.style.display === "block") ? "none" : "block";
}
function logout() { alert("Logging out..."); }
document.addEventListener("click", (e) => {
  const menu = document.getElementById("logoutMenu");
  const icon = document.querySelector(".menu-icon");
  if (menu && icon && !menu.contains(e.target) && !icon.contains(e.target)) {
    menu.style.display = "none";
  }
});

// ===== 各股票的演示数据（你可替换为真实数据） =====
const TICKER_MAP = {
  MMM: {
    name: "3M Company",
    logo: "../../static/images/mmm_logo.png",
    date: "Jul 31, 2025",
    series: {
      "1W": { dates: ["Jul 22","Jul 31"], values: [98, 101] },
      "1M": { dates: ["Jul 1","Jul 31"], values: [95, 101] },
      "1Y": { dates: ["Aug '24","Jul '25"], values: [88, 101] },
    },
    metrics: { diff: 1.2, diffPct: 1.2, pred: 101, predPct: 1.5, real: 100, realPct: -0.3 }
  },

  AMZN: {
    name: "Amazon.com Inc.",
    logo: "../../static/images/amazon_logo.png",
    date: "Jul 31, 2025",
    series: {
      "1W": { dates: ["Jul 22","Jul 31"], values: [179, 186] },
      "1M": { dates: ["Jul 1","Jul 31"], values: [171, 186] },
      "1Y": { dates: ["Aug '24","Jul '25"], values: [132, 186] },
    },
    metrics: { diff: 1.2, diffPct: 0.6, pred: 186, predPct: 1.4, real: 185, realPct: -0.4 }
  },

  AAPL: {
    name: "Apple Inc.",
    logo: "../../static/images/apple-logo.png",
    date: "Jul 31, 2025",
    series: {
      "1W": { dates: ["Jul 22","Jul 31"], values: [205, 213] },
      "1M": { dates: ["Jul 1","Jul 31"], values: [198, 213] },
      "1Y": { dates: ["Aug '24","Jul '25"], values: [176, 213] },
    },
    metrics: { diff: 2.0, diffPct: 1.1, pred: 213, predPct: 1.8, real: 211, realPct: -2.9 }
  },

  BAC: {
    name: "Bank of America Corp.",
    logo: "../../static/images/bac_logo.png",
    date: "Jul 31, 2025",
    series: {
      "1W": { dates: ["Jul 22","Jul 31"], values: [39.8, 40.9] },
      "1M": { dates: ["Jul 1","Jul 31"], values: [38.5, 40.9] },
      "1Y": { dates: ["Aug '24","Jul '25"], values: [30.2, 40.9] },
    },
    metrics: { diff: 0.3, diffPct: 0.7, pred: 40.9, predPct: 1.2, real: 40.6, realPct: -0.5 }
  },

  BA: {
    name: "The Boeing Company",
    logo: "../../static/images/ba_logo.png",
    date: "Jul 31, 2025",
    series: {
      "1W": { dates: ["Jul 22","Jul 31"], values: [180, 187] },
      "1M": { dates: ["Jul 1","Jul 31"], values: [172, 187] },
      "1Y": { dates: ["Aug '24","Jul '25"], values: [145, 187] },
    },
    metrics: { diff: 2.1, diffPct: 1.1, pred: 187, predPct: 2.2, real: 185, realPct: -0.8 }
  },

  CAT: {
    name: "Caterpillar Inc.",
    logo: "../../static/images/cat_logo.png",
    date: "Jul 31, 2025",
    series: {
      "1W": { dates: ["Jul 22","Jul 31"], values: [325, 334] },
      "1M": { dates: ["Jul 1","Jul 31"], values: [312, 334] },
      "1Y": { dates: ["Aug '24","Jul '25"], values: [258, 334] },
    },
    metrics: { diff: 1.8, diffPct: 0.5, pred: 334, predPct: 1.6, real: 332, realPct: -0.3 }
  },

  CSCO: {
    name: "Cisco Systems, Inc.",
    logo: "../../static/images/csco_logo.png",
    date: "Jul 31, 2025",
    series: {
      "1W": { dates: ["Jul 22","Jul 31"], values: [48.2, 49.5] },
      "1M": { dates: ["Jul 1","Jul 31"], values: [47.0, 49.5] },
      "1Y": { dates: ["Aug '24","Jul '25"], values: [41.8, 49.5] },
    },
    metrics: { diff: 0.4, diffPct: 0.8, pred: 49.5, predPct: 1.5, real: 49.1, realPct: -0.4 }
  },

  KO: {
    name: "The Coca-Cola Company",
    logo: "../../static/images/ko_logo.png",
    date: "Jul 31, 2025",
    series: {
      "1W": { dates: ["Jul 22","Jul 31"], values: [61.0, 62.2] },
      "1M": { dates: ["Jul 1","Jul 31"], values: [59.8, 62.2] },
      "1Y": { dates: ["Aug '24","Jul '25"], values: [54.6, 62.2] },
    },
    metrics: { diff: 0.3, diffPct: 0.5, pred: 62.2, predPct: 1.0, real: 61.9, realPct: -0.3 }
  },

  DIS: {
    name: "The Walt Disney Company",
    logo: "../../static/images/dis_logo.png",
    date: "Jul 31, 2025",
    series: {
      "1W": { dates: ["Jul 22","Jul 31"], values: [95, 101] },
      "1M": { dates: ["Jul 1","Jul 31"], values: [92, 101] },
      "1Y": { dates: ["Aug '24","Jul '25"], values: [82, 101] },
    },
    metrics: { diff: 0.9, diffPct: 0.9, pred: 101, predPct: 1.8, real: 100, realPct: -0.5 }
  },

  GS: {
    name: "The Goldman Sachs Group, Inc.",
    logo: "../../static/images/gs_logo.png",
    date: "Jul 31, 2025",
    series: {
      "1W": { dates: ["Jul 22","Jul 31"], values: [421, 432] },
      "1M": { dates: ["Jul 1","Jul 31"], values: [405, 432] },
      "1Y": { dates: ["Aug '24","Jul '25"], values: [342, 432] },
    },
    metrics: { diff: 3.2, diffPct: 0.8, pred: 432, predPct: 1.9, real: 428, realPct: -0.6 }
  },

  HD: {
    name: "The Home Depot, Inc.",
    logo: "../../static/images/hd_logo.png",
    date: "Jul 31, 2025",
    series: {
      "1W": { dates: ["Jul 22","Jul 31"], values: [330, 338] },
      "1M": { dates: ["Jul 1","Jul 31"], values: [316, 338] },
      "1Y": { dates: ["Aug '24","Jul '25"], values: [282, 338] },
    },
    metrics: { diff: 1.6, diffPct: 0.5, pred: 338, predPct: 1.7, real: 336, realPct: -0.4 }
  },

  INTC: {
    name: "Intel Corporation",
    logo: "../../static/images/intc_logo.png",
    date: "Jul 31, 2025",
    series: {
      "1W": { dates: ["Jul 22","Jul 31"], values: [33.2, 34.5] },
      "1M": { dates: ["Jul 1","Jul 31"], values: [31.8, 34.5] },
      "1Y": { dates: ["Aug '24","Jul '25"], values: [28.4, 34.5] },
    },
    metrics: { diff: 0.4, diffPct: 1.2, pred: 34.5, predPct: 2.0, real: 34.1, realPct: -0.8 }
  },

  IBM: {
    name: "International Business Machines Corporation",
    logo: "../../static/images/ibm_logo.png",
    date: "Jul 31, 2025",
    series: {
      "1W": { dates: ["Jul 22","Jul 31"], values: [183, 188] },
      "1M": { dates: ["Jul 1","Jul 31"], values: [176, 188] },
      "1Y": { dates: ["Aug '24","Jul '25"], values: [150, 188] },
    },
    metrics: { diff: 1.1, diffPct: 0.6, pred: 188, predPct: 1.4, real: 187, realPct: -0.3 }
  }
};


// ===== 画线 & 切换区间 =====
function drawLine(svgEl, data) {
  const w = 300, h = 120, pad = 10;
  svgEl.setAttribute("viewBox", `0 0 ${w} ${h}`);
  svgEl.innerHTML = "";

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
  const { dates, values } = series[range];
  document.getElementById("startLabel").textContent = dates[0];
  document.getElementById("endLabel").textContent = dates[dates.length - 1];
  drawLine(document.getElementById("lineChart"), values);
}

// ===== 初始化页面 =====
document.addEventListener("DOMContentLoaded", () => {
  // 1) 读参数
  const ticker = (new URLSearchParams(location.search).get("ticker") || "AAPL").toUpperCase();
  const info = TICKER_MAP[ticker] || TICKER_MAP["AAPL"];

  // 2) 写入头部信息
  document.getElementById("companyName").textContent = info.name;
  document.getElementById("tickerSymbol").textContent = ticker;
  document.getElementById("companyLogo").src = info.logo;
  document.getElementById("companyLogo").alt = info.name;
  document.getElementById("dateChip").textContent = info.date;

  // 3) 写入指标
  const { diff, diffPct, pred, predPct, real, realPct } = info.metrics;
  document.getElementById("diffVal").textContent = `$${diff.toFixed(1)}`;
  document.getElementById("diffChange").textContent = `${diffPct.toFixed(1)}%`;

  document.getElementById("predVal").textContent = `$${pred.toFixed(0)}`;
  document.getElementById("predChange").textContent = `${predPct >= 0 ? "+" : ""}${predPct.toFixed(1)}%`;
  document.getElementById("predChange").className = `pill ${predPct >= 0 ? "up" : "down"}`;

  document.getElementById("realVal").textContent = `$${real.toFixed(0)}`;
  document.getElementById("realPriceChange").textContent = `${realPct >= 0 ? "+" : ""}${realPct.toFixed(1)}%`;
  document.getElementById("realPriceChange").className = `pill ${realPct >= 0 ? "up" : "down"}`;

  // 4) 默认区间 & 切换
  setRange("1W", info.series);
  document.querySelectorAll(".range-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".range-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      setRange(btn.dataset.range, info.series);
    });
  });
});
  // ===== 滑轨拖拽 =====
  const svg = document.getElementById("lineChart");
  const track = document.getElementById("chartTrack");
  const knob = document.getElementById("chartKnob");
  const vGuide = document.getElementById("vGuide");
  const chartWrap = document.querySelector(".chart-wrap");

  // 当前百分比（0~1）
  let pct = 0.5;

  function clamp(x, min=0, max=1){ return Math.max(min, Math.min(max, x)); }

  function placeByPercent(p) {
    // 放置 knob：相对 track 的宽度
    const rect = track.getBoundingClientRect();
    const x = rect.left + p * rect.width;

    knob.style.left = `${p * 100}%`;
    knob.setAttribute("aria-valuenow", Math.round(p * 100));

    // 放置 vGuide：相对 svg 的宽度定位
    const svgRect = svg.getBoundingClientRect();
    const wrapRect = chartWrap.getBoundingClientRect();
    const guideLeft = svgRect.left - wrapRect.left + p * svgRect.width;
    vGuide.style.left = `${guideLeft}px`;
  }

  function pointerToPercent(clientX){
    const rect = track.getBoundingClientRect();
    return clamp((clientX - rect.left) / rect.width);
  }

  // 点击轨道也能跳转
  track.addEventListener("pointerdown", (e) => {
    track.setPointerCapture(e.pointerId);
    pct = pointerToPercent(e.clientX);
    placeByPercent(pct);
  });

  // 拖拽圆钮
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

  // 键盘无障碍：左右键微调、Home/End
  knob.addEventListener("keydown", (e) => {
    const step = 0.02;
    if (e.key === "ArrowLeft") { pct = clamp(pct - step); placeByPercent(pct); }
    if (e.key === "ArrowRight") { pct = clamp(pct + step); placeByPercent(pct); }
    if (e.key === "Home") { pct = 0; placeByPercent(pct); }
    if (e.key === "End") { pct = 1; placeByPercent(pct); }
  });

  // 窗口变化时重算定位
  window.addEventListener("resize", () => placeByPercent(pct));

  // 初始化一次
  placeByPercent(pct);
