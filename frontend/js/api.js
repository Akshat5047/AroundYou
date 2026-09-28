// ============================================================
// AROUND YOU - API CONFIGURATION
// ============================================================


// ============================================================
// BACKEND URL
// ============================================================

// Local development backend.
//
// Start it from the backend folder using:
//
// python -m uvicorn main:app --reload
//
// Uvicorn runs locally on port 8000.

const API_BASE =
    "http://127.0.0.1:8000";


// ============================================================
// POST REQUEST
// ============================================================

async function apiPost(
    path,
    body
) {

    const response = await fetch(
        API_BASE + path,
        {
            method: "POST",

            headers: {
                "Content-Type":
                    "application/json"
            },

            body: JSON.stringify(
                body
            )
        }
    );


    let data = null;

    try {

        data =
            await response.json();

    } catch {

        data = null;
    }


    if (!response.ok) {

        const message =
            typeof data?.detail === "string"
                ? data.detail
                : `Request failed (${response.status})`;

        throw new Error(
            message
        );
    }


    if (!data) {

        throw new Error(
            "Empty response"
        );
    }


    return data;
}

// ============================================================
// GET REQUEST
// ============================================================

async function apiGet(path) {

    const response =
        await fetch(
            API_BASE + path,
            {
                method: "GET",

                headers: {
                    "Accept":
                        "application/json"
                }
            }
        );


    let data = null;

    try {

        data =
            await response.json();

    } catch {

        data = null;
    }


    if (!response.ok) {

        const message =
            typeof data?.detail === "string"
                ? data.detail
                : `Request failed (${response.status})`;

        throw new Error(
            message
        );
    }


    if (!data) {

        throw new Error(
            "Empty response"
        );
    }


    return data;
}

// ============================================================
// CURRENCY FORMATTER
// ============================================================

const money = number =>
    new Intl.NumberFormat(
        "en-IN",
        {
            style: "currency",
            currency: "INR",
            maximumFractionDigits: 0
        }
    ).format(
        Number(
            number || 0
        )
    );


// ============================================================
// NUMBER FORMATTER
// ============================================================

const num = number =>
    new Intl.NumberFormat(
        "en-IN",
        {
            maximumFractionDigits: 0
        }
    ).format(
        Number(
            number || 0
        )
    );


// ============================================================
// HTML ESCAPE
// ============================================================

function esc(value) {

    const element =
        document.createElement(
            "div"
        );

    element.textContent =
        String(
            value ?? ""
        );

    return element.innerHTML;
}