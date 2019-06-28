import L from "leaflet";
import create_map from "./createMap";

/** A Map wher a marker can be placed with an input for the radius around the marker */
export default class LocationDropdown {
    constructor($widget) {
        this.$widget = $widget;
        this.leaflet = null;

        let mapIsInitialized = false;
        this.currMarker = null;
        this.currPosition = null;
        this.initDropdownListener(mapIsInitialized);

        this.$widget.find(".dropdown-menu").click((event) => {
            event.preventDefault();
            event.stopPropagation();
        });
    }

    initDropdownListener(mapIsInitialized) {
        this.$widget.on("shown.bs.modal", () => {
            if (!mapIsInitialized) {
                let location = this.$widget.data("location");
                let pos = new L.LatLng(location['coordinates'][1], location['coordinates'][0]);

                let $mapElement = this.$widget.find(".location-map");
                let initData = $mapElement.data("map-data");
                this.leaflet = create_map($mapElement, initData, false);
                this.leaflet.setView(pos, 16);
                mapIsInitialized = true;

                this.setLocation(pos);
            }
        });
    }

    setLocation(pos) {
        if (this.currMarker) {
            this.leaflet.removeLayer(this.currMarker);
        }
        this.currPosition = pos;
        this.currMarker = new L.Marker(pos);
        this.currMarker.addTo(this.leaflet);
    }
}
