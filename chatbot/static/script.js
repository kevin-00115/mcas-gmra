document.addEventListener("DOMContentLoaded", () => {
    const chatBox = document.querySelector('#chat-box');
    const messageInput = document.querySelector('#user-input');
    const sendButton = document.querySelector('#send-btn');
    const newChatButton = document.querySelector('#new-chat-btn');

    function appendMessage(message, type) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', type);
        messageDiv.textContent = message;
        chatBox.appendChild(messageDiv);
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    async function sendMessage() {
        console.log("Send button clicked");
        const message = messageInput.value;
        if (message.trim() !== '') {
            appendMessage(message, 'user-message');
            messageInput.value = '';

            try {
                console.log("Sending request to /chat");
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ message: message })
                });

                console.log("Response received");
                const data = await response.json();
                console.log("Response data:", data);
                appendMessage(data.response, 'bot-message');
            } catch (error) {
                console.error('Error:', error);
                appendMessage('Sorry, something went wrong!', 'error-message');
            }
        } else {
            console.log("Message input is empty");
        }
    }

    sendButton.addEventListener('click', () => {
        console.log("Send button event listener triggered");
        sendMessage();
    });

    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            console.log("Enter key pressed");
            sendMessage();
        }
    });

    if (newChatButton) {
        newChatButton.addEventListener('click', () => {
            console.log("New chat button clicked");
            startNewConversation();
        });
    }

    // Load chat history when page loads
    async function loadChatHistory() {
        try {
            const response = await fetch('/history');
            const messages = await response.json();
            
            // Clear existing messages
            chatBox.innerHTML = '';
            
            // Display each message from history
            messages.forEach(msg => {
                appendMessage(msg.message, `${msg.sender}-message`);
            });
        } catch (error) {
            console.error('Error loading chat history:', error);
        }
    }

    loadChatHistory();
});