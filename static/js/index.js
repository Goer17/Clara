document.addEventListener("DOMContentLoaded", () => {

    // markdown
    // md_container = document.getElementsByClassName("markdown")
    // md_container.innerHTML = marked(md_container.innerText)

    const messagesDiv = document.getElementById("messages");
    const input = document.getElementById("input");
    const sendButton = document.getElementById("send");
    const resetButton = document.getElementById("reset")

    function renderChatHistory(history) {
        history.forEach(({ role, content }) => {
            if ((role === "user" || role == "assistant") && content.trim() !== "") {
                appendMessage(role, content);
            }
        });
    }
    renderChatHistory(chatHistory);

    function appendMessage(role, text) {
        text = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>');
        const messageDiv = document.createElement("div");
        messageDiv.classList.add("message", role);
    
        const div = document.createElement("div");
        div.classList.add("ctx")
        div.innerHTML = text;
        messageDiv.appendChild(div);
    
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

    const wordInput = document.getElementById("word");
    const searchButton = document.getElementById("search");
    const addButton = document.getElementById("add");
    const deleteButton = document.getElementById("delete");
    const result = document.getElementById("result");
    var cur_word = "";
    var cur_content = "";

    async function search() {
        const word = wordInput.value.trim().toLowerCase();
        request = {word : word}
        try {
            appendMessage("assistant", `Searching "${word}" in dictionary...`)
            const response = await fetch("/chat/dictionary", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(request)
            });
            const data = await response.json()
            if (!response.ok) {
                throw data.error
            }
            result.querySelector("#abstract h2").textContent = word
            result.querySelector("pre").textContent = data.reply
            result.style.display = ""
            cur_word = word
            cur_content = data.reply
            appendMessage("assistant", `✅ Completed!\n${word}\n${data.reply}`)
        } catch (error) {
            appendMessage("assistant", error)
        }
    }

    async function add_word() {
        request = {
            profile: {
                label: "unfamiliar_word",
                abstract: cur_word,
                content: cur_content,
                familiarity: 0
            },
            n_rela: 5
        }
        try {
            const w = cur_word
            appendMessage("assistant", `Adding "${cur_word}" to the vocabulary notebook...`)
            const response = await fetch("/chat/remember", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(request)
            });
            if (!response.ok) {
                throw data.error
            }
            appendMessage("assistant", `✅ "${w}" was added to the vocabulary notebook.`)
        } catch (error) {
            console.log(error)
        }
    }

    function clear() {
        result.querySelector("#abstract h2").textContent = ""
        result.querySelector("pre").textContent = ""
        result.style.display = "none"
        cur_word = ""
        cur_content = ""
    }

    searchButton.addEventListener("click", search)
    addButton.addEventListener("click", add_word)
    deleteButton.addEventListener("click", clear)

    wordInput.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
            event.preventDefault();
            search();
        }
    });
});
