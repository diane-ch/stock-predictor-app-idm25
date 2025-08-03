function toggleMenu() {
  const menu = document.getElementById("logoutMenu");
  menu.style.display = (menu.style.display === "block") ? "none" : "block";
}

function logout() {
  alert("Logging out...");
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

let currentLessonUrl = "";

window.addEventListener("DOMContentLoaded", function () {
  // 点击星星/圆圈打开弹窗
  window.openVideoCard = function (index) {
    // 你可以根据 index 设置不同内容
    if (index === 2) {
      document.getElementById("popupCategory").textContent = "🔍 Analysis";
      document.getElementById("popupTime").textContent = "8 min";
      document.getElementById("popupTitle").textContent = "What is Risk vs Return?";
      document.getElementById("popupDesc").textContent = "This is a little explanation of what the module is about.";
      document.getElementById("popupImage").src = "../../static/images/lesson-placeholder.png";
      currentLessonUrl = "../auth/lesson1.html";
    }

    document.getElementById("videoPopup").style.display = "flex";
  };

  // 点击按钮跳转
  window.startLesson = function () {
    if (currentLessonUrl) {
      window.location.href = currentLessonUrl;
    }
  };

  // 点击遮罩关闭弹窗
  const popup = document.getElementById("videoPopup");
  popup.addEventListener("click", function (e) {
    if (e.target.id === "videoPopup") {
      popup.style.display = "none";
    }
  });
});



