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

                loading.className =
                    "loading";
            }

        };
}


// ============================================================
// RENDER TRIP RESULTS
// ============================================================

function renderTrip(
    data,
    output
) {

    const tools =
        data.tool_results || {};


    const ml =
        tools.ml_predictions || {};


    const budget =
        tools.budget_evaluation || {};


    const budgetPrediction =
        ml.budget?.prediction || {};


    const transport =
        ml.transport || {};


    const crowd =
        ml.crowd || {};


    const climate =
        ml.climate || {};


    const destinationSearch =
        tools.destination_search || {};


    const sources =
        destinationSearch.sources || [];


    const source =
        sources.length
            ? sources[0]
            : {};


    const storage =
        tools.storage || {};


    // --------------------------------------------------------
    // DESTINATION
    // --------------------------------------------------------

    const destinationName =
        source.spot_name
        || destinationInput?.value
        || districtInput?.value
        || "Your Telangana Trip";


    // --------------------------------------------------------
    // CLIMATE MESSAGE
    // --------------------------------------------------------

    let climateMessage =
        "Climate prediction isn't available for this district yet.";


    if (climate.status === "success") {

        const prediction =
            climate.prediction || {};


        const maxTemp =
            prediction.Temperature_Max_C;

        const minTemp =
            prediction.Temperature_Min_C;

        const rainfall =
            prediction.Rainfall_Percent;


        const climateParts = [];


        if (
            maxTemp !== undefined
            && maxTemp !== null
        ) {

            climateParts.push(
                `Max ${Number(maxTemp).toFixed(1)}°C`
            );
        }


        if (
            minTemp !== undefined
            && minTemp !== null
        ) {

            climateParts.push(
                `Min ${Number(minTemp).toFixed(1)}°C`
            );
        }


        if (
            rainfall !== undefined
            && rainfall !== null
        ) {

            climateParts.push(
                `Rainfall chance ${Number(rainfall).toFixed(1)}%`
            );
        }


        climateMessage =
            climateParts.length
                ? climateParts.join(" · ")
                : "Climate prediction available.";


    } else if (climate.message) {

        climateMessage =
            climate.message;
    }


    // --------------------------------------------------------
    // BUDGET DIFFERENCE DISPLAY
    // --------------------------------------------------------

    let budgetDifferenceLabel =
        "Remaining";


    let budgetDifference =
        budget.difference;


    if (
        budget.status === "over_budget"
        && budgetDifference !== undefined
        && budgetDifference !== null
    ) {

        budgetDifferenceLabel =
            "Over Budget";

        budgetDifference =
            Math.abs(
                Number(
                    budgetDifference
                )
            );
    }


    // --------------------------------------------------------
    // HTML
    // --------------------------------------------------------

    output.innerHTML = `

        <div class="resultCard">

            <span class="tag">
                AI Trip Plan
            </span>

            <h2>
                ${escapeValue(destinationName)}
            </h2>

            <div
                style="
                    margin-top:15px;
                    line-height:1.7;
                ">

                ${renderMarkdown(data.plan)}

            </div>

        </div>


        <div class="resultCard">

            <h3>
                Budget
            </h3>

            <div class="metrics">

                <div class="metric">

                    Limit

                    <b>
                        ${formatMoney(
                            budget.budget_limit
                        )}
                    </b>

                </div>


                <div class="metric">

                    Predicted

                    <b>
                        ${formatMoney(
                            budget.predicted_cost
                        )}
                    </b>

                </div>


                <div class="metric">

                    ${escapeValue(
                        budgetDifferenceLabel
                    )}

                    <b>
                        ${formatMoney(
                            budgetDifference
                        )}
                    </b>

                </div>


                <div class="metric">

                    Status

                    <b>
                        ${escapeValue(
                            String(
                                budget.status || "—"
                            )
                            .replaceAll(
                                "_",
                                " "
                            )
                        )}
                    </b>

                </div>

            </div>

        </div>


        <div class="resultCard">

            <h3>
                Cost Breakdown
            </h3>

            <div class="metrics">

                <div class="metric">

                    Travel

                    <b>
                        ${formatMoney(
                            budgetPrediction
                                .travel_cost_est
                        )}
                    </b>

                </div>


                <div class="metric">

                    Stay

                    <b>
                        ${formatMoney(
                            budgetPrediction
                                .stay_cost_est
                        )}
                    </b>

                </div>


                <div class="metric">

                    Food

                    <b>
                        ${formatMoney(
                            budgetPrediction
                                .food_cost_est
                        )}
                    </b>

                </div>


                <div class="metric">

                    Entry

                    <b>
                        ${formatMoney(
                            budgetPrediction
                                .entry_fees_est
                        )}
                    </b>

                </div>

            </div>

        </div>


        <div class="resultCard">

            <h3>
                Transport
            </h3>

            <p>

                Planned:

                <b>
                    ${escapeValue(
                        transport
                            .user_planned_mode
                        || "—"
                    )}
                </b>

                &nbsp;·&nbsp;

                ML recommendation:

                <b>
                    ${escapeValue(
                        transport
                            .prediction
                            ?.recommended_transport_mode
                        || "—"
                    )}
                </b>

            </p>

        </div>


        <div class="resultCard">

            <h3>
                Crowd
            </h3>

            <p>

                ${escapeValue(
                    crowd.destination
                    || destinationName
                )}

                :

                <b>

                    ${formatNumber(
                        crowd
                            .prediction
                            ?.predicted_total_visitors
                    )}

                </b>

                predicted visitors

            </p>

        </div>


        <div class="resultCard">

            <h3>
                Climate
            </h3>

            <p>
                ${escapeValue(
                    climateMessage
                )}
            </p>

        </div>


        ${
            sources.length
                ? `

                <div class="resultCard">

                    <h3>
                        Recommended Destinations
                    </h3>

                    ${sources
                        .map(
                            (item, index) => `

                                <div
                                    style="
                                        margin-top:
                                        ${index === 0 ? "10px" : "18px"};
                                    "
                                >

                                    <strong>
                                        ${index + 1}.
                                        ${escapeValue(
                                            item.spot_name
                                            || "Destination"
                                        )}
                                    </strong>

                                    <div class="muted">
                                        ${escapeValue(
                                            item.category
                                            || ""
                                        )}
                                        ${
                                            item.district
                                                ? ` · ${escapeValue(
                                                    item.district
                                                )}`
                                                : ""
                                        }
                                    </div>

                                </div>

                            `
                        )
                        .join("")}

                    <p class="muted">
                        Grounded using Around You's
                        destination knowledge base.
                    </p>

                </div>

                `
                : ""
        }


        ${
            storage.request_saved
            && storage.result_saved
                ? `

                <div class="notice">

                    Trip generated successfully
                    and saved.

                </div>

                `
                : ""
        }

    `;


    output.className =
        "result show";
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