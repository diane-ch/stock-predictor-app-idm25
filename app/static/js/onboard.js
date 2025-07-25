document.addEventListener('DOMContentLoaded', function () {
  const btn = document.getElementById('nextBtn');
  if (!btn) return;

  btn.addEventListener('click', function () {

    const currentPage = window.location.pathname;
    const match = currentPage.match(/onboard(\d+)\.html/);

    if (match) {
      const currentNum = parseInt(match[1]);
      const nextNum = currentNum + 1;
      const nextPage = `onboard${nextNum}.html`;
      window.location.href = nextPage;
    } else {
      console.error('not onboard page');
    }
  });
});
