document.addEventListener('DOMContentLoaded', function() {
  const container = document.querySelector('.stars');
  if (!container) return;
  const initial = parseInt(container.dataset.initial || '0', 10);
  const input = document.getElementById('rating-input');
  for (let i = 1; i <= 10; i++) {
    const star = document.createElement('span');
    star.textContent = '★';
    star.className = 'star' + (i <= initial ? ' filled' : '');
    star.dataset.value = i;
    star.addEventListener('click', () => {
      const val = parseInt(star.dataset.value, 10);
      input.value = val;
      [...container.children].forEach((s, idx) => {
        s.classList.toggle('filled', idx < val);
      });
    });
    container.appendChild(star);
  }
});