function goBackToDiscovery() {
  window.location.href = "discovery.html";
}

const data = {
  AAPL: {
    name: "Apple Inc.",
    logo: "../../static/images/apple-logo.png",
    price: "211.16 USD",
    change: "+1.9%",
    changeIcon: "../../static/images/up-logo.png",
    changePositive: true,
    confidence: "high",
    features: ["Feature 1: iPhone 16 Release", "Feature 2: Services Growth", "Feature 3: Strong Cash Flow"]
  },
  TSLA: {
    name: "Tesla Inc.",
    logo: "../../static/images/tesla-logo.png",
    price: "313.51 USD",
    change: "-1.8%",
    changeIcon: "../../static/images/down-logo.png",
    changePositive: false,
    confidence: "mid",
    features: ["Feature 1: EV Market Slowing", "Feature 2: Robotaxi Plans", "Feature 3: FSD Beta Expansion"]
  },
  AMZN: {
    name: "Amazon",
    logo: "../../static/images/amazon.png",
    price: "225.02 USD",
    change: "+1.2%",
    changeIcon: "../../static/images/up-logo.png",
    changePositive: true,
    confidence: "high",
    features: ["Feature 1: AWS Growth", "Feature 2: Ads Business", "Feature 3: AI Retail Integration"]
  },
  SOFI: {
    name: "SoFi Technologies",
    logo: "../../static/images/sofi.png",
    price: "21.20 USD",
    change: "+3.64%",
    changeIcon: "../../static/images/up-logo.png",
    changePositive: true,
    confidence: "mid",
    features: ["Feature 1: Lending Expansion", "Feature 2: New Licenses", "Feature 3: Brand Awareness"]
  },
  MSFT: {
    name: "Microsoft Corp.",
    logo: "../../static/images/microsoft-logo.png",
    price: "351.30 USD",
    change: "-0.7%",
    changeIcon: "../../static/images/down-logo.png",
    changePositive: false,
    confidence: "low",
    features: ["Feature 1: Copilot Integration", "Feature 2: Azure Market Share", "Feature 3: Gaming Growth"]
  }
};

// 读取 URL 参数中的 ticker
const urlParams = new URLSearchParams(window.location.search);
const ticker = urlParams.get("ticker");

if (ticker && data[ticker]) {
  const stock = data[ticker];

  document.getElementById("stock-name").textContent = stock.name;
  document.getElementById("stock-ticker").textContent = ticker;
  document.getElementById("stock-logo").src = stock.logo;

  document.getElementById("stock-price").textContent = stock.price;
  document.getElementById("change-text").textContent = stock.change;
  document.getElementById("change-icon").src = stock.changeIcon;

  const changeEl = document.getElementById("stock-change");
  changeEl.classList.add(stock.changePositive ? "positive" : "negative");

  const dot = document.getElementById("confidence-dot");
  dot.classList.add(stock.confidence); // 添加 high / mid / low
  document.getElementById("confidence-text").textContent =
    stock.confidence.charAt(0).toUpperCase() + stock.confidence.slice(1) + " Confidence";

  const featureList = document.getElementById("feature-list");
  stock.features.forEach(f => {
    const div = document.createElement("div");
    div.className = "feature-item";
    div.textContent = f;
    featureList.appendChild(div);
  });
} else {
  document.getElementById("stock-name").textContent = "Unknown";
  document.getElementById("confidence-text").textContent = "Unknown Confidence";
}
// detail.js

window.addEventListener("DOMContentLoaded", () => {
  const transitionDirection = localStorage.getItem("transitionDirection");
  const container = document.querySelector(".page-transition");
  
  if (transitionDirection === "up") {
    // 表示是从 discovery 页面来的，动画从下往上（上升）
    container.classList.add("enter-from-top");  // ✅ 上升动画
  } else {
    // 表示是返回 discovery，动画从上往下（下降）
    container.classList.add("enter-from-bottom");  // ✅ 下降动画
  }

  localStorage.removeItem("transitionDirection");
});
