import * as L from "leaflet/src/Leaflet";
import {CooperativeScrollWheelZoom} from "./LeafletCooperativeScrollWheelZoom";

let coordsToPolygon = function (coords) {
    return coords[0].map((lnglat) => L.latLng(lnglat[1], lnglat[0]));
};

let getPolygonCoveringExterior = function (limitRect, outline) {
    let polygons = [];
    if (typeof(outline) === 'string') {
        outline = JSON.parse(outline);
    }

    // The limit of the view is the outer ring of the polygon
    polygons.push([
        L.latLng(limitRect['min']['lat'], limitRect['min']['lng']),
        L.latLng(limitRect['min']['lat'], limitRect['max']['lng']),
        L.latLng(limitRect['max']['lat'], limitRect['max']['lng']),
        L.latLng(limitRect['max']['lat'], limitRect['min']['lng']),
    ]);

    // The shape of the city itself is the "hole" in the polygon
    if (outline['type'] && outline['type'] === 'Polygon') {
        polygons.push(coordsToPolygon(outline['coordinates']));
    }
    if (outline['features']) {
        outline['features'].forEach((feature) => {
            if (feature['geometry']['type'] === 'MultiPolygon') {
                feature['geometry']['coordinates'].forEach((coords) => polygons.push(coordsToPolygon(coords)));
            }
            if (feature['geometry']['type'] === 'Polygon') {
                polygons.push(coordsToPolygon(feature['geometry']['coordinates']));
            }
        });
    }

    return polygons;
};

let setTiles = function (leaflet, initData) {
    let tiles = initData['tiles'];
    switch (tiles['provider']) {
        case 'OSM':
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: 'Map data © <a href="https://www.openstreetmap.org">OpenStreetMap</a>',
            }).addTo(leaflet);
            break;
        case 'Mapbox':
            let tileUrl = (tiles['tileUrl'] ? tiles['tileUrl'] : 'https://api.tiles.mapbox.com/v4/mapbox.streets/{z}/{x}/{y}{highres}.png?access_token={accessToken}');
            L.tileLayer(tileUrl, {
                attribution: 'Map data &copy; <a href="https://www.openstreetmap.org">OpenStreetMap</a>, <a href="https://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA</a>, Imagery © <a href="https://www.mapbox.com">Mapbox</a>',
                accessToken: tiles['token'],
                highres: (window.devicePixelRatio > 1.5 ? '@2x' : '')
            }).addTo(leaflet);
            break;
    }
};

let setInitView = function (leaflet, initData) {
    let initCenter = L.latLng(35.658611, 139.745556); // If nothing else is said explicitly, we're probably talking about the Tokyo Tower
    let initZoom = 15;
    if (initData['center']) {
        initCenter = L.latLng(initData['center']['lat'], initData['center']['lng']);
    }
    if (initData['zoom']) {
        initZoom = initData['zoom'];
    }
    leaflet.setView(initCenter, initZoom);
};

let setOutline = function (leaflet, initData) {
    if (initData['outline'] && initData['limit']) {
        let polygon = getPolygonCoveringExterior(initData['limit'], initData['outline']);
        let polygonLayer = L.polygon(polygon, {
            weight: 1,
            fillColor: "#ffffff",
            fillOpacity: 0.75,
            stroke: true,
            color: '#0000ff',
            opacity: 0.5,
            dashArray: [2, 4]
        });
        leaflet.addLayer(polygonLayer);
    }
};

let setBounds = function (leaflet, initData) {
    if (initData['limit']) {
        let bounds = L.latLngBounds(
            L.latLng(initData['limit']['min']['lat'], initData['limit']['min']['lng']),
            L.latLng(initData['limit']['max']['lat'], initData['limit']['max']['lng'])
        );
        leaflet.setMaxBounds(bounds);
    }
};

let setZoomBehavior = function (leaflet) {
    leaflet.addHandler('cooperativezoom', CooperativeScrollWheelZoom);
    leaflet.cooperativezoom.enable();
};

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
    // This behavior is enabled for maps that are shown by default. Drop-down-maps keep leaflet's default behavior.

    let leaflet = L.map($map_element.attr("id"), {
        maxBoundsViscosity: 1,
        minZoom: (initData['zoom'] < 12 ? initData['zoom'] : 12),
        maxZoom: 19,
        scrollWheelZoom: !(noTouchDrag === true),
        dragging: !(noTouchDrag === true),
    });

    setTiles(leaflet, initData);
    setInitView(leaflet, initData);
    setBounds(leaflet, initData);
    setOutline(leaflet, initData);
    setScrollingBehavior(noTouchDrag, leaflet, $map_element);

    return leaflet;
}
