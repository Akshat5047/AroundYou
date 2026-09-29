// ============================================================
// AROUND YOU - TRIP PLANNER
// ============================================================

const form = document.querySelector("#planner");
const dateInput = document.querySelector("#date");
const destinationInput = document.querySelector("#destination");
const districtInput = document.querySelector("#district");
const districtDestinationInput =
    document.querySelector(
        "#districtDestination"
    );

const districtDestinationField =
    document.querySelector(
        "#districtDestinationField"
    );


// ============================================================
// SET DEFAULT DATE
// ============================================================

if (dateInput) {

    const nextDate = new Date();

    nextDate.setDate(
        nextDate.getDate() + 14
    );

    dateInput.value =
        nextDate
            .toISOString()
            .slice(0, 10);
}


// ============================================================
// GET DESTINATION FROM EXPLORE PAGE
// ============================================================

const urlParams =
    new URLSearchParams(
        window.location.search
    );

const selectedDestination =
    urlParams.get("destination");

const selectedDistrict =
    urlParams.get("district");


if (
    selectedDestination
    && destinationInput
) {

    destinationInput.value =
        selectedDestination;
}


if (
    selectedDistrict
    && districtInput
) {

    const exists =
        Array.from(
            districtInput.options
        ).some(
            option =>
                option.value ===
                selectedDistrict
        );

    if (exists) {

        districtInput.value =
            selectedDistrict;
    }
}

// ============================================================
// GET MULTIPLE DESTINATIONS FROM HOME PAGE
// ============================================================

let plannerSelectedDestinations = [];

try {

    const saved =
        JSON.parse(
            localStorage.getItem(
                "aroundYouSelectedDestinations"
            ) || "[]"
        );

    if (Array.isArray(saved)) {
        plannerSelectedDestinations = saved;
    }

} catch (error) {

    console.error(
        "Unable to read selected destinations:",
        error
    );

}


function renderPlannerSelectedDestinations() {

    const container =
        document.querySelector(
            "#plannerSelectedDestinations"
        );

    if (!container) {
        return;
    }

    if (!plannerSelectedDestinations.length) {

        container.innerHTML =
            `<span class="muted">
                No destinations selected from Home.
            </span>`;

        return;
    }

    container.innerHTML =
        plannerSelectedDestinations
            .map(
                (item, index) => `

                    <div class="plannerDestinationChip">

                        <div>
                            <strong>
                                ${escapeValue(
                                    item.name
                                    || item.spot_name
                                    || "Destination"
                                )}
                            </strong>

                            ${
                                item.district
                                    ? `<span>
                                        ${escapeValue(item.district)}
                                    </span>`
                                    : ""
                            }
                        </div>

                        <button
                            type="button"
                            class="plannerDestinationRemove"
                            data-index="${index}"
                            aria-label="Remove destination">
                            ×
                        </button>

                    </div>

                `
            )
            .join("");

    container
        .querySelectorAll(
            ".plannerDestinationRemove"
        )
        .forEach(button => {

            button.addEventListener(
                "click",
                () => {

                    const index =
                        Number(
                            button.dataset.index
                        );

                    plannerSelectedDestinations.splice(
                        index,
                        1
                    );

                    localStorage.setItem(
                        "aroundYouSelectedDestinations",
                        JSON.stringify(
                            plannerSelectedDestinations
                        )
                    );

                    renderPlannerSelectedDestinations();
                    updateDistrictFieldVisibility();

                }
            );

        });

}


renderPlannerSelectedDestinations();

// ============================================================
// DISTRICT FIELD BEHAVIOR
// ============================================================

const districtField =
    districtInput?.closest(".field");

function updateDistrictFieldVisibility() {

    const districtField =
        districtInput?.closest(
            ".field"
        );

    if (districtField) {
        districtField.style.display = "";
    }

    if (districtDestinationField) {
        districtDestinationField.style.display = "";
    }
}

updateDistrictFieldVisibility();

