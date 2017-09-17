import * as L from "leaflet/src/Leaflet";

export default class IndexView {
    constructor(map_element) {
        console.log("init map2");
        this.leaflet = L.map(map_element.attr('id'));

        L.tileLayer('https://api.tiles.mapbox.com/v4/{id}/{z}/{x}/{y}@2x.png?access_token=pk.eyJ1IjoidG9iaWFzaG9lc3NsIiwiYSI6ImNpeTMwdnFndTAwNDAzM21uaHpxYjZnNnEifQ.J_LAeL1849oRy4JK59X8cw', {
            attribution: 'Map data &copy; <a href="http://openstreetmap.org">OpenStreetMap</a> contributors, <a href="http://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA</a>, Imagery © <a href="http://mapbox.com">Mapbox</a>',
            maxZoom: 18,
            id: 'mapbox.streets',
            accessToken: 'pk.eyJ1IjoidG9iaWFzaG9lc3NsIiwiYSI6ImNpeTMwdnFndTAwNDAzM21uaHpxYjZnNnEifQ.J_LAeL1849oRy4JK59X8cw'
        }).addTo(this.leaflet);

        this.leaflet.setView(L.latLng(48.15509285476017, 11.542510986328125), 15);
    }
}
