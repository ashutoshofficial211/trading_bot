const form = document.querySelector("#order-form");
const orderTypeSelect = document.querySelector("#order-type");
const priceField = document.querySelector("#price-field");
const priceInput = document.querySelector("#price");
const priceNote = document.querySelector("#price-note");
const submitButton = document.querySelector("#submit-button");
const formStatus = document.querySelector("#form-status");
const statusBanner = document.querySelector("#status-banner");
const requestSummary = document.querySelector("#request-summary");
const orderResponse = document.querySelector("#order-response");
const errorMessage = document.querySelector("#error-message");

function setPriceFieldState() {
    const isLimit = orderTypeSelect.value === "LIMIT";
    priceInput.disabled = !isLimit;
    priceInput.required = isLimit;
    priceField.classList.toggle("field-hidden", !isLimit);
    if (!isLimit) {
        priceInput.value = "";
    }
    priceNote.textContent = isLimit
        ? "Price is required for LIMIT orders and will be sent to Binance."
        : "Price is disabled for MARKET orders and will not be sent.";
}

function setBannerState(kind, message) {
    statusBanner.className = `status-banner status-${kind}`;
    statusBanner.textContent = message;
}

function renderSummary(target, fields, emptyText) {
    if (!fields || fields.length === 0) {
        target.className = "summary-list empty-state";
        target.innerHTML = `<li>${emptyText}</li>`;
        return;
    }

    target.className = "summary-list";
    target.innerHTML = fields
        .map(
            (field) => `
                <li>
                    <span class="summary-label">${field.label}</span>
                    <span class="summary-value">${field.value}</span>
                </li>
            `,
        )
        .join("");
}

async function submitOrder(event) {
    event.preventDefault();

    const payload = {
        symbol: document.querySelector("#symbol").value,
        side: document.querySelector("#side").value,
        orderType: orderTypeSelect.value,
        quantity: document.querySelector("#quantity").value,
        price: orderTypeSelect.value === "LIMIT" ? priceInput.value : null,
    };

    submitButton.disabled = true;
    formStatus.textContent = "Submitting order...";
    setBannerState("loading", "Submitting order to Binance Demo Trading...");
    errorMessage.textContent = "Waiting for response...";

    try {
        const response = await fetch("/api/orders", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(payload),
        });

        const data = await parseApiResponse(response);
        renderSummary(
            requestSummary,
            data.requestSummary,
            "Submit a form to see the normalized request.",
        );
        renderSummary(orderResponse, data.orderResponse, "No response yet.");

        if (data.finalStatus === "SUCCESS") {
            setBannerState("success", "Order accepted by Binance Demo Trading.");
            errorMessage.textContent = "No errors.";
        } else {
            setBannerState("failed", "Order submission failed.");
            errorMessage.textContent = data.errorMessage || "An unknown error occurred.";
        }

        formStatus.textContent =
            data.finalStatus === "SUCCESS"
                ? "Order completed."
                : "Review the error details and try again.";
    } catch (error) {
        handleFrontendError(error);
        console.error(error);
    } finally {
        submitButton.disabled = false;
    }
}

async function parseApiResponse(response) {
    const responseText = await response.text();
    const contentType = response.headers.get("content-type") || "";

    if (contentType.includes("application/json")) {
        const data = JSON.parse(responseText);
        if (!response.ok && !data.errorMessage) {
            data.errorMessage = `The backend returned HTTP ${response.status}.`;
        }
        return data;
    }

    throw new Error(
        response.ok
            ? "The backend returned an unexpected non-JSON response."
            : `The backend returned HTTP ${response.status}. ${responseText.slice(0, 240)}`
    );
}

function handleFrontendError(error) {
    renderSummary(
        requestSummary,
        [],
        "Submit a form to see the normalized request.",
    );
    renderSummary(orderResponse, [], "No response yet.");

    const message = error instanceof Error ? error.message : String(error);
    const isConnectionError =
        message.includes("Failed to fetch") ||
        message.includes("NetworkError") ||
        message.includes("Load failed");

    if (isConnectionError) {
        setBannerState("failed", "The local UI could not reach the Python backend.");
        errorMessage.textContent =
            "The browser could not reach the local server. Make sure python web.py is running.";
        formStatus.textContent = "Connection failed.";
        return;
    }

    setBannerState("failed", "The Python backend returned an error.");
    errorMessage.textContent = message;
    formStatus.textContent = "Backend error.";
}

orderTypeSelect.addEventListener("change", setPriceFieldState);
form.addEventListener("submit", submitOrder);
setPriceFieldState();