async function loadDistrictDestinations() {

    if (!districtDestinationInput) {
        return;
    }

    const district =
        districtInput?.value || "";

    districtDestinationInput.innerHTML = `
        <option value="">
            Loading destinations...
        </option>
    `;

    districtDestinationInput.disabled = true;

    if (!district) {

        districtDestinationInput.innerHTML = `
            <option value="">
                Select a district first
            </option>
        `;

        return;
    }

    try {

        const response =
            await apiGet(
                "/api/destinations"
            );

        const destinations =
            Array.isArray(response)
                ? response
                : response.destinations || [];

        const matching =
            destinations.filter(
                destination =>
                    String(
                        destination.district || ""
                    )
                        .trim()
                        .toLowerCase()
                    ===
                    district
                        .trim()
                        .toLowerCase()
            );

        districtDestinationInput.innerHTML = `
            <option value="">
                Select a destination
            </option>
        `;

        matching
            .sort(
                (a, b) =>
                    String(
                        a.name ||
                        a.spot_name ||
                        ""
                    ).localeCompare(
                        String(
                            b.name ||
                            b.spot_name ||
                            ""
                        )
                    )
            )
            .forEach(destination => {

                const name =
                    destination.name ||
                    destination.spot_name ||
                    "";

                if (!name) {
                    return;
                }

                const option =
                    document.createElement(
                        "option"
                    );

                option.value =
                    name;

                option.textContent =
                    name;

                option.dataset.id =
                    destination.document_id ||
                    destination.id ||
                    "";

                option.dataset.category =
                    destination.category ||
                    "";

                option.dataset.rating =
                    destination.rating ??
                    "";

                option.dataset.entryFee =
                    destination.entry_fee ??
                    "";

                districtDestinationInput.appendChild(
                    option
                );
            });

        districtDestinationInput.disabled = false;

        if (!matching.length) {

            districtDestinationInput.innerHTML = `
                <option value="">
                    No destinations available
                </option>
            `;

            districtDestinationInput.disabled = true;
        }

    } catch (error) {

        console.error(
            "Unable to load district destinations:",
            error
        );

        districtDestinationInput.innerHTML = `
            <option value="">
                Unable to load destinations
            </option>
        `;

        districtDestinationInput.disabled = true;
    }
}

if (
    districtInput
    && districtDestinationInput
) {

    districtInput.addEventListener(
        "change",
        () => {

            loadDistrictDestinations();
        }
    );
}

if (districtDestinationInput) {

    districtDestinationInput.addEventListener(
        "change",
        () => {

            const selectedOption =
                districtDestinationInput
                    .options[
                        districtDestinationInput.selectedIndex
                    ];

            const name =
                String(
                    selectedOption?.value || ""
                ).trim();

            if (!name) {
                return;
            }

            const district =
                String(
                    districtInput?.value || ""
                ).trim();

            const id =
                String(
                    selectedOption?.dataset.id || ""
                ).trim();

            const alreadySelected =
                plannerSelectedDestinations.some(
                    item => {

                        const itemId =
                            String(
                                item.id ||
                                item.document_id ||
                                ""
                            ).trim();

                        if (
                            id &&
                            itemId &&
                            id === itemId
                        ) {
                            return true;
                        }

                        return (
                            String(
                                item.name ||
                                item.spot_name ||
                                ""
                            )
                                .trim()
                                .toLowerCase()
                            ===
                            name.toLowerCase()
                            &&
                            String(
                                item.district || ""
                            )
                                .trim()
                                .toLowerCase()
                            ===
                            district.toLowerCase()
                        );
                    }
                );

            if (!alreadySelected) {

                plannerSelectedDestinations.push({
                    id:
                        id || null,

                    name:
                        name,

                    district:
                        district,

                    category:
                        selectedOption?.dataset.category || "",

                    rating:
                        selectedOption?.dataset.rating || null,

                    entry_fee:
                        selectedOption?.dataset.entryFee || null
                });

                localStorage.setItem(
                    "aroundYouSelectedDestinations",
                    JSON.stringify(
                        plannerSelectedDestinations
                    )
                );

                renderPlannerSelectedDestinations();
                updateDistrictFieldVisibility();
            }

            districtDestinationInput.value = "";
        }
    );
}

