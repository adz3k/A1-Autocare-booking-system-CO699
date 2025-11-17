document.addEventListener("DOMContentLoaded", function () {

    // Helper function to show validation result
    function validateField(element, condition) {
        if (condition) {
            element.classList.remove("is-invalid");
            element.classList.add("is-valid");
        } else {
            element.classList.remove("is-valid");
            element.classList.add("is-invalid");
        }
    }

    // EMAIL VALIDATION
    const emailField = document.getElementById("email");
    emailField.addEventListener("input", function () {
        const value = emailField.value.trim();
        const isValid = value.includes("@") && value.includes(".") && value.length > 5;
        validateField(emailField, isValid);
    });

    // NAME VALIDATION
    const nameField = document.getElementById("name");
    nameField.addEventListener("input", function () {
        validateField(nameField, nameField.value.trim().length >= 2);
    });

    // VEHICLE VALIDATION
    const vehicleField = document.getElementById("vehicle");
    vehicleField.addEventListener("input", function () {
        validateField(vehicleField, vehicleField.value.trim().length >= 2);
    });

    // POSTCODE VALIDATION
    const postcodeField = document.getElementById("postcode");
    postcodeField.addEventListener("input", function () {
        const formatted = postcodeField.value.replace(/\s+/g, "");
        validateField(postcodeField, formatted.length >= 5);
    });

    // MAKE VALIDATION
    const makeField = document.getElementById("make");
    makeField.addEventListener("change", function () {
        validateField(makeField, makeField.value !== "");
    });

    // SERVICE VALIDATION
    const serviceField = document.getElementById("service");
    serviceField.addEventListener("change", function () {
        validateField(serviceField, serviceField.value !== "");
    });

    // DATE VALIDATION (no past dates)
    const dateField = document.getElementById("date");
    dateField.addEventListener("input", function () {
        const today = new Date().toISOString().split("T")[0];
        validateField(dateField, dateField.value >= today);
    });

    // TIME VALIDATION
    const timeField = document.getElementById("booking_time");
    timeField.addEventListener("input", function () {
        validateField(timeField, timeField.value !== "");
    });

});
