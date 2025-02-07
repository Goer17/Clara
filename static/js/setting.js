document.addEventListener("DOMContentLoaded", () => {
    const modelSelector = document.getElementById("model-select");
    const slider = document.getElementById("temperature-slider");
    const temperatureValue = document.getElementById("temperature-value");
    const saveButton = document.getElementById("save");

    slider.addEventListener("input", () => {
        temperatureValue.textContent = slider.value;
    });
});