if (
    plannerSelectedDestinations.length === 0
) {

    loadDistrictDestinations();
}

// ============================================================
// SUBMIT TRIP
// ============================================================

if (form) {

    form.onsubmit =
        async function (event) {

            event.preventDefault();


            const output =
                document.querySelector("#out");

            const loading =
                document.querySelector("#load");

            if (loading.classList.contains('show')) return;

            const errorBox =
                document.querySelector("#err");

            const welcome =
                document.querySelector(
                    "#plannerWelcome"
                );


            // ------------------------------------------------
            // RESET UI
            // ------------------------------------------------

            output.className =
                "result";

            errorBox.className =
                "error";

            errorBox.textContent =
                "";

            loading.className =
                "loading show";


            if (welcome) {

                welcome.style.display =
                    "none";
            }


            // ------------------------------------------------
            // READ FORM VALUES
            // ------------------------------------------------

            const days =
                Number(
                    document.querySelector(
                        "#days"
                    ).value
                );


            const people =
                Number(
                    document.querySelector(
                        "#people"
                    ).value
                );


            const district =
    plannerSelectedDestinations.length > 0
        ? ""
        : districtInput.value;


            const destination =
                destinationInput
                    ? destinationInput.value.trim()
                    : "";

                    
            const selectedDestinationNames =
                plannerSelectedDestinations
        .map(item =>
            item.name ||
            item.spot_name ||
            ""
        )
        .filter(Boolean);        


            const preferences =
                document.querySelector(
                    "#request"
                ).value.trim();


            const budget =
                Number(
                    document.querySelector(
                        "#budget"
                    ).value
                );


            const tier =
                document.querySelector(
                    "#tier"
                ).value;


            const transport =
                document.querySelector(
                    "#transport"
                ).value;


            // ------------------------------------------------
            // BUILD AUTHORITATIVE REQUEST
            // ------------------------------------------------
            //
            // The structured form values are treated as the
            // authoritative trip requirements.
            //
            // Free-text preferences supplement those values
            // instead of replacing them.
            // ------------------------------------------------

            let requestText =
                `Plan a ${days}-day Telangana trip ` +
                `for ${people} people`;


            if (selectedDestinationNames.length > 0) {

    requestText +=
        ` specifically interested in visiting ` +
        `${selectedDestinationNames.join(", ")}`;

} else if (destination) {

    requestText +=
        ` interested in visiting ${destination}`;
}


            if (selectedDestinationNames.length > 0) {

    requestText += ".";

} else {

    requestText +=
        ` in ${district}.`;
}


            if (budget > 0) {

                requestText +=
                    ` The total trip budget is ₹${budget}.`;
            }


            if (tier) {

                requestText +=
                    ` Preferred accommodation tier: ${tier}.`;
            }


            if (transport) {

                requestText +=
                    ` Preferred transport mode: ${transport}.`;
            }


            if (preferences) {

                requestText +=
                    ` Traveler interests and preferences: ${preferences}.`;
            }


            // ------------------------------------------------
            // API REQUEST
            // ------------------------------------------------

            const submitButton = form.querySelector('button[type="submit"]');
            const submitLabel = submitButton.textContent;
            submitButton.disabled = true;
            submitButton.textContent = 'Generating your trip…';
            try {

                const data =
                    await apiPost(
                        "/api/agent/plan-trip",
                        {

                            request:
    requestText,

selected_destinations:
    plannerSelectedDestinations.map(
        item => ({
            name:
                item.name ||
                item.spot_name ||
                "",

            district:
                item.district ||
                district,

            id:
                item.id ||
                item.document_id ||
                null
        })
    ),

district:
    district,

                            travel_date:
                                dateInput.value,

                            budget_limit:
                                budget,

                            num_travelers:
                                people,

                            accommodation_tier:
                                tier,

                            transport_mode:
                                transport,

                            route_distance_km:
                                Number(
                                    document.querySelector(
                                        "#distance"
                                    ).value
                                ),

                            rainfall_mm:
                                Number(
                                    document.querySelector(
                                        "#rain"
                                    ).value
                                ),

                            road_access_rating:
                                Number(
                                    document.querySelector(
                                        "#road"
                                    ).value
                                ),

                            festival:
                                document.querySelector(
                                    "#festival"
                                ).value || "None"

                        }
                    );


                renderTrip(
                    data,
                    output
                );


            } catch (error) {

                console.error(
                    "Planner error:",
                    error
                );


                errorBox.textContent =
                    error.message
                    || "Unable to generate trip.";

                errorBox.className =
                    "error show";


                if (welcome) {

                    welcome.style.display =
                        "block";
                }


            } finally {

                submitButton.disabled = false;
                submitButton.textContent = submitLabel;

                loading.className =
                    "loading";
            }

        };
}


