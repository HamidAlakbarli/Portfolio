document.addEventListener("DOMContentLoaded", function() {
    const navbarToggle = document.querySelector(".navbar-toggle");
    const navbar = document.querySelector(".navbar");

    navbarToggle.addEventListener("click", function() {
        navbar.classList.toggle("navbar-open");
    });
});
document.querySelector('.burger-menu').addEventListener('click', function() {
    document.querySelector('.navbar').classList.toggle('active');
});

function toggleChat() {
    var chatContainer = document.getElementById('chat-container');
    if (chatContainer.style.display === 'block') {
        chatContainer.style.display = 'none';
    } else {
        chatContainer.style.display = 'block';
    }
}

function toggleMenu() {
    document.querySelector('.navbar').classList.toggle('active');
    document.querySelector('.burger-menu').classList.toggle('active');
}