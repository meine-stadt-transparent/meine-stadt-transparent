import * as L from "leaflet/src/Leaflet";
import create_map from "./createMap";

export default class IndexView {
    static escapeHtml(html) {
        return String(html).replace(/[&<>"'`=\/]/g, function (s) {
            return {
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                '"': '&quot;',
                "'": '&#39;',
                '/': '&#x2F;',
                '`': '&#x60;',
                '=': '&#x3D;'
            }[s];
        });
    }

    static geojsonToLocation(geojson) {
        if (geojson['type'] === 'Point') {
            return L.latLng(geojson['coordinates'][1], geojson['coordinates'][0]);
        } else {
            throw 'Unknown GeoJSON-Type: ' + geojson['type'];
        }
    }

    addDocumentLocationMarkers(documents) {
        this.locationMarkers = [];
        for (let location of Object.values(documents)) {
            if (Object.values(location.papers).length > 1) {
                console.warn('Multiple papers in this location', location); // @TODO Handle colliding markers and multiple papers
            }
            for (let paper of Object.values(location.papers)) {
                let marker = L.marker(IndexView.geojsonToLocation(location.coordinates), {
                    icon: L.icon({
                        iconUrl: '/static/images/marker-icon-2x.png',
                        iconSize: [25, 41],
                        iconAnchor: [12.5, 41],
                        popupAnchor: [0, -35]
                    })
                });
                let files = '';
                for (let i = 0; i < paper.files.length; i++) {
                    files += (i > 1 ? ', ' : '');
                    files += '<a href="' + paper.files[i].url + '">' + IndexView.escapeHtml(paper.files[i].name) + '</a>';
                }

                let paperHtml = '<a href="' + paper.url + '">' + IndexView.escapeHtml(paper.name) + '</a>';
                let contentHtml = '<div class="paper-title">' + paperHtml + '</div>' +
                    '<div class="file-location"><div class="location-name">' + IndexView.escapeHtml(location.name) + '</div>' +
                    '<div class="files">' + files + '</div></div>';
                marker.bindPopup(contentHtml, {className: 'file-location', minWidth: 200});
                marker.addTo(this.leaflet);

                this.locationMarkers.push(marker);
            }
        }
    }

    constructor($mapElement) {
        let initData = $mapElement.data("map-data");

        this.leaflet = create_map($mapElement, initData);

        if (initData['documents']) {
            this.addDocumentLocationMarkers(initData['documents']);
        }
    }
}
