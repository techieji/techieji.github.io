// JavaScript for interactive effects
document.addEventListener('DOMContentLoaded', function() {
    const themeToggle = document.getElementById('themeToggle');
    const body = document.body;
    
    // Check for saved theme preference, default to dark
    const currentTheme = localStorage.getItem('theme') || 'dark';
    if (currentTheme === 'dark') {
        body.classList.add('dark-mode');
        themeToggle.textContent = 'light';
    } else {
        themeToggle.textContent = 'dark';
    }
    
    // Toggle theme
    themeToggle.addEventListener('click', function() {
        body.classList.toggle('dark-mode');
        
        if (body.classList.contains('dark-mode')) {
            themeToggle.textContent = 'light';
            localStorage.setItem('theme', 'dark');
        } else {
            themeToggle.textContent = 'dark';
            localStorage.setItem('theme', 'light');
        }
    });
});