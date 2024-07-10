document.addEventListener("DOMContentLoaded", function() {
    const chatContainer = document.getElementById('chat-container');
    const chatInput = document.getElementById('chat-input');
    const chatBox = document.getElementById('chat-box');
    let isChatOpened = false; // Flag to check if chat has been opened before

    window.toggleChat = function() {
        chatContainer.style.display = chatContainer.style.display === 'none' || chatContainer.style.display === '' ? 'flex' : 'none';
        if (chatContainer.style.display === 'flex' && !isChatOpened) {
            displayMessage('Hamid', "Hello, my name is Hamid. How can I help you?");
            isChatOpened = true; // Set the flag to true after the first opening
        }
    };

    window.sendMessage = async function() {
        const message = chatInput.value.trim();
        if (message === '') return;

        displayMessage('You', message);
        chatInput.value = '';

        const response = await fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ question: message })
        });
        const data = await response.json();
        displayMessage('Hamid', data.response);
    };

    window.checkEnter = function(event) {
        if (event.key === 'Enter') {
            sendMessage();
        }
    };

    function displayMessage(sender, message) {
        const messageElement = document.createElement('div');
        messageElement.textContent = `${sender}: ${message}`;
        messageElement.style.marginBottom = '10px'; // Add some space between messages
        chatBox.appendChild(messageElement);
        chatBox.scrollTop = chatBox.scrollHeight;
    }
});
