const map = new maplibregl.Map({
    container: "map",

    style: "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",

    center: [-84.8008, 33.4740],
    zoom: 9
});

map.addControl(
    new maplibregl.NavigationControl(),
    "top-right"
);


map.on("load", async () => {

    const [warningResponse, assetsResponse] = await Promise.all([
        fetch("./data/warning.geojson"),
        fetch("./data/grid_assets.geojson")
    ]);

    const warningData = await warningResponse.json();
    const assetsData = await assetsResponse.json();

    const warningProperties = warningData.features[0]?.properties;

    if (warningProperties) {
        document.getElementById("warning-id").textContent =
            warningProperties.warning_id || "—";
    }


    // --------------------------------------------------
    // Warning polygon
    // --------------------------------------------------

    map.addSource("warning", {
        type: "geojson",
        data: warningData
    });

    map.addLayer({
        id: "warning-fill",
        type: "fill",
        source: "warning",

        paint: {
            "fill-color": "#ef4444",
            "fill-opacity": 0.24
        }
    });

    map.addLayer({
        id: "warning-outline",
        type: "line",
        source: "warning",

        paint: {
            "line-color": "#ff6b6b",
            "line-width": 3
        }
    });


    // --------------------------------------------------
    // Infrastructure
    // --------------------------------------------------

    map.addSource("grid-assets", {
        type: "geojson",
        data: assetsData
    });


    map.addLayer({
        id: "power-lines",
        type: "line",
        source: "grid-assets",

        filter: [
            "==",
            ["get", "asset_class"],
            "power_line"
        ],

        paint: {
            "line-color": "#facc15",
            "line-width": 2.4,
            "line-opacity": 0.95
        }
    });


    /*
        Some Overture substations are polygon geometry rather than points,
        so support both polygon and point representations.
    */

    map.addLayer({
        id: "substation-fill",
        type: "fill",
        source: "grid-assets",

        filter: [
            "all",
            ["==", ["get", "asset_class"], "substation"],
            ["==", ["geometry-type"], "Polygon"]
        ],

        paint: {
            "fill-color": "#38bdf8",
            "fill-opacity": 0.85
        }
    });


    map.addLayer({
        id: "substation-outline",
        type: "line",
        source: "grid-assets",

        filter: [
            "all",
            ["==", ["get", "asset_class"], "substation"],
            ["==", ["geometry-type"], "Polygon"]
        ],

        paint: {
            "line-color": "#ffffff",
            "line-width": 1.4
        }
    });


    map.addLayer({
        id: "substation-points",
        type: "circle",
        source: "grid-assets",

        filter: [
            "all",
            ["==", ["get", "asset_class"], "substation"],
            ["==", ["geometry-type"], "Point"]
        ],

        paint: {
            "circle-radius": 6,
            "circle-color": "#38bdf8",
            "circle-stroke-color": "#ffffff",
            "circle-stroke-width": 1.5
        }
    });


    // --------------------------------------------------
    // Layer toggles
    // --------------------------------------------------

    document
        .getElementById("toggle-warning")
        .addEventListener("change", event => {

            const visibility = event.target.checked
                ? "visible"
                : "none";

            map.setLayoutProperty(
                "warning-fill",
                "visibility",
                visibility
            );

            map.setLayoutProperty(
                "warning-outline",
                "visibility",
                visibility
            );
        });


    document
        .getElementById("toggle-lines")
        .addEventListener("change", event => {

            map.setLayoutProperty(
                "power-lines",
                "visibility",
                event.target.checked ? "visible" : "none"
            );
        });


    document
        .getElementById("toggle-substations")
        .addEventListener("change", event => {

            const visibility = event.target.checked
                ? "visible"
                : "none";

            [
                "substation-fill",
                "substation-outline",
                "substation-points"
            ].forEach(layer => {

                map.setLayoutProperty(
                    layer,
                    "visibility",
                    visibility
                );

            });
        });


    // --------------------------------------------------
    // Asset inspector
    // --------------------------------------------------

    const interactiveLayers = [
        "power-lines",
        "substation-fill",
        "substation-points"
    ];


    interactiveLayers.forEach(layerId => {

        map.on("mouseenter", layerId, () => {
            map.getCanvas().style.cursor = "pointer";
        });

        map.on("mouseleave", layerId, () => {
            map.getCanvas().style.cursor = "";
        });


        map.on("click", layerId, event => {

            const feature = event.features[0];
            const properties = feature.properties;

            const assetClass =
                properties.asset_class === "power_line"
                    ? "Power Line"
                    : "Substation";

            document
                .getElementById("asset-inspector-empty")
                .classList
                .add("hidden");

            document
                .getElementById("asset-inspector")
                .classList
                .remove("hidden");

            document.getElementById("asset-type").textContent =
                assetClass;

            document.getElementById("asset-name").textContent =
                properties.asset_name || "Unnamed Overture asset";

            document.getElementById("asset-id").textContent =
                properties.asset_id || "—";


            new maplibregl.Popup({
                closeButton: false,
                offset: 10
            })
                .setLngLat(event.lngLat)
                .setHTML(`
                    <strong>${assetClass}</strong><br>
                    ${properties.asset_name || "Unnamed asset"}
                `)
                .addTo(map);

        });

    });

});