// ============================================================
// RENDER TRIP RESULTS
// ============================================================

function renderTrip(data, output) {
    renderPlannerResults(data, output);
}

// ============================================================
// FORMATTING HELPERS
// ============================================================

function renderMarkdown(markdown) {

    if (!markdown) {
        return "";
    }

    let text = String(markdown);
    text = text.replace(/\\/g, "");

    // Normalize line endings
    text = text
        .replace(/\r\n/g, "\n")
        .replace(/\r/g, "\n");

    // Remove Gemini backslash formatting artifacts
    text = text
        .replace(/^\s*\\+\s*$/gm, "")
        .replace(/\\([*_~`#>+\-.!])/g, "$1")
        .replace(/\\+\s*$/gm, "");

    // Remove excessive blank lines
    text = text.replace(
        /\n\s*\n+/g,
        "\n"
    );

    // Escape actual HTML
    text = escapeValue(text);

    // Headings
    text = text.replace(
        /^####\s+(.+)$/gm,
        "<h4>$1</h4>"
    );

    text = text.replace(
        /^###\s+(.+)$/gm,
        "<h3>$1</h3>"
    );

    text = text.replace(
        /^##\s+(.+)$/gm,
        "<h2>$1</h2>"
    );

    text = text.replace(
        /^#\s+(.+)$/gm,
        "<h1>$1</h1>"
    );

    // Bold
    text = text.replace(
        /\*\*(.+?)\*\*/g,
        "<strong>$1</strong>"
    );

    // Bullets
    text = text.replace(
        /^\s*[•*-]\s+(.+)$/gm,
        '<div class="ai-plan-bullet">• $1</div>'
    );

    // Remaining line breaks
    text = text.replace(
        /\n/g,
        "<br>"
    );

    return text;
}


// ============================================================
// ESCAPE HTML
// ============================================================

function escapeValue(value) {

    if (
        value === undefined
        || value === null
    ) {
        return "";
    }


    return String(value)
        .replaceAll(
            "&",
            "&amp;"
        )
        .replaceAll(
            "<",
            "&lt;"
        )
        .replaceAll(
            ">",
            "&gt;"
        )
        .replaceAll(
            "\"",
            "&quot;"
        )
        .replaceAll(
            "'",
            "&#039;"
        );
}


// ============================================================
// FORMAT MONEY
// ============================================================

function formatMoney(value) {

    if (
        value === undefined
        || value === null
        || value === ""
        || Number.isNaN(
            Number(value)
        )
    ) {

        return "—";
    }


    return (
        "₹"
        + Number(value)
            .toLocaleString(
                "en-IN",
                {
                    maximumFractionDigits: 2
                }
            )
    );
}


// ============================================================
// FORMAT NUMBER
// ============================================================

function formatNumber(value) {

    if (
        value === undefined
        || value === null
        || value === ""
        || Number.isNaN(
            Number(value)
        )
    ) {

        return "—";
    }


    return Number(value)
        .toLocaleString(
            "en-IN",
            {
                maximumFractionDigits: 0
            }
        );
}
