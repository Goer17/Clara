document.addEventListener("DOMContentLoaded", () => {
    const preButton = document.getElementById("pre");
    const nextButton = document.getElementById("next");
    const curPage = document.getElementById("cur-page");
    const wordList = document.getElementById("word-list")

    const pageLine = 12;

    var pageIndex = 0;

    async function render() {
        try {
            response = await fetch("/chat/query", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(
                    {
                        profile: {
                            label: "unfamiliar_word"
                        },
                        order: ["familiarity", "DESC"],
                        skip: pageLine * pageIndex,
                        limit: pageLine
                    }
                )
            });
            data = (await response.json())[0];
            if (data.length === 0) {
                pageIndex -= 1;
                nextButton.disabled = true;
                return;
            }
            while (wordList.firstChild) {
                wordList.removeChild(wordList.firstChild);
            }
            for (let i = 0; i < data.length; i++) {
                const div = document.createElement("div");
                div.classList.add("word");
    
                const spanW = document.createElement("span");
                spanW.classList.add("w");
                spanW.textContent = data[i].abstract;
    
                const spanF = document.createElement("span");
                spanF.classList.add("f");
                spanF.innerHTML = "familiarity:&emsp;" + parseInt(data[i].familiarity);
                
                div.appendChild(spanW);
                div.appendChild(spanF);
    
                wordList.appendChild(div);
            }
            nextButton.disabled = false;
            if (pageIndex === 0) {
                preButton.disabled = true;
            }
            else if (pageIndex > 0) {
                preButton.disabled = false;
            }
            curPage.textContent = "- " + (pageIndex + 1) + " -";
        } catch (error) {}
    }
    render();

    async function next_page() {
        pageIndex += 1;
        render();
    }

    async function pre_page() {
        pageIndex -= 1;
        render();
    }

    nextButton.addEventListener("click", next_page);
    preButton.addEventListener("click", pre_page);
});