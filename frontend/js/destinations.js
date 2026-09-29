const API_BASE_URL = "https://aroundyou-api-xi6n.onrender.com";

const districtFilter =
    document.getElementById("districtFilter");

const categoryFilter =
    document.getElementById("categoryFilter");

const destinationSearch =
    document.getElementById("destinationSearch");

const destinationGrid =
    document.getElementById("destinationGrid");

const destinationCount =
    document.getElementById("destinationCount");

const heroDestinationCount =
    document.getElementById("heroDestinationCount");

const resultsTitle =
    document.getElementById("resultsTitle");

const exploreStatus =
    document.getElementById("exploreStatus");

const loadMoreButton =
    document.getElementById("loadMoreButton");


let allDestinations = [];
let filteredDestinations = [];

const SELECTED_DESTINATIONS_KEY =
    "aroundYouSelectedDestinations";

let selectedDestinations =
    loadSelectedDestinations();

const PAGE_SIZE = 12;
let visibleCount = PAGE_SIZE;


/* ==========================================================
HELPERS
   ========================================================== */

function loadSelectedDestinations() {

    try {

        const stored = localStorage.getItem(
            SELECTED_DESTINATIONS_KEY
        );

        const parsed = JSON.parse(
            stored || "[]"
        );

        return Array.isArray(parsed)
            ? parsed
            : [];

    } catch (error) {

        console.error(
            "Unable to load selected destinations:",
            error
        );

        return [];
    }
}


function saveSelectedDestinations() {

    localStorage.setItem(
        SELECTED_DESTINATIONS_KEY,
        JSON.stringify(
            selectedDestinations
        )
    );
}


function getDestinationId(destination) {

    return String(
        destination.document_id ||
        destination.id ||
        ""
    ).trim();
}


function isDestinationSelected(destination) {

    const id =
        getDestinationId(destination);

    const name =
        String(
            destination.name || ""
        ).trim().toLowerCase();

    const district =
        String(
            destination.district || ""
        ).trim().toLowerCase();

    return selectedDestinations.some(
        selected => {

            const selectedId =
                String(
                    selected.id || ""
                ).trim();

            if (
                id &&
                selectedId &&
                id === selectedId
            ) {
                return true;
            }

            return (
                String(
                    selected.name || ""
                ).trim().toLowerCase() === name
                &&
                String(
                    selected.district || ""
                ).trim().toLowerCase() === district
            );
        }
    );
}

