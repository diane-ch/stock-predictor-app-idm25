// ../../static/js/detail.js
document.addEventListener('DOMContentLoaded', function () {
  (function () {
    const params = new URLSearchParams(window.location.search);
    const ticker = (params.get("ticker") || "").toUpperCase();

    const IMG = {
      up: "../../static/images/up-logo.png",
      down: "../../static/images/down-logo.png",
      confidence: "../../static/images/confidenceicon.png",
      logos: {
        AAPL: "../../static/images/apple-logo.png",
        TSLA: "../../static/images/tesla-logo.png",
        AMZN: "../../static/images/amazon.png",
        SOFI: "../../static/images/sofi.png",
        MSFT: "../../static/images/microsoft-logo.png",
      },
    };

    const STOCKS = {
      AAPL: { name:"Apple Inc.",  price:211.16, changePct:+2.30, confidence:8.2, factorsCount:10, reasons:["Strong iPhone sales momentum","High cash reserves","Ecosystem stickiness"] },
      TSLA: { name:"Tesla Inc.",  price:313.51, changePct:-1.80, confidence:7.5, factorsCount:10, reasons:["EV market leadership","Energy storage growth","Software/ADAS optionality"] },
      AMZN: { name:"Amazon",      price:225.02, changePct:+1.20, confidence:8.0, factorsCount:10, reasons:["Retail operating leverage","Ads monetization","AWS margin uptick"] },
      SOFI: { name:"SoFi Technologies", price:21.20, changePct:+3.64, confidence:7.0, factorsCount:10, reasons:["Member growth","Improving unit economics","Product cross-sell"] },
      MSFT: { name:"Microsoft Corp.",   price:351.30, changePct:-0.70, confidence:7.9, factorsCount:10, reasons:["Azure consumption growth","Copilot attach","Operating discipline"] },
    };

    const data = STOCKS[ticker] || STOCKS["AAPL"];

    // 顶部置信度
    const headerConfVal = document.querySelector(".header-confidence .confidence-value");
    if (headerConfVal) headerConfVal.textContent = `${data.confidence.toFixed(1)}/10`;

    // 中间：logo/名称/ticker
    const logoMain = document.getElementById("logoMain");
    if (logoMain) logoMain.src = IMG.logos[ticker] || IMG.logos["AAPL"];

    const nameEl = document.querySelector(".brand-name");
    if (nameEl) nameEl.textContent = data.name;

    const tickerEl = document.querySelector(".brand-ticker");
    if (tickerEl) tickerEl.textContent = ticker;

    // 价格 + 涨跌
    const priceEl = document.getElementById("price");
    if (priceEl) priceEl.textContent = `${data.price.toFixed(2)} USD`;

    const changeEl = document.getElementById("change");
    if (changeEl) {
      changeEl.classList.remove("positive","negative");
      const isUp = data.changePct >= 0;
      changeEl.classList.add(isUp ? "positive" : "negative");
      const arrow = changeEl.querySelector(".arrow-icon");
      if (arrow) arrow.src = isUp ? IMG.up : IMG.down;
      const pctText = `${isUp ? "+" : ""}${data.changePct.toFixed(2)}% `;
      if (changeEl.firstChild && changeEl.firstChild.nodeType === 3) {
        changeEl.firstChild.nodeValue = pctText;
      } else {
        changeEl.insertBefore(document.createTextNode(pctText), changeEl.firstChild);
      }
    }

    // 推荐理由
    const reasonList = document.querySelector(".reason-list");
    if (reasonList) {
      reasonList.innerHTML = "";
      data.reasons.forEach(txt => {
        const div = document.createElement("div");
        div.className = "reason-chip";
        div.textContent = txt;
        reasonList.appendChild(div);
      });
    }

    // 底部 factors
    const aiText = document.querySelector(".ai-text");
    if (aiText) aiText.textContent = `AI Analysis Based on ${data.factorsCount} Factors`;
  })();
});
