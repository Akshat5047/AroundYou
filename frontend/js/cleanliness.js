const form = document.getElementById(
    "cleanlinessForm"
);

const fileInput = document.getElementById(
    "cleanlinessImage"
);

const preview = document.getElementById(
    "imagePreview"
);

const previewPlaceholder = document.getElementById(
    "previewPlaceholder"
);

const loading = document.getElementById(
    "cleanlinessLoading"
);

const result = document.getElementById(
    "cleanlinessResult"
);

const errorBox = document.getElementById(
    "cleanlinessError"
);


// ============================================================
// IMAGE PREVIEW
// ============================================================

fileInput.addEventListener(
    "change",
    function () {

        const file = fileInput.files[0];

        result.classList.remove("show");
        errorBox.classList.remove("show");

        if (!file) {

            preview.style.display = "none";

            previewPlaceholder.style.display = "flex";

            return;
        }


        const reader = new FileReader();


        reader.onload = function (event) {

            preview.src = event.target.result;

            preview.style.display = "block";

            previewPlaceholder.style.display = "none";

        };


        reader.readAsDataURL(file);

    }
);


// ============================================================
// ANALYSIS
// ============================================================

form.addEventListener(
    "submit",
    async function (event) {

        event.preventDefault();


        const file = fileInput.files[0];


        if (!file) {

            showError(
                "Please select an image first."
            );

            return;
        }


        if (file.size > 10 * 1024 * 1024) {

            showError(
                "Please select an image smaller than 10 MB."
            );

            return;
        }


        const allowedTypes = [
            "image/jpeg",
            "image/png",
            "image/webp"
        ];


        if (
            file.type
            && !allowedTypes.includes(file.type)
        ) {

            showError(
                "Please use a JPEG, PNG or WebP image."
            );

            return;
        }


        errorBox.classList.remove("show");

        result.classList.remove("show");

        loading.classList.add("show");


        try {

            const formData = new FormData();

            formData.append(
                "file",
                file
            );


            const response = await fetch(
                `${API_BASE}/api/cleanliness/analyze`,
                {
                    method: "POST",
                    body: formData
                }
            );


            let data;


            try {

                data = await response.json();

            } catch {

                throw new Error(
                    "The server returned an invalid response."
                );

            }


            if (!response.ok) {

                throw new Error(
                    data.detail
                    || "Cleanliness analysis failed."
                );

            }


            displayResult(data);

        } catch (error) {

            showError(
                error.message
                || "Unable to analyze the image."
            );

        } finally {

            loading.classList.remove("show");

        }

    }
);


// ============================================================
// DISPLAY RESULT
// ============================================================

function displayResult(data) {

    document.getElementById(
        "cleanlinessScore"
    ).textContent = `${data.cleanliness_score}/100`;


    const statusElement = document.getElementById(
        "cleanlinessStatus"
    );


    statusElement.textContent = data.status;


    statusElement.className =
        "cleanlinessStatus "
        + getStatusClass(data.status);


    document.getElementById(
        "litterCount"
    ).textContent = data.litter_count;


    document.getElementById(
        "litterCoverage"
    ).textContent =
        `${data.litter_coverage_percent}%`;


    document.getElementById(
        "averageConfidence"
    ).textContent =
        `${(
            data.average_confidence * 100
        ).toFixed(1)}%`;


    document.getElementById(
        "annotatedImage"
    ).src = data.annotated_image;


    document.getElementById(
        "cleanlinessDisclaimer"
    ).textContent = data.disclaimer;


    renderDetections(
        data.detections || []
    );


    result.classList.add("show");


    result.scrollIntoView({
        behavior: "smooth",
        block: "start"
    });

}


// ============================================================
// DETECTIONS
// ============================================================

function renderDetections(detections) {

    const container = document.getElementById(
        "detectionList"
    );


    container.innerHTML = "";


    if (detections.length === 0) {

        container.innerHTML = `
            <div class="noDetections">
                <strong>No visible litter detected.</strong>
                <p class="muted">
                    The model did not identify litter above
                    its confidence threshold in this image.
                </p>
            </div>
        `;

        return;
    }


    detections.forEach(
        function (detection, index) {

            const item = document.createElement(
                "div"
            );

            item.className = "detectionItem";


            const confidence = (
                detection.confidence * 100
            ).toFixed(1);


            item.innerHTML = `
                <div>
                    <strong>
                        Litter Detection ${index + 1}
                    </strong>

                    <span class="muted">
                        ${confidence}% confidence
                    </span>
                </div>

                <span class="chip">
                    ${detection.class_name}
                </span>
            `;


            container.appendChild(item);

        }
    );

}


// ============================================================
// STATUS STYLE
// ============================================================

function getStatusClass(status) {

    const normalized = String(
        status
    ).toLowerCase();


    if (normalized === "clean") {

        return "statusClean";

    }


    if (normalized.includes("light")) {

        return "statusLight";

    }


    if (normalized.includes("moderate")) {

        return "statusModerate";

    }


    return "statusHeavy";

}


// ============================================================
// ERROR
// ============================================================

function showError(message) {

    errorBox.textContent = message;

    errorBox.classList.add("show");

}