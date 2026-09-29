const HOME_API_BASE_URL =
    "https://aroundyou-api-xi6n.onrender.com";

const popularDestinationsContainer =
    document.getElementById("destinations");

const SELECTED_DESTINATIONS_KEY =
    "aroundYouSelectedDestinations";


// ============================================================
// HELPERS
// ============================================================

function homeEscapeHTML(value) {

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


function homeFormatCategory(category) {

    if (!category) {
        return "Tourist Place";
    }

    return String(category)
        .replaceAll("_", " ")
        .replace(
            /\b\w/g,
            letter => letter.toUpperCase()
        );
}


function homeFormatEntryFee(fee) {

    const value = Number(fee);

    if (!Number.isFinite(value) || value <= 0) {
        return "Free Entry";
    }

    return `₹${value.toLocaleString("en-IN")}`;
}


// ============================================================
// SELECTED DESTINATIONS
// ============================================================

function getSelectedDestinations() {

    try {

        const stored =
            localStorage.getItem(
                SELECTED_DESTINATIONS_KEY
            );

        if (!stored) {
            return [];
        }

        const parsed = JSON.parse(stored);

        return Array.isArray(parsed)
            ? parsed
            : [];

    } catch (error) {

        console.error(
            "Unable to read selected destinations:",
            error
        );

        return [];
    }
}


function saveSelectedDestinations(destinations) {

    localStorage.setItem(
        SELECTED_DESTINATIONS_KEY,
        JSON.stringify(destinations)
    );
}


function destinationSelectionKey(destination) {
    const name = destination.name || destination.spot_name;
    if (name) return `${String(name).trim()}|${String(destination.district || '').trim()}`.toLowerCase();

    const id =
        destination.id ||
        destination.document_id;

    if (id) {
        return String(id);
    }

    return `${destination.name || ""}|${destination.district || ""}`
        .trim()
        .toLowerCase();
}


function isDestinationSelected(destination) {

    const key =
        destinationSelectionKey(destination);

    return getSelectedDestinations().some(
        selected =>
            destinationSelectionKey(selected) === key
    );
}


function toggleDestinationSelection(destination) {

    const selected =
        getSelectedDestinations();

    const key =
        destinationSelectionKey(destination);

    const existingIndex =
        selected.findIndex(
            item =>
                destinationSelectionKey(item) === key
        );

    if (existingIndex >= 0) {

        selected.splice(
            existingIndex,
            1
        );

    } else {

        selected.push({
            id:
                destination.id ||
                destination.document_id ||
                null,

            name:
                destination.name ||
                "Unknown Destination",

            district:
                destination.district ||
                "Telangana",

            category:
                destination.category ||
                null,

            rating:
                destination.rating ??
                null,

            entry_fee:
                destination.entry_fee ??
                null
        });
    }

    saveSelectedDestinations(selected);

    updateDestinationSelectionButtons();

    renderSelectedDestinationsTray();
}


function removeSelectedDestination(key) {

    const selected =
        getSelectedDestinations()
            .filter(
                destination =>
                    destinationSelectionKey(
                        destination
                    ) !== key
            );

    saveSelectedDestinations(selected);

    updateDestinationSelectionButtons();

    renderSelectedDestinationsTray();
}


// ============================================================
// SELECTED DESTINATION TRAY
// ============================================================

function ensureSelectedDestinationsTray() {

    let tray =
        document.getElementById(
            "homeSelectedDestinations"
        );

    if (tray) {
        return tray;
    }

    const sectionHead =
        document.querySelector(
            ".sectionHead"
        );

    if (!sectionHead) {
        return null;
    }

    tray =
        document.createElement("div");

    tray.id =
        "homeSelectedDestinations";

    tray.className =
        "homeSelectionTray";

    sectionHead.insertAdjacentElement(
        "afterend",
        tray
    );

    return tray;
}


function renderSelectedDestinationsTray() {

    const tray =
        ensureSelectedDestinationsTray();

    if (!tray) {
        return;
    }

    const selected =
        getSelectedDestinations();

    if (selected.length === 0) {

        tray.innerHTML = "";

        tray.classList.remove("show");

        return;
    }

    const chips =
        selected
            .map(destination => {

                const key =
                    destinationSelectionKey(
                        destination
                    );

                return `
                    <div class="selectedDestinationChip">

                        <span>
                            ${homeEscapeHTML(
                                destination.name
                            )}
                        </span>

                        <button
                            type="button"
                            class="removeSelectedDestination"
                            data-selection-key="${homeEscapeHTML(
                                key
                            )}"
                            aria-label="Remove ${homeEscapeHTML(
                                destination.name
                            )}">

                            ×

                        </button>

                    </div>
                `;
            })
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
                    ${selected.length}
                    ${
                        selected.length === 1
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

    tray
        .querySelectorAll(
            ".removeSelectedDestination"
        )
        .forEach(button => {

            button.addEventListener(
                "click",
                () => {

                    removeSelectedDestination(
                        button.dataset.selectionKey
                    );
                }
            );
        });
}


// ============================================================
// SKELETON LOADING
// ============================================================

function renderDestinationSkeletons() {

    if (!popularDestinationsContainer) {
        return;
    }

    const skeletons = [];

    for (let index = 0; index < 6; index++) {

        skeletons.push(`

            <article
                class="destinationCard destinationSkeleton"
                aria-hidden="true">

                <div class="destinationTop">

                    <div class="skeletonIcon"></div>

                    <div class="skeletonTag"></div>

                </div>


                <div class="destinationBody">

                    <div
                        class="skeletonLine skeletonDistrict">
                    </div>

                    <div
                        class="skeletonLine skeletonTitle">
                    </div>

                    <div
                        class="skeletonLine skeletonTitleShort">
                    </div>


                    <div class="destinationMeta">

                        <div>
                            <div
                                class="skeletonLine skeletonMeta">
                            </div>
                        </div>

                        <div>
                            <div
                                class="skeletonLine skeletonMeta">
                            </div>
                        </div>

                    </div>


                    <div
                        class="skeletonLine skeletonButton">
                    </div>

                </div>

            </article>
        `);
    }

    popularDestinationsContainer.innerHTML =
        skeletons.join("");
}


// ============================================================
// LOAD POPULAR DESTINATIONS
// ============================================================

async function loadPopularDestinations() {

    if (!popularDestinationsContainer) {
        return;
    }

    renderDestinationSkeletons();

    try {

        const response = await fetch(
            `${HOME_API_BASE_URL}/api/destinations`
        );

        if (!response.ok) {

            throw new Error(
                `Request failed with status ${response.status}`
            );
        }

        const data =
            await response.json();

        const destinations =
            Array.isArray(data.destinations)
                ? data.destinations
                : [];

        destinations.sort((a, b) => {

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

        const [, photos] = await destinationAssets;
        const photographed = destinations.filter(item => photos[destinationAssetKey(item)]);
        const popularDestinations = (photographed.length ? photographed : destinations).slice(0, 6);

        popularDestinationsContainer.innerHTML =
            "";

        if (popularDestinations.length === 0) {

            popularDestinationsContainer.innerHTML = `
                <div class="emptyState">

                    <h3>
                        No destinations available
                    </h3>

                    <p>
                        Popular destinations could not
                        be found right now.
                    </p>

                </div>
            `;

            return;
        }

        popularDestinations.forEach(
            destination => {

                const card =
                    createHomeDestinationCard(
                        destination
                    );

                popularDestinationsContainer
                    .appendChild(card);
            }
        );

        updateDestinationSelectionButtons();

    } catch (error) {

        console.error(
            "Popular destination loading error:",
            error
        );

        popularDestinationsContainer.innerHTML = `
            <div class="emptyState">

                <h3>
                    Unable to load destinations
                </h3>

                <p>
                    Please refresh the page and try again.
                </p>

            </div>
        `;
    }
}


// ============================================================
// DESTINATION CARD
// ============================================================

function createHomeDestinationCard(destination) {

    const card =
        document.createElement("article");

    card.className =
        "destinationCard";

    const name =
        destination.name ||
        "Unknown Destination";

    const district =
        destination.district ||
        "Telangana";

    const category =
        homeFormatCategory(
            destination.category
        );

    const rating =
        destination.rating !== null &&
        destination.rating !== undefined
            ? Number(
                destination.rating
            ).toFixed(1)
            : "N/A";

    const entryFee =
        homeFormatEntryFee(
            destination.entry_fee
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
            encodeURIComponent(
                askQuestion
            )
        }`;

    const selectionKey =
        destinationSelectionKey(
            destination
        );

    const selected =
        isDestinationSelected(
            destination
        );

    card.dataset.selectionKey =
        selectionKey;

    card.innerHTML = `

        <div class="destinationTop">
${destinationVisual(category)}

            <button
                type="button"
                class="destinationIcon destinationAddButton ${
                    selected ? "selected" : ""
                }"
                data-selection-key="${homeEscapeHTML(
                    selectionKey
                )}"
                aria-label="${
                    selected
                        ? "Remove from trip"
                        : "Add to trip"
                }"
                title="${
                    selected
                        ? "Remove from trip"
                        : "Add to trip"
                }">

                ${selected ? "✓ Added" : "+ Add to trip"}

            </button>


            <span class="tag">
                ${homeEscapeHTML(category)}
            </span>

        </div>


        <div class="destinationBody">

            <p class="destinationDistrict">
                ${homeEscapeHTML(district)},
                Telangana
            </p>


            <h3>
                ${homeEscapeHTML(name)}
            </h3>


            <div class="destinationMeta">

                <div>

                    <span class="metaLabel">
                        Rating
                    </span>

                    <strong>
                        ★ ${homeEscapeHTML(rating)}
                    </strong>

                </div>


                <div>

                    <span class="metaLabel">
                        Entry
                    </span>

                    <strong>
                        ${homeEscapeHTML(entryFee)}
                    </strong>

                </div>

            </div>


            <div class="destinationActions">

                <a
                    href="${plannerURL}"
                    class="btn primary destinationPlan">

                    Plan This Trip

                </a>


                <a
                    href="${askURL}"
                    class="destinationAsk">

                    Ask About It →

                </a>

            </div>

        </div>
    `;


    const addButton =
        card.querySelector(
            ".destinationAddButton"
        );

    addButton.addEventListener(
        "click",
        () => {

            toggleDestinationSelection(
                destination
            );
        }
    );

    decorateDestinationCard(card, destination);
    return card;
}


// ============================================================
// REFRESH + / CHECK BUTTONS
// ============================================================

function updateDestinationSelectionButtons() {

    const selected =
        getSelectedDestinations();

    const selectedKeys =
        new Set(
            selected.map(
                destination =>
                    destinationSelectionKey(
                        destination
                    )
            )
        );

    document
        .querySelectorAll(
            ".destinationAddButton"
        )
        .forEach(button => {

            const selectedNow =
                selectedKeys.has(
                    button.dataset.selectionKey
                );

            button.classList.toggle(
                "selected",
                selectedNow
            );

            button.textContent =
                selectedNow
                    ? "✓ Added"
                    : "+ Add to trip";

            button.setAttribute(
                "aria-label",
                selectedNow
                    ? "Remove from trip"
                    : "Add to trip"
            );

            button.title =
                selectedNow
                    ? "Remove from trip"
                    : "Add to trip";
        });
}


// ============================================================
// INITIALIZE
// ============================================================

renderSelectedDestinationsTray();

loadPopularDestinations();
