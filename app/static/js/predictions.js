document.addEventListener("DOMContentLoaded", function () {
  // 股票列表
  /*const stocks = [
    "3M (MMM)", "Amazon (AMZN)", "Apple (AAPL)", "Bank of America (BAC)",
    "Boeing (BA)", "Caterpillar (CAT)", "Cisco Systems (CSCO)", "Coca-Cola (KO)",
    "Disney (DIS)", "Goldman Sachs (GS)", "Home Depot (HD)", "Intel (INTC)",
    "International Business Machines (IBM)"
  ];*/

  const listContainer = document.getElementById("stockList");
  const searchInput = document.getElementById("searchInput");

  let stocks = []; // Will be populated from JSON file

  // Load stocks from API endpoints
  async function loadStocks() {
    try {
      const response = await fetch('/api/stocks-list');
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const result = await response.json();
      
      if (!result.success) {
        throw new Error(result.error || 'Failed to load stocks');
      }
      
      const stocksData = result.stocks;
      
      // Transform JSON data to display format: "Company Name (TICKER)"
      stocks = stocksData.map(stock => `${stock.name} (${stock.ticker})`);
      
      // Initial render after loading data
      renderList(stocks);
    } catch (error) {
      console.error('Error loading stocks:', error);
      // Fallback to hardcoded list if JSON fails to load
      stocks = [
        "3M Company (MMM)", "Amazon.com Inc. (AMZN)", "Apple Inc. (AAPL)", 
        "Bank of America Corp. (BAC)", "The Boeing Company (BA)", 
        "Caterpillar Inc. (CAT)", "Cisco Systems, Inc. (CSCO)", 
        "The Coca-Cola Company (KO)", "The Walt Disney Company (DIS)", 
        "The Goldman Sachs Group, Inc. (GS)", "The Home Depot, Inc. (HD)", 
        "Intel Corporation (INTC)", "International Business Machines Corporation (IBM)"
      ];
      renderList(stocks);
    }
  }


  // 渲染股票列表
  function renderList(filtered) {
    listContainer.innerHTML = "";

  if (filtered.length === 0) {
    const noResultDiv = document.createElement("div");
    noResultDiv.className = "no-result";

    const noResultImg = document.createElement("img");
    noResultImg.src = "../../static/images/noresult.png"; // 用你的图标路径
    noResultImg.alt = "No result";

    const noResultText1 = document.createElement("p");
    noResultText1.textContent = "Whoops!";
    noResultText1.classList.add("no-result-title");

    const noResultText2 = document.createElement("p");
    noResultText2.textContent = "We couldn’t find the stock you’re looking for.";
    noResultText2.classList.add("no-result-sub");

    const noResultText3 = document.createElement("p");
    noResultText3.textContent = "Try another one.";
    noResultText3.classList.add("no-result-sub");

    noResultDiv.appendChild(noResultImg);
    noResultDiv.appendChild(noResultText1);
    noResultDiv.appendChild(noResultText2);
    noResultDiv.appendChild(noResultText3);
    listContainer.appendChild(noResultDiv);
    return;
  }


  filtered.forEach(stock => {
    const item = document.createElement("div");
    item.className = "stock-item";
    item.textContent = stock;

    item.addEventListener("click", () => {
      const ticker = /\(([^)]+)\)/.exec(stock)?.[1] || "AAPL";
      const baseUrl = window.PREDICTION_DETAIL_URL || '/prediction-detail';
      window.location.href = `${baseUrl}?ticker=${encodeURIComponent(ticker)}`;
    });

    listContainer.appendChild(item);
  });
}


  // 初始渲染
  //renderList(stocks);

  // 搜索过滤 Search functionality
  searchInput.addEventListener("input", () => {
    const query = searchInput.value.toLowerCase();
    const filtered = stocks.filter(stock => stock.toLowerCase().includes(query));
    renderList(filtered);
  });

  // Load stocks when page loads
  loadStocks();
});

// 右上角菜单逻辑
function toggleMenu() {
  const menu = document.getElementById("logoutMenu");
  menu.style.display = (menu.style.display === "block") ? "none" : "block";
}

function logout() {
  alert("Logging out...");
}

// 点击外部关闭菜单
document.addEventListener("click", function (event) {
  const menu = document.getElementById("logoutMenu");
  const icon = document.querySelector(".menu-icon");
  if (!menu.contains(event.target) && !icon.contains(event.target)) {
    menu.style.display = "none";
  }
});

