// 显示确认弹窗
function showConfirm() {
  document.getElementById("confirmOverlay").style.display = "flex";
}

// 关闭弹窗
function closeConfirm() {
  document.getElementById("confirmOverlay").style.display = "none";
}

// 退出课程
function quitLesson() {
  window.location.href = "home.html"; // ✅ 可按需修改跳转页面
}

