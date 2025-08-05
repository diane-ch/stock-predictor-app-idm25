document.addEventListener("DOMContentLoaded", function () {
  const dateListEl = document.querySelector('.date-list');
  const countdownEl = document.querySelector('.countdown-text');

  const today = new Date();
  let selectedIndex = 2; // 初始默认中间位置为今天

  function getDates() {
    const base = new Date();
    const dates = [];
    for (let i = -4; i <= 1; i++) { // dates span from 4 days ago to 1 day ahead (-4, +1)
      const d = new Date(base);
      d.setDate(base.getDate() + i);
      dates.push(d);
    }
    return dates;
  }


  let fullDates = getDates(); // 初始化生成7个日期
  let selectedDate = fullDates.find(d => d.toDateString() === today.toDateString());
console.log("Dates to render:", fullDates);

  function renderDates() {
  const centerIndex = fullDates.findIndex(d => d.toDateString() === selectedDate.toDateString());

  let start = Math.max(0, centerIndex - 2);
  let end = start + 4;

  // 修正索引范围
  if (end >= fullDates.length) {
    end = fullDates.length - 1;
    start = Math.max(0, end - 4);
  }

  let displayDates = fullDates.slice(start, end + 1); // 正常日期

  const willShowCountdown = end === fullDates.length - 1;

  // 如果最后一个日期是 fullDates 的最后，就加一个“预测块”
  if (willShowCountdown && displayDates.length < 5) {
    displayDates.push("PREDICTION");
  }

  dateListEl.innerHTML = displayDates
    .map(date => {
      if (date === "PREDICTION") {
        const now = new Date();
        const next8am = new Date(now);
        next8am.setDate(now.getHours() >= 8 ? now.getDate() + 1 : now.getDate());
        next8am.setHours(8, 0, 0, 0);

        const msLeft = next8am - now;
        const hoursLeft = Math.ceil(msLeft / (1000 * 60 * 60));

        return `
          <span class="date-item" style="background-color:#ec7845; color:white;">
            <strong>${hoursLeft}h</strong><small>left</small>
          </span>`;
      }

      const day = date.getDate();
      const month = date.toLocaleString('en-US', { month: 'short' });
      const isSelected = date.toDateString() === selectedDate.toDateString();
      return `
        <span class="date-item ${isSelected ? 'selected' : ''}" data-date="${date.toISOString()}">
          ${day}<br><small>${month}</small>
        </span>`;
    })
    .join('');

  // 点击事件只绑定真实日期
const items = document.querySelectorAll('.date-item[data-date]');
items.forEach(item => {
  item.addEventListener('click', () => {
    const clickedDate = new Date(item.dataset.date);
    selectedDate = clickedDate;
    renderDates(); // 重新渲染日期
    fetchStocksForDate(clickedDate); // ✅ 加载新股票数据
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

    countdownEl.innerHTML = `<strong>${hoursLeft} hours</strong><br>until prediction`;
  }

  renderDates();
  updateCountdown();
});


function toggleMenu() {
  const menu = document.getElementById("logoutMenu");
  menu.style.display = (menu.style.display === "block") ? "none" : "block";
}

function logout() {
  alert("Logging out...");
  // 你可以在这里添加实际登出逻辑
}

// 可选：点击其他地方关闭菜单
document.addEventListener("click", function(event) {
  const menu = document.getElementById("logoutMenu");
  const icon = document.querySelector(".menu-icon");
  if (!menu.contains(event.target) && !icon.contains(event.target)) {
    menu.style.display = "none";
  }
});
// discovery.js
function addTransition() {
  localStorage.setItem("transitionDirection", "up");
}


// New function to fetch stocks for a specific date
async function fetchStocksForDate(date) {
    const dateStr = date.toISOString().split('T')[0];
    
    try {
        // Show loading state
        const container = document.getElementById('stocks-container');
        container.innerHTML = '<div style="text-align: center; padding: 40px; color: #ccc;">Loading stocks...</div>';
        
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
        container.innerHTML = '<div style="text-align: center; padding: 40px; color: #ff4444;">Error loading stocks. Please try again.</div>';
    }
}

// Function to update stock cards display
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
