import L from "leaflet";
import {CooperativeScrollWheelZoom} from "./LeafletCooperativeScrollWheelZoom";

const outlineStroke = {
    weight: 1,
    fillColor: "#ffffff",
    fillOpacity: 0.75,
    stroke: true,
    color: "#0000ff",
    opacity: 0.5,
    dashArray: [2, 4]
};


function coordsToPolygon(coords) {
    return coords[0].map((lnglat) => L.latLng(lnglat[1], lnglat[0]));
}

function getOutlineAsPolygons(outline) {
    let polygons = [];
    if (typeof (outline) === "string") {
        outline = JSON.parse(outline);
    }

    // The shape of the city itself is the "hole" in the polygon
    if (outline["type"] && outline["type"] === "Polygon") {
        polygons.push(coordsToPolygon(outline["coordinates"]));
    }
    if (outline["features"]) {
        outline["features"].forEach((feature) => {
            if (feature["geometry"]["type"] === "MultiPolygon") {
                feature["geometry"]["coordinates"].forEach((coords) => polygons.push(coordsToPolygon(coords)));
            }
            if (feature["geometry"]["type"] === "Polygon") {
                polygons.push(coordsToPolygon(feature["geometry"]["coordinates"]));
            }
        });
    }

    return polygons;
}

function setTiles(leaflet, initData) {
    let tiles = initData["tiles"];
    switch (tiles["provider"]) {
        case "OSM":
            L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
                attribution: 'Map data © <a href="https://www.openstreetmap.org">OpenStreetMap</a>',
            }).addTo(leaflet);
            break;
        case "Mapbox":
            let tileUrl = (tiles["tileUrl"] ? tiles["tileUrl"] : "https://api.tiles.mapbox.com/v4/mapbox.streets/{z}/{x}/{y}{highres}.png?access_token={accessToken}");
            L.tileLayer(tileUrl, {
                attribution: 'Map data &copy; <a href="https://www.openstreetmap.org">OpenStreetMap</a>, <a href="https://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA</a>, Imagery © <a href="https://www.mapbox.com">Mapbox</a>',
                accessToken: tiles['token'],
                highres: (window.devicePixelRatio > 1.5 ? '@2x' : '')
            }).addTo(leaflet);
            break;
    }
}

function setBoundsAndOutline(leaflet, polygons) {
    // Create a bound around all polygons
    let cityBounds = L.polygon(polygons[0]).getBounds();
    for (let polygon of polygons) {
        cityBounds = cityBounds.extend(L.polygon(polygon).getBounds());
    }
    let paddedBounds = cityBounds.pad(1);

    // View is limit to the city and a bit of surrounding area
    leaflet.setMaxBounds(paddedBounds);
    // Sets the initial zoom
    leaflet.fitBounds(cityBounds);
    // We don"t want the user to be able zoom out so far he can see we"re using a bounding box
    leaflet.setMinZoom(leaflet.getBoundsZoom(paddedBounds, true));

    // The white-ishly blurred area is paddedBounds as polygon
    let blurringBounds = [
        paddedBounds.getNorthEast(),
        paddedBounds.getNorthWest(),
        paddedBounds.getSouthWest(),
        paddedBounds.getSouthEast(),
    ];

    // This will make the inner part by normal and outer surrounding area white-ish
    polygons.unshift(blurringBounds);

    let polygonLayer = L.polygon(polygons, outlineStroke);
    leaflet.addLayer(polygonLayer);
}

function setZoomBehavior(leaflet) {
    leaflet.addHandler("cooperativezoom", CooperativeScrollWheelZoom);
    leaflet.cooperativezoom.enable();
}

function setScrollingBehavior(noTouchDrag, leaflet, $map_element) {
    if (noTouchDrag === true) {
        setZoomBehavior(leaflet);

        let mouseMode = false;

        $map_element.one("mousedown mousemove", (ev) => {
            if (ev.originalEvent.sourceCapabilities && ev.originalEvent.sourceCapabilities.firesTouchEvents === true) {
                // Ghost event triggered by touching the map
                return;
            }
            leaflet.dragging.enable();
            mouseMode = true;
        });
        $map_element.on("focus", () => {
            if (!mouseMode) {
                leaflet.dragging.enable();
            }
        });
        $map_element.on("blur", () => {
            if (!mouseMode) {
                leaflet.dragging.disable();
            }
        });
    }
}

export default function ($map_element, initData, noTouchDrag) {
    // noTouchDrag: Dragging is disabled by default.
    // For mouse users, it is enabled once the first mouse-typical event occurs
    // For touch users, it is enabled as long as the map has the focus
    // This behavior is enabled for maps that are shown by default. Drop-down-maps keep leaflet"s default behavior.

    let leaflet = L.map($map_element.attr("id"), {
        maxBoundsViscosity: 1,
        maxZoom: 19,
        scrollWheelZoom: !(noTouchDrag === true),
        dragging: !(noTouchDrag === true),
        zoomSnap: 0.1,
    });

    setTiles(leaflet, initData);

    if (initData["outline"]) {
        let polygons = getOutlineAsPolygons(initData["outline"]);
        setBoundsAndOutline(leaflet, polygons);
    } else {
        // If nothing else is said explicitly, we"re probably talking about the Tokyo Tower
        let initCenter = L.latLng(35.658611, 139.745556);
        let initZoom = 15;
        leaflet.setView(initCenter, initZoom);
    }

    setScrollingBehavior(noTouchDrag, leaflet, $map_element);

    return leaflet;
};
