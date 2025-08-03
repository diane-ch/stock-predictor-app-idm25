document.addEventListener('DOMContentLoaded', () => {
  const checkButton = document.querySelector('.quiz-submit');
  const feedbackBox = document.getElementById('feedback');
  const header = document.getElementById('feedback-header');
  const explanation = document.getElementById('feedback-explanation');

  checkButton.addEventListener('click', () => {
    const selected = document.querySelector('input[name="q1"]:checked');
    if (!selected) return;

    const isCorrect = selected.value === 'expensive1';

    if (isCorrect) {
      feedbackBox.classList.remove('error');
      header.textContent = '🎉 Correct!';
      explanation.textContent = 'P/E = Price ÷ Earnings = $50 ÷ $2 = 25. Since 25 is above our "expensive" threshold of 25, it\'s potentially expensive (though normal for growth companies).';
    } else {
      feedbackBox.classList.add('error');
      header.textContent = '🤔 Incorrect!';
      explanation.textContent = 'That answer is incorrect. Review how to calculate P/E = Price ÷ Earnings.';
    }

    feedbackBox.classList.add('show');
  });
});

function closeFeedback() {
  document.getElementById('feedback').classList.remove('show');
  document.getElementById('feedback').classList.remove('error');
}
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

function closeFeedback() {
  document.getElementById('feedback').classList.remove('show');
  // 显示完成弹窗
  document.getElementById('completionOverlay').style.display = 'flex';
}

function finishQuiz() {
  window.location.href = "home.html"; // ✅ 修改为完成后跳转页面
}
