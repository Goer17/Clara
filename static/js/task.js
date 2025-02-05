let started = false;

window.addEventListener('beforeunload', (event) => {
    event.preventDefault();
    event.returnValue = ''; 
});

window.addEventListener('unload', () => {
    if (started) {
        fetch('/chat/quiz/quit', {
            method: 'GET',
        });

        navigator.sendBeacon('/chat/quiz/quit');
    }
});

document.addEventListener("DOMContentLoaded", () => {
    const question = document.getElementById("question");
    const analysis = document.getElementById("analysis");
    const answerInput = document.getElementById("answer");
    const finishButton = document.getElementById("finish");
    
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
                    finishButton.disabled = true;
                    finishButton.textContent = "";
                    finishButton.appendChild(loading_icon);
                    try {
                        await fetch("/chat/quiz/play", {
                            method: "POST",
                            headers: {
                                "Content-Type": "application/json",
                            },
                            body: JSON.stringify({content: content, t: 2})
                        });
                    } catch (error) {
                        console.log(error)
                    }
                    finishButton.disabled = false;
                    finishButton.removeChild(loading_icon);
                }
            }

            if (cur_state == STATE.START) {
                finishButton.innerText = "I am ready";
            }
            else if (cur_state == STATE.NEXT) {
                finishButton.innerText = "Next ➡️";
            }
            else if (cur_state == STATE.CONFIRM) {
                finishButton.innerText = "Confirm ✅";
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
                    body: JSON.stringify({name: taskName})
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
                analysis.innerText = `Right answer: ${data.solution}\n` +
                    `Your answer: ${answer}\n` +
                    `Score: ${data.score}\n` +
                    `${data.analysis}`;
                finishButton.disabled = false;
                marked = true;
            } catch (error) {
                console.log(error);
            }
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