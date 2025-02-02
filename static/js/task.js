window.addEventListener('beforeunload', (event) => {
    event.preventDefault();
    event.returnValue = '';
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
                    analysis.innerText = ""
                }
                answerInput.style.display = "block";
            }

            if (cur_state == STATE.START) {
                finishButton.innerText = "I am ready"
            }
            else if (cur_state == STATE.NEXT) {
                finishButton.innerText = "Next ➡️"
            }
            else if (cur_state == STATE.CONFIRM) {
                finishButton.innerText = "Confirm ✅"
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
            } catch (error) {}
        }
        else if (cur_state === STATE.NEXT) {
            idx += 1;
            cur_state = STATE.CONFIRM;
            marked = false;
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
                console.log(data);
                analysis.innerText = `Right answer: ${data.solution}\n` +
                    `Your answer: ${answer}\n` +
                    `Score: ${data.score}\n` +
                    `${data.analysis}`;
                marked = true;
            } catch (error) {
                console.log(error);
            }
        }

        render_task();
    }

    finishButton.addEventListener("click", finish)
});