function escapeHTML(value) {

    if (value === null || value === undefined) {
        return "";
    }

    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


function formatCategory(category) {

    if (!category) {
        return "Tourist Place";
    }

    return category
        .replaceAll("_", " ")
        .replace(/\b\w/g, letter => letter.toUpperCase());
}


function formatEntryFee(fee) {

    const value = Number(fee);

    if (!Number.isFinite(value) || value <= 0) {
        return "Free Entry";
    }

    return `₹${value.toLocaleString("en-IN")}`;
}

/* ==========================================================
   SELECTED DESTINATIONS TRAY
   ========================================================== */

function ensureExploreSelectionTray() {

    let tray =
        document.getElementById(
            "exploreSelectedDestinations"
        );

    if (tray) {
        return tray;
    }

    const resultsHead =
        document.querySelector(
            ".exploreResultsHead"
        );

    if (!resultsHead) {
        return null;
    }

    tray =
        document.createElement("div");

    tray.id =
        "exploreSelectedDestinations";

    tray.className =
        "homeSelectionTray";

    resultsHead.insertAdjacentElement(
        "afterend",
        tray
    );

    return tray;
}


function renderExploreSelectionTray() {

    const tray =
        ensureExploreSelectionTray();

    if (!tray) {
        return;
    }

    if (selectedDestinations.length === 0) {

        tray.innerHTML = "";
        tray.classList.remove("show");

        return;
    }

    const chips =
        selectedDestinations
            .map(destination => `

                <div class="selectedDestinationChip">

                    <span>
                        ${escapeHTML(
                            destination.name
                        )}
                    </span>

                </div>
            `)
            .join("");

    tray.innerHTML = `

        <div class="selectionTrayHeader">

            <div>

                <span class="eyebrow">
                    Your Trip
                </span>

                <h3>
                    Selected destinations
                </h3>

                <p class="muted">
                    ${selectedDestinations.length}
                    ${
                        selectedDestinations.length === 1
                            ? "destination"
                            : "destinations"
                    }
                    selected
                </p>

            </div>


            <a
                href="planner.html?selected=1"
                class="btn primary">

                Plan Selected →

            </a>

        </div>


        <div class="selectedDestinationList">

            ${chips}

        </div>
    `;

    tray.classList.add("show");
}

/* ==========================================================
   API
   ========================================================== */

async function loadDestinations() {

    if (destinationCount) {
    destinationCount.textContent =
        "Loading destinations...";
}

if (exploreStatus) {
    exploreStatus.innerHTML = "";
}

    try {

        const response = await fetch(
            `${API_BASE_URL}/api/destinations`
        );

        if (!response.ok) {

            throw new Error(
                `Request failed with status ${response.status}`
            );
        }

        const data = await response.json();

        allDestinations =
            Array.isArray(data.destinations)
                ? data.destinations
                : [];


        allDestinations.sort((a, b) => {

            const popularityDifference =
                Number(b.popularity || 0) -
                Number(a.popularity || 0);

            if (popularityDifference !== 0) {
                return popularityDifference;
            }

            return (
                Number(b.rating || 0) -
                Number(a.rating || 0)
            );
        });


        heroDestinationCount.textContent =
            allDestinations.length;


        populateDistricts();
        populateCategories();

        applyFilters();

    } catch (error) {

        console.error(
            "Destination loading error:",
            error
        );

        destinationCount.textContent =
            "Unable to load destinations";

        heroDestinationCount.textContent = "—";

        exploreStatus.innerHTML = `
            <div class="exploreError">
                <strong>We couldn't load the destinations.</strong>
                <span>
                    Please check your connection and try again.
                </span>
            </div>
        `;
    }
}


/* ==========================================================
   FILTER OPTIONS
   ========================================================== */

function populateDistricts() {

    const districts = [
        ...new Set(
            allDestinations
                .map(item => item.district)
                .filter(Boolean)
        )
    ].sort((a, b) =>
        a.localeCompare(b)
    );


    districtFilter.innerHTML =
        `<option value="">All Districts</option>`;


    districts.forEach(district => {

        const option =
            document.createElement("option");

        option.value = district;
        option.textContent = district;

        districtFilter.appendChild(option);
    });
}


function populateCategories() {

    const categories = [
        ...new Set(
            allDestinations
                .map(item => item.category)
                .filter(Boolean)
        )
    ].sort((a, b) =>
        a.localeCompare(b)
    );


    categoryFilter.innerHTML =
        `<option value="">All Categories</option>`;


    categories.forEach(category => {

        const option =
            document.createElement("option");

        option.value = category;
        option.textContent =
            formatCategory(category);

        categoryFilter.appendChild(option);
    });
}


/* ==========================================================
   FILTERING
   ========================================================== */

function applyFilters() {

    const district =
        districtFilter.value.trim();

    const category =
        categoryFilter.value.trim();

    const search =
        destinationSearch.value
            .trim()
            .toLowerCase();


    filteredDestinations =
        allDestinations.filter(destination => {

            const matchesDistrict =
                !district ||
                destination.district === district;


            const matchesCategory =
                !category ||
                destination.category === category;


            const searchableText = `
                ${destination.name || ""}
                ${destination.district || ""}
                ${destination.category || ""}
            `.toLowerCase();


            const matchesSearch =
                !search ||
                searchableText.includes(search);


            return (
                matchesDistrict &&
                matchesCategory &&
                matchesSearch
            );
        });


    visibleCount = PAGE_SIZE;

    updateResultsHeading();

    renderDestinations();
}


function updateResultsHeading() {

    const district =
        districtFilter.value;

    const category =
        categoryFilter.value;


    if (district && category) {

        resultsTitle.textContent =
            `${formatCategory(category)} places in ${district}`;

    } else if (district) {

        resultsTitle.textContent =
            `Explore ${district}`;

    } else if (category) {

        resultsTitle.textContent =
            `${formatCategory(category)} destinations`;

    } else {

        resultsTitle.textContent =
            "Explore Telangana";
    }


    destinationCount.textContent =
        `${filteredDestinations.length} ${
            filteredDestinations.length === 1
                ? "destination"
                : "destinations"
        } found`;
}


/* ==========================================================
   RENDER DESTINATIONS
   ========================================================== */

function renderDestinations() {

    destinationGrid.innerHTML = "";

    exploreStatus.innerHTML = "";


    if (filteredDestinations.length === 0) {

        exploreStatus.innerHTML = `
            <div class="emptyState">

                <div class="emptyStateIcon">
                    ⌕
                </div>

                <h3>
                    No destinations found
                </h3>

                <p>
                    Try changing your search,
                    district or category.
                </p>

            </div>
        `;

        loadMoreButton.style.display = "none";

        return;
    }


    const destinationsToShow =
        filteredDestinations.slice(
            0,
            visibleCount
        );


    destinationsToShow.forEach(
        destination => {

            const card =
                createDestinationCard(destination);

            destinationGrid.appendChild(card);
        }
    );


    if (
        visibleCount <
        filteredDestinations.length
    ) {

        loadMoreButton.style.display =
            "inline-block";

    } else {

        loadMoreButton.style.display =
            "none";
    }
}


/* ==========================================================
   DESTINATION CARD
   ========================================================== */

function createDestinationCard(destination) {

    const card =
        document.createElement("article");

    card.className = "destinationCard";


    const name =
        destination.name ||
        "Unknown Destination";

    const district =
        destination.district ||
        "Telangana";

    const category =
        formatCategory(
            destination.category
        );

    const rating =
        destination.rating !== null &&
        destination.rating !== undefined
            ? Number(
                destination.rating
            ).toFixed(1)
            : "N/A";

    const popularity =
        destination.popularity !== null &&
        destination.popularity !== undefined
            ? Number(
                destination.popularity
            ).toLocaleString("en-IN")
            : "N/A";

    const entryFee =
        formatEntryFee(
            destination.entry_fee
        );


    const selected =
        isDestinationSelected(
            destination
        );


    const plannerURL =
        `planner.html?destination=${
            encodeURIComponent(name)
        }&district=${
            encodeURIComponent(district)
        }`;


    const askQuestion =
        `Tell me about ${name} in ${district}, Telangana.`;

    const askURL =
        `ask.html?q=${
            encodeURIComponent(askQuestion)
        }`;


    card.innerHTML = `

        <div class="destinationTop">
${destinationVisual(category)}

<button
    type="button"
    class="destinationIcon destinationAddButton ${
        selected ? "selected" : ""
    }"
    aria-label="${
        selected ? "Remove" : "Add"
    } ${escapeHTML(name)} ${
        selected ? "from" : "to"
    } trip"
    title="${
        selected ? "Remove from trip" : "Add to trip"
    }"
>
    ${selected ? "✓ Added" : "+ Add to trip"}
</button>

            <span class="tag">
                ${escapeHTML(category)}
            </span>

        </div>


        <div class="destinationBody">

            <p class="destinationDistrict">
                ${escapeHTML(district)}, Telangana
            </p>

            <h3>
                ${escapeHTML(name)}
            </h3>


            <div class="destinationMeta">

                <div>
                    <span class="metaLabel">
                        Rating
                    </span>

                    <strong>
                        ★ ${escapeHTML(rating)}
                    </strong>
                </div>


                <div>
                    <span class="metaLabel">
                        Entry
                    </span>

                    <strong>
                        ${escapeHTML(entryFee)}
                    </strong>
                </div>


                <div>
                    <span class="metaLabel">
                        Popularity
                    </span>

                    <strong>
                        ${escapeHTML(popularity)}
                    </strong>
                </div>

            </div>


            <div class="destinationActions">

                <a
                    href="${plannerURL}"
                    class="btn primary destinationPlan"
                >
                    Plan This Trip
                </a>

                <a
                    href="${askURL}"
                    class="destinationAsk"
                >
                    Ask About It →
                </a>

            </div>

        </div>
    `;

        const addButton =
        card.querySelector(
            ".destinationAddButton"
        );

    if (addButton) {

        addButton.addEventListener(
            "click",
            function () {

                const destinationId =
                    getDestinationId(
                        destination
                    );

                const alreadySelected =
                    isDestinationSelected(
                        destination
                    );

                if (alreadySelected) {

                    selectedDestinations =
                        selectedDestinations.filter(
                            selected => {

                                const selectedId =
                                    String(
                                        selected.id || ""
                                    ).trim();

                                if (
                                    destinationId &&
                                    selectedId
                                ) {
                                    return (
                                        selectedId !==
                                        destinationId
                                    );
                                }

                                return !(
                                    String(
                                        selected.name || ""
                                    )
                                        .trim()
                                        .toLowerCase()
                                    ===
                                    String(
                                        name
                                    )
                                        .trim()
                                        .toLowerCase()
                                    &&
                                    String(
                                        selected.district || ""
                                    )
                                        .trim()
                                        .toLowerCase()
                                    ===
                                    String(
                                        district
                                    )
                                        .trim()
                                        .toLowerCase()
                                );
                            }
                        );

                } else {

                    selectedDestinations.push({
                        id:
                            destinationId,

                        name:
                            name,

                        district:
                            district,

                        category:
                            destination.category || "",

                        rating:
                            destination.rating ?? null,

                        entry_fee:
                            destination.entry_fee ?? 0
                    });
                }

                saveSelectedDestinations();

renderExploreSelectionTray();

renderDestinations();
            }
        );
    }


    decorateDestinationCard(card, destination);
    return card;
}


/* ==========================================================
   EVENTS
   ========================================================== */

if (districtFilter) {
    districtFilter.addEventListener(
        "change",
        applyFilters
    );
}

if (categoryFilter) {
    categoryFilter.addEventListener(
        "change",
        applyFilters
    );
}


if (destinationSearch) {
    destinationSearch.addEventListener(
        "input",
        applyFilters
    );
}

if (loadMoreButton) {
    loadMoreButton.addEventListener(
        "click",
        function () {

            visibleCount += PAGE_SIZE;

            renderDestinations();
        }
    );
}


/* ==========================================================
START
   ========================================================== */

renderExploreSelectionTray();

if (destinationGrid) {
    loadDestinations();
}
