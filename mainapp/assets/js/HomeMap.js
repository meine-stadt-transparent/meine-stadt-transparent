import * as L from "leaflet/src/Leaflet";

export default class IndexView {
    escapeHtml(html) {
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

    getOutlineToPolygons(outline) {
        let polygons = [];
        if (typeof(outline) === 'string') {
            outline = JSON.parse(outline);
        }

        let coordsToPolygon = (coords) => {
            let latlngs = [];
            coords[0].forEach((lnglat) => {
                latlngs.push(L.latLng(lnglat[1], lnglat[0]));
            });
            polygons.push(L.polygon(latlngs, {}));
        };

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
    }

    geojsonToLocation(geojson) {
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
            console.log(location);
            for (let paper of Object.values(location.papers)) {
                let marker = L.marker(this.geojsonToLocation(location.coordinates), {
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
                    files += '<a href="' + paper.files[i].url + '">' + this.escapeHtml(paper.files[i].name) + '</a>';
                }

                let paperHtml = '<a href="' + paper.url + '">' + this.escapeHtml(paper.name) + '</a>';
                let contentHtml = '<div class="paper-title">' + paperHtml + '</div>' +
                    '<div class="file-location"><div class="location-name">' + this.escapeHtml(location.name) + '</div>' +
                    '<div class="files">' + files + '</div></div>';
                marker.bindPopup(contentHtml, {className: 'file-location', minWidth: 200});
                marker.addTo(this.leaflet);

                this.locationMarkers.push(marker);
            }
        }
    }

    constructor($map_element) {
        this.leaflet = L.map($map_element.attr('id'));

        L.tileLayer('https://api.tiles.mapbox.com/v4/{id}/{z}/{x}/{y}@2x.png?access_token=pk.eyJ1IjoidG9iaWFzaG9lc3NsIiwiYSI6ImNpeTMwdnFndTAwNDAzM21uaHpxYjZnNnEifQ.J_LAeL1849oRy4JK59X8cw', {
            attribution: 'Map data &copy; <a href="http://openstreetmap.org">OpenStreetMap</a> contributors, <a href="http://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA</a>, Imagery © <a href="http://mapbox.com">Mapbox</a>',
            maxZoom: 18,
            id: 'mapbox.streets',
            accessToken: 'pk.eyJ1IjoidG9iaWFzaG9lc3NsIiwiYSI6ImNpeTMwdnFndTAwNDAzM21uaHpxYjZnNnEifQ.J_LAeL1849oRy4JK59X8cw'
        }).addTo(this.leaflet);

        let initData = $map_element.data("map-data");

        let initCenter = L.latLng(35.658611, 139.745556); // If nothing else is said explicitly, we're probably talking about the Tokyo Tower
        let initZoom = 15;
        if (initData['center']) {
            initCenter = L.latLng(initData['center']['lat'], initData['center']['lng']);
        }
        if (initData['zoom']) {
            initZoom = initData['zoom'];
        }
        this.leaflet.setView(initCenter, initZoom);
        this.leaflet.setMinZoom(10);

        if (initData['limit']) {
            this.leaflet.setMaxBounds(L.latLngBounds(
                L.latLng(initData['limit']['min']['lat'], initData['limit']['min']['lng']),
                L.latLng(initData['limit']['max']['lat'], initData['limit']['max']['lng']),
            ));
        }

        if (initData['outline']) {
            this.getOutlineToPolygons(initData['outline']).forEach((polygon) => {
                this.leaflet.addLayer(polygon);
            });
        }

        if (initData['documents']) {
            this.addDocumentLocationMarkers(initData['documents']);
        }
    }
}
