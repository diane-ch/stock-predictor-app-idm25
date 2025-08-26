let currentModuleId = null;
let currentLessonId = null;

function toggleMenu() {
  const menu = document.getElementById('logoutMenu');
  menu.style.display = menu.style.display === 'block' ? 'none' : 'block';
}

function logout() {
  // Redirect to Flask logout route
  window.location.href = "{{ url_for('auth.logout') if url_for }}";
}

// Close menu when clicking outside (from original learn.js)
document.addEventListener("click", function(event) {
  const menu = document.getElementById("logoutMenu");
  const icon = document.querySelector(".menu-icon");
  if (menu && icon && !menu.contains(event.target) && !icon.contains(event.target)) {
    menu.style.display = "none";
  }
});

function openVideoCard(moduleId, lessonId) {
  currentModuleId = moduleId;
  currentLessonId = lessonId;
  
  // Fetch lesson details via AJAX
  fetch(`/education/lesson/${moduleId}/${lessonId}/preview`)
    .then(response => response.json())
    .then(data => {
      document.getElementById('popupCategory').textContent = `${data.module.emoji} ${data.module.title}`;
      document.getElementById('popupTime').textContent = `${data.lesson.duration} min`;
      document.getElementById('popupTitle').textContent = data.lesson.title;
      document.getElementById('popupDesc').textContent = data.lesson.description;
      
      // FIX: Use Flask template syntax properly (this will be processed by Flask)
      let imagePreview = 'default.png';
      
      if (data.lesson && data.lesson['image-preview']) {
        imagePreview = data.lesson['image-preview'];
      } else if (data.lesson && data.lesson.image_preview) {
        imagePreview = data.lesson.image_preview;
      }
      
      const imageSrc = window.STATIC_LESSONS_URL + imagePreview;
      document.getElementById('popupImage').src = imageSrc;
      
      document.getElementById('videoPopup').style.display = 'flex';
    })
    .catch(error => {
      console.error('Error fetching lesson data:', error);
      // Fallback data
      document.getElementById('popupCategory').textContent = "🌱 Foundations";
      document.getElementById('popupTime').textContent = "8 min";
      document.getElementById('popupTitle').textContent = "Loading...";
      document.getElementById('popupDesc').textContent = "Loading lesson details...";
      document.getElementById('videoPopup').style.display = 'flex';
    });
}

function startLesson() {
  if (currentModuleId && currentLessonId) {
    // Close the popup first
    document.getElementById('videoPopup').style.display = 'none';
    // Navigate to lesson start
    window.location.href = `/education/lesson/${currentModuleId}/${currentLessonId}/start`;
  } else {
    alert('Please select a lesson first.');
  }
}

function addTransition() {
  localStorage.setItem("transitionDirection", "up");
}

// Make functions global for onclick handlers
window.openVideoCard = openVideoCard;
window.startLesson = startLesson;
window.toggleMenu = toggleMenu;
window.logout = logout;

function updateFoundationsIcon() {
  // Utiliser le bon sélecteur pour trouver le texte de progression
  const progressElement = document.querySelector('.progress-text');
  
  if (!progressElement) {
    console.log('❌ Element .progress-text introuvable');
    return;
  }
  
  const progressText = progressElement.textContent;
  console.log('Texte de progression trouvé:', progressText);
  
  const match = progressText.match(/(\d+)\/(\d+)/);
  
  if (match) {
    const completed = parseInt(match[1]);
    console.log('Leçons complétées:', completed);
    
    // Si au moins 1 leçon complétée, changer l'icône
    if (completed >= 1) {
      const foundationsIcon = document.querySelector('[data-module-id="foundations"]');
      if (foundationsIcon) {
        const currentSrc = foundationsIcon.src;
        console.log('Source actuelle:', currentSrc);
        
        if (currentSrc.includes('baby_foundations.png')) {
          foundationsIcon.src = currentSrc.replace('baby_foundations.png', 'toddler_foundations.png');
          console.log('✅ Icône foundations mise à jour !');
        } else {
          console.log('ℹ️ Icône déjà mise à jour ou nom différent');
        }
      } else {
        console.log('❌ Icône foundations introuvable');
      }
    } else {
      console.log('ℹ️ Pas encore de leçon complétée');
    }
  } else {
    console.log('❌ Format de progression non reconnu');
  }
}

// Close popup when clicking outside
document.addEventListener('DOMContentLoaded', function() {
  console.log('🚀 DOM chargé, initialisation...');
  
  const popup = document.getElementById('videoPopup');
  if (popup) {
    popup.addEventListener('click', function(e) {
      if (e.target === this) {
        this.style.display = 'none';
      }
    });
  }

  // Appeler la fonction de mise à jour de l'icône
  updateFoundationsIcon();

  // Tutorial modal functionality
  const tutorialBtn = document.getElementById("tutorialBtn");
  const tutorialModal = document.getElementById("tutorialModal");
  const tutorialCloseBtn = document.getElementById("tutorialCloseBtn");
  const logoutMenu = document.getElementById("logoutMenu");

  if (!tutorialBtn || !tutorialModal || !tutorialCloseBtn) {
    console.log('❌ Éléments tutorial introuvables');
    return;
  }

  // 打开：显示为 flex 才能触发弹窗的居中布局
  tutorialBtn.addEventListener("click", function (e) {
    e.stopPropagation();
    tutorialModal.style.display = "flex";
    if (logoutMenu) logoutMenu.style.display = "none";
  });

  // 关闭按钮
  tutorialCloseBtn.addEventListener("click", function () {
    tutorialModal.style.display = "none";
  });

  // 点击遮罩关闭（只在点到遮罩本身时关闭）
  tutorialModal.addEventListener("click", function (e) {
    if (e.target === tutorialModal) {
      tutorialModal.style.display = "none";
    }
  });
});