let started = false;

window.addEventListener('beforeunload', (event) => {
    if (started) {
        event.preventDefault();
        event.returnValue = ''; 
    }
});

window.addEventListener('unload', () => {
    if (started) {
        fetch('/chat/quiz/quit', {
            method: 'GET'
        });

        navigator.sendBeacon('/chat/quiz/quit');
    }
});

document.addEventListener("DOMContentLoaded", () => {
    const question = document.getElementById("question");
    const analysis = document.getElementById("analysis");
    const supplement = document.getElementById("supplement");
    const answerInput = document.getElementById("answer");
    const finishButton = document.getElementById("finish");
    const player = document.getElementById("player")

    const STATE = {
        START: 'start',
        CONFIRM: 'confirm',
        NEXT: 'next',
        END: 'end'
    }

    var idx = -1;
    var cur_state = STATE.START;
    var marked = false;
    var cur_data = {}

    const loading_icon = document.createElement("img");
    loading_icon.src = "/static/imgs/circle-loading-2.gif";
    loading_icon.id = "loading";

    async function render_task() {
        try {
            const response = await fetch("/chat/quiz/card", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({idx: idx})
            });
            const data = await response.json();
            if (!response.ok) {
                throw data.error;
            }
            cur_data = data;
            if (data.type === "intro") {
                question.innerText = data.props.content;
                analysis.innerText = ""
                answerInput.style.display = "none";
                cur_state = STATE.NEXT;
            }
            else if (data.type === "learn") {
                question.innerText = data.props.abstract;
                analysis.innerText = data.props.content;
                for (let url in data.props.images) {
                    const img = document.createElement('img');
                    img.src = data.props.images[url];
                    
                    img.style.cssText = `
                        padding: 4px;
                        margin: 8px;
                        border: 1px solid #e0e0e0;
                        border-radius: 6px;
                        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
                        display: block;
                        max-width: 100%;
                    `;
                    
                    supplement.appendChild(img);
                }
                answerInput.style.display = "none";
                cur_state = STATE.NEXT;
            }
            else if (data.type === "question") {
                question.innerText = data.props.question;
                if (!marked) {
                    analysis.innerText = "";
                }
                answerInput.style.display = "block";
                if (data.props.type === "ListeningQuestion") {
                    content = data.props.solution;
                    voice = data.props.voice;
                    finishButton.disabled = true;
                    finishButton.textContent = "";
                    finishButton.appendChild(loading_icon);
                    try {
                        const response = await fetch("/chat/quiz/play", {
                            method: "POST",
                            headers: {
                                "Content-Type": "application/json",
                            },
                            body: JSON.stringify({content: content, t: 2, voice: voice})
                        });
                        if (response.ok) {
                            const audioBlob = await response.blob();
                            const audioUrl = URL.createObjectURL(audioBlob);
                            player.src = audioUrl;
                            player.play();
                        }
                    } catch (error) {
                        console.log(error)
                    }
                    finishButton.disabled = false;
                    finishButton.removeChild(loading_icon);
                }
            }
            else if (data.type === "end") {
                question.innerText = "Congratulations! You've completed this learning task.";
                analysis.innerText = "Click the button below to close this page and wait for Clara to analyze your results.";
                answerInput.style.display = "none";
                cur_state = STATE.END;
            }

            if (cur_state === STATE.START) {
                finishButton.innerText = "I am ready";
            }
            else if (cur_state === STATE.NEXT) {
                finishButton.innerText = "Next ➡️";
            }
            else if (cur_state === STATE.CONFIRM) {
                finishButton.innerText = "Confirm ✅";
            }
            else if (cur_state === STATE.END) {
                finishButton.innerText = "Finished ✔️";
            }
        } catch (error) {
            console.log(error);
        }
    }

    async function finish() {
        if (cur_state === STATE.START) {
            try {
                const response = await fetch("/chat/quiz/start", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify({name: taskName, type: taskType})
                });
                const data = await response.json();
                if (!response.ok) {
                    throw data.error
                }
                idx += 1;
                cur_state = STATE.CONFIRM;
                started = true;
            } catch (error) {}
        }
        else if (cur_state === STATE.NEXT) {
            idx += 1;
            cur_state = STATE.CONFIRM;
            marked = false;
            answerInput.value = "";
            supplement.innerHTML = "";
        }
        else if (cur_state === STATE.CONFIRM) {
            answer = answerInput.value.trim();
            cur_state = STATE.NEXT;
            try {
                const answer_data = {
                    q_type: cur_data.props.type,
                    idx: cur_data.props.idx,
                    answer: answer
                }
                finishButton.disabled = true;
                finishButton.textContent = "";
                finishButton.appendChild(loading_icon);
                const response = await fetch("/chat/quiz/mark", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify(answer_data)
                });
                const data = await response.json();
                if (!response.ok) {
                    throw data.error;
                }
                analysis.innerText = `🙆✅: ${data.solution}\n` +
                    `🙇🏻➡️: ${answer}\n` +
                    `score: [${data.score.toFixed(2)} / 1.00]\n` +
                    `${data.analysis}`;
                finishButton.disabled = false;
                marked = true;
            } catch (error) {
                console.log(error);
            }
        }
        else if (cur_state === STATE.END) {
            started = false;
            fetch("/chat/quiz/end", {
                method: "GET",
                keepalive: true
            });
            setTimeout(() => {
                window.close();
            }, 100);
        }

        render_task();
    }

    finishButton.addEventListener("click", finish)
    
    answerInput.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
            event.preventDefault();
            finishButton.click();
        }
    });
});