document.addEventListener("DOMContentLoaded", () => {
    const modelSelector = document.getElementById("model-select");
    const slider = document.getElementById("temperature-slider");
    const temperatureValue = document.getElementById("temperature-value");
    const saveButton = document.getElementById("save");

    slider.addEventListener("input", () => {
        temperatureValue.textContent = slider.value;
    });

    modelSelector.value = model;
    slider.value = temp;
    temperatureValue.textContent = temp.toFixed(2);

    saveButton.addEventListener("click", event => {
        event.preventDefault();
        try {
            fetch("/chat/setting", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    model: modelSelector.value,
                    temp: slider.value
                })
            })
        } catch (error) {
            console.log(error);
        }
    });
});
