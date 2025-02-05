document.addEventListener("DOMContentLoaded", () => {

    const messagesDiv = document.getElementById("messages");
    const input = document.getElementById("input");
    const sendButton = document.getElementById("send");
    const resetButton = document.getElementById("reset")

    const loading_icon = document.createElement("img");
    loading_icon.src = "/static/imgs/circle-loading-3.gif";
    loading_icon.id = "loading";

    const loading_icon_a = document.createElement("img");
    loading_icon_a.src = "/static/imgs/circle-loading-1.gif";
    loading_icon_a.id = "loading";

    const loading_icon_s = document.createElement("img");
    loading_icon_s.src = "/static/imgs/line-loading-2.gif";
    loading_icon_s.id = "loading";


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

        sendButton.disabled = true;
        sendButton.textContent = "";
        sendButton.appendChild(loading_icon_s);

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

        sendButton.removeChild(loading_icon_s);
        sendButton.textContent = "send";
        sendButton.disabled = false;
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
            sendButton.click();
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
        if (!word) return;
        request = {word : word}
        
        searchButton.disabled = true;
        const span = searchButton.querySelector("span");
        searchButton.replaceChild(loading_icon, span);

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

        searchButton.replaceChild(span, loading_icon);
        searchButton.disabled = false;

        addButton.textContent = "+";
        addButton.disabled = false;
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
        addButton.textContent = "";
        addButton.appendChild(loading_icon_a);
        addButton.disabled = true;
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
        addButton.removeChild(loading_icon_a);
        addButton.textContent = "✅";
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
            searchButton.click();
        }
    });
});
