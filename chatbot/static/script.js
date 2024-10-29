document.addEventListener("DOMContentLoaded", () => {
    const chatBox = document.querySelector('#chat-box');
    const messageInput = document.querySelector('#user-input');
    const sendButton = document.querySelector('#send-btn');

    function appendMessage(message, type) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', type);
        messageDiv.textContent = message;
        chatBox.appendChild(messageDiv);
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    async function sendMessage() {
        const message = messageInput.value;
        if (message.trim() !== '') {
            // Display user message
            appendMessage(message, 'user-message');
            messageInput.value = '';

            try {
                // Send message to backend
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ message: message })
                });
                
                const data = await response.json();
                
                // Display bot's response
                appendMessage(data.response, 'bot-message');
            } catch (error) {
                console.error('Error:', error);
                appendMessage('Sorry, something went wrong!', 'error-message');
            }
        }
    }

    sendButton.addEventListener('click', sendMessage);
    
    // Add Enter key support
    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
});
