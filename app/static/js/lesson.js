// 显示确认弹窗
function showConfirm() {
  document.getElementById("confirmOverlay").style.display = "flex";
}

// 关闭弹窗
function closeConfirm() {
  document.getElementById("confirmOverlay").style.display = "none";
}

// 退出课程 - Pas de Jinja2 ici !
function quitLesson() {
  window.location.href = "/education/"; // URL statique
}

// Global functions
window.showConfirm = showConfirm;
window.closeConfirm = closeConfirm;
window.quitLesson = quitLesson;