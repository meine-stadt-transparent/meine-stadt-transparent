import L from "leaflet";
import {TextHint} from "./LeafletTextHint";
import {MarkerClusterGroup} from "leaflet.markercluster/dist/leaflet.markercluster-src";

import create_map from "./createMap";

export default class IndexView {
    constructor($mapElement) {
        let initData = $mapElement.data("map-data");
        this.textMore1 = $mapElement.data("more-file-1");
        this.textMoreX = $mapElement.data("more-files-x");

        this.leaflet = create_map($mapElement, initData, true);
        let textHint = $mapElement.data("text-hint");
        if (textHint !== "") {
            (new TextHint({text: textHint})).addTo(this.leaflet);
        }

        if (initData['documents']) {
            this.addDocumentLocationMarkers(initData['documents']);
        }
    }

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
        let clusterGroup = new MarkerClusterGroup({
            maxClusterRadius: 40
        });

        this.locationMarkers = [];
        for (let location of Object.values(documents)) {
            for (let paper of Object.values(location.papers)) {
                if (!location.coordinates) {
                    continue;
                }
                let marker = this.addLocationMarker(location, paper, clusterGroup);

                this.locationMarkers.push(marker);
            }
        }

        clusterGroup.addTo(this.leaflet);
    }

    addLocationMarker(location, paper, clusterGroup) {
        let marker = L.marker(IndexView.geojsonToLocation(location.coordinates));

        let paperName = IndexView.escapeHtml(paper.name);
        let paperHtml = '<a href="' + paper.url + '" title="' + paperName + '">' + paperName + '</a>';

        let files = '';
        for (let i = 0; i < paper.files.length && i < 2; i++) {
            let fileUrl = paper.files[i].url + '?pdfjs_search=' + encodeURIComponent(location.name) + '&pdfjs_phrase=true';
            files += '<li>↳ <a href="' + fileUrl + '">' + IndexView.escapeHtml(paper.files[i].name) + '</a></li>';
        }
        if (paper.files.length > 3) {
            let remaining = this.textMoreX.replace(/%NUM%/, paper.files.length - 2);
            files += '<li class="more"><a href="' + paper.url + '">… ' + IndexView.escapeHtml(remaining) + '</a></li>';
        } else if (paper.files.length > 2) {
            files += '<li class="more"><a href="' + paper.url + '">… ' + IndexView.escapeHtml(this.textMore1) + '</a></li>'
        }

        let contentHtml = '<div class="type-address"><div class="type">' + IndexView.escapeHtml(paper.type) + '</div>' +
            '<div class="address">' + IndexView.escapeHtml(location.name) + '</div></div>' +
            '<div class="paper-title">' + paperHtml + '</div>' +
            '<ul class="files">' + files + '</ul>';
        marker.bindPopup(contentHtml, {className: 'file-location', minWidth: 200});
        clusterGroup.addLayer(marker);
        return marker;
    }
}
