document.addEventListener("DOMContentLoaded", () => {
    const messagesDiv = document.getElementById("messages");
    const input = document.getElementById("input");
    const sendButton = document.getElementById("send");
    const resetButton = document.getElementById("reset")

    function renderChatHistory(history) {
        history.forEach(({ role, content }) => {
            if (role === "user" || role == "assistant") {
                appendMessage(role, content);
            }
        });
    }
    renderChatHistory(chatHistory);

    function appendMessage(role, text) {
        const messageDiv = document.createElement("div");
        messageDiv.classList.add("message", role);
    
        const pre = document.createElement("pre");
        pre.textContent = text;
        messageDiv.appendChild(pre);
    
        messagesDiv.appendChild(messageDiv);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }

    async function sendMessage() {
        const message = input.value.trim();
        if (!message) return;

        appendMessage("user", message);
        input.value = "";

        try {
            const response = await fetch("/chat/v1", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ message }),
            });

            const data = await response.json();
            console.log(data)
            if (data.reply) {
                appendMessage("assistant", data.reply);
            } else {
                appendMessage("assistant", "Error: " + (data.error || "Unknown error"));
            }
        } catch (error) {
            appendMessage("assistant", "Error: " + error.message);
        }
    }

    async function resetMessage() {
        try {
            const response = await fetch("/chat/reset", {
                method: "POST"
            });
            if (response.ok) {
                messagesDiv.innerHTML = ""; 
            } else {
                const errorData = await response.json();
                appendMessage("assistant", "Error: " + (errorData.error || "Failed to reset chat."));
            }
        } catch (error) {
            appendMessage("assistant", "Error: " + error.message);
        }
    }

    sendButton.addEventListener("click", sendMessage);
    resetButton.addEventListener("click", resetMessage);

    input.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
            event.preventDefault();
            sendMessage();
        }
    });
});
