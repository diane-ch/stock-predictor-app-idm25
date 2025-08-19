// Quiz.js - Version corrigée sans conflits
// Les données viennent du template HTML via window.quizData

document.addEventListener('DOMContentLoaded', () => {
  // Check if we have quiz data from the template
  if (!window.quizData) {
    console.error('Quiz data not available');
    return;
  }

  const checkButton = document.querySelector('.quiz-submit');
  const feedbackBox = document.getElementById('feedback');
  const options = document.querySelectorAll('.quiz-option');
  
  if (!checkButton || !feedbackBox) {
    console.error('Quiz elements not found');
    return;
  }

  // Initially disable submit button
  checkButton.disabled = true;
  
  // Add click listeners to options
  options.forEach(option => {
    option.addEventListener('click', function() {
      // Remove selected class from all options
      options.forEach(opt => opt.classList.remove('selected'));
      
      // Add selected class to clicked option
      this.classList.add('selected');
      
      // Check the radio button
      const radio = this.querySelector('input[type="radio"]');
      if (radio) {
        radio.checked = true;
      }
      
      // Enable submit button
      checkButton.disabled = false;
    });
  });
  
  // Add click listener to check button
  checkButton.addEventListener('click', (e) => {
    e.preventDefault();
    checkAnswer();
  });
});

function showConfirm() {
  const overlay = document.getElementById('confirmOverlay');
  if (overlay) {
    overlay.style.display = 'flex';
  }
}

function closeConfirm() {
  const overlay = document.getElementById('confirmOverlay');
  if (overlay) {
    overlay.style.display = 'none';
  }
}

function quitLesson() {
  window.location.href = "/education/";
}

function checkAnswer() {
  if (!window.quizData) {
    console.error('Quiz data not available');
    return;
  }

  const selected = document.querySelector('input[name="answer"]:checked');
  if (!selected) return;

  const userAnswer = parseInt(selected.value);
  const correctAnswer = window.quizData.currentQuestion.correct_answer;
  const isCorrect = userAnswer === correctAnswer;

  const feedbackBox = document.getElementById('feedback');
  const header = document.getElementById('feedback-header');
  const explanation = document.getElementById('feedback-explanation');

  // Show feedback
  if (isCorrect) {
    feedbackBox.classList.remove('error');
    header.textContent = '🎉 Correct!';
    explanation.textContent = window.quizData.currentQuestion.explanation;
  } else {
    feedbackBox.classList.add('error');
    header.textContent = '🤔 Not quite right!';
    explanation.textContent = window.quizData.currentQuestion.explanation;
  }

  feedbackBox.classList.add('show');
}

function closeFeedback() {
  const feedbackBox = document.getElementById('feedback');
  if (feedbackBox) {
    feedbackBox.classList.remove('show');
    feedbackBox.classList.remove('error');
  }
  
  if (!window.quizData) return;
  
  // Soumettre la réponse au backend - UNE SEULE FOIS
  const selected = document.querySelector('input[name="answer"]:checked');
  if (!selected) return;
  
  const userAnswer = parseInt(selected.value);
  
  const form = document.createElement('form');
  form.method = 'POST';
  form.action = window.quizData.submitUrl;
  form.style.display = 'none';
  
  const input = document.createElement('input');
  input.type = 'hidden';
  input.name = 'answer';
  input.value = userAnswer;
  
  form.appendChild(input);
  document.body.appendChild(form);
  
  // Soumettre et laisser le backend gérer la redirection
  form.submit();
}

function finishQuiz() {
  // Cette fonction est seulement appelée depuis l'overlay de completion
  window.location.href = "/education/";
}

// Global functions
window.showConfirm = showConfirm;
window.closeConfirm = closeConfirm;
window.quitLesson = quitLesson;
window.checkAnswer = checkAnswer;
window.closeFeedback = closeFeedback;
window.finishQuiz = finishQuiz;