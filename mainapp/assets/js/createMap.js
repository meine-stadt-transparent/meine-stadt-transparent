import * as L from "leaflet/src/Leaflet";

let getPolygonCoveringExterior = function (limitRect, outline) {
    let polygons = [];
    if (typeof(outline) === 'string') {
        outline = JSON.parse(outline);
    }

    let coordsToPolygon = (coords) => {
        let latlngs = [];
        coords[0].forEach((lnglat) => {
            latlngs.push(L.latLng(lnglat[1], lnglat[0]));
        });
        polygons.push(latlngs);
    };

    // The limit of the view is the outer ring of the polygon
    polygons.push([
        L.latLng(limitRect['min']['lat'], limitRect['min']['lng']),
        L.latLng(limitRect['min']['lat'], limitRect['max']['lng']),
        L.latLng(limitRect['max']['lat'], limitRect['max']['lng']),
        L.latLng(limitRect['max']['lat'], limitRect['min']['lng']),
    ]);

    // The shape of the city itself is the "hole" in the polygon
    if (outline['type'] && outline['type'] === 'Polygon') {
        coordsToPolygon(outline['coordinates']);
    }
    if (outline['features']) {
        outline['features'].forEach((feature) => {
            if (feature['geometry']['type'] === 'MultiPolygon') {
                feature['geometry']['coordinates'].forEach(coordsToPolygon);
            }
            if (feature['geometry']['type'] === 'Polygon') {
                coordsToPolygon(feature['geometry']['coordinates']);
            }
        });
    }

    return polygons;
};


export default function ($map_element, initData) {

    let leaflet = L.map($map_element.attr("id"), {
        maxBoundsViscosity: 1,
        minZoom: (initData['zoom'] < 12 ? initData['zoom'] : 12),
        maxZoom: 19,
    });

    L.tileLayer('https://api.tiles.mapbox.com/v4/{id}/{z}/{x}/{y}@2x.png?access_token=pk.eyJ1IjoidG9iaWFzaG9lc3NsIiwiYSI6ImNpeTMwdnFndTAwNDAzM21uaHpxYjZnNnEifQ.J_LAeL1849oRy4JK59X8cw', {
        attribution: 'Map data &copy; <a href="http://openstreetmap.org">OpenStreetMap</a> contributors, <a href="http://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA</a>, Imagery © <a href="http://mapbox.com">Mapbox</a>',
        id: 'mapbox.streets',
        accessToken: 'pk.eyJ1IjoidG9iaWFzaG9lc3NsIiwiYSI6ImNpeTMwdnFndTAwNDAzM21uaHpxYjZnNnEifQ.J_LAeL1849oRy4JK59X8cw'
    }).addTo(leaflet);

    let initCenter = L.latLng(35.658611, 139.745556); // If nothing else is said explicitly, we're probably talking about the Tokyo Tower
    let initZoom = 15;
    if (initData['center']) {
        initCenter = L.latLng(initData['center']['lat'], initData['center']['lng']);
    }
    if (initData['zoom']) {
        initZoom = initData['zoom'];
    }
    leaflet.setView(initCenter, initZoom);

    if (initData['limit']) {
        leaflet.setMaxBounds(L.latLngBounds(
            L.latLng(initData['limit']['min']['lat'], initData['limit']['min']['lng']),
            L.latLng(initData['limit']['max']['lat'], initData['limit']['max']['lng']),
        ));
    }

    if (initData['outline'] && initData['limit']) {
        let polygon = getPolygonCoveringExterior(initData['limit'], initData['outline']);
        leaflet.addLayer(L.polygon(polygon, {
            weight: 1,
            fillColor: "#ffffff",
            fillOpacity: 0.75,
            stroke: true,
            color: '#0000ff',
            opacity: 0.5,
            dashArray: [2, 4]
        }));
    }

    return leaflet;
}
