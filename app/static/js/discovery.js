document.addEventListener("DOMContentLoaded", function () {
  const dateListEl = document.querySelector('.date-list');
  const countdownEl = document.querySelector('.countdown-text');

  const today = new Date();
  today.setHours(0, 0, 0, 0); // 清除时间部分

  function getDates() {
    const base = new Date(today);
    const dates = [];
    for (let i = -3; i <= 0; i++) { // 显示今天和前面三天
      const d = new Date(base);
      d.setDate(base.getDate() + i);
      dates.push(d);
    }
    return dates;
  }

  let fullDates = getDates();          // 四个日期
  let selectedDate = fullDates[3];     // 默认选中今天（最后一个）

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

    const items = document.querySelectorAll('.date-item[data-date]');
    items.forEach(item => {
      item.addEventListener('click', () => {
        const clickedDate = new Date(item.dataset.date);
        selectedDate = clickedDate;
        renderDates(); // 重新渲染
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

  renderDates();
  updateCountdown();
});

// 菜单功能：显示/隐藏
function toggleMenu() {
  const menu = document.getElementById("logoutMenu");
  menu.style.display = (menu.style.display === "block") ? "none" : "block";
}

// 登出提示
function logout() {
  alert("Logging out...");
  // 实际登出逻辑可在此实现
}

// 点击空白关闭菜单
document.addEventListener("click", function(event) {
  const menu = document.getElementById("logoutMenu");
  const icon = document.querySelector(".menu-icon");
  if (menu && icon && !menu.contains(event.target) && !icon.contains(event.target)) {
    menu.style.display = "none";
  }
});

// 页面切换动画方向设置
function addTransition() {
  localStorage.setItem("transitionDirection", "up");
}
