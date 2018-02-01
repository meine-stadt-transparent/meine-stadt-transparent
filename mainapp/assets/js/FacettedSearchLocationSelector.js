import * as L from "leaflet/src/Leaflet";
import create_map from "./createMap";

export default class FacettedSearchLocationSelector {
    constructor($facet) {
        this.$facet = $facet;
        this.leaflet = null;

        this.$inputLat = this.$facet.find("input[name=lat]");
        this.$inputLng = this.$facet.find("input[name=lng]");
        this.$inputRadius = this.$facet.find("input[name=radius]");

        let mapIsInitialized = false;
        this.currMarker = null;
        this.currPosition = null;
        this.initDropdownListener(mapIsInitialized);

        this.$facet.find("input.new-radius").keyup((event) => {
            this.updateLocationData();
            event.preventDefault();
            event.stopPropagation();
        });
        this.$facet.find(".select-btn").click(() => {
            this.updateLocationData();
            this.$facet.find(".dropdown").dropdown("toggle");
        });
        this.$facet.find(".dropdown-menu").click((event) => {
            event.preventDefault();
            event.stopPropagation();
        });
        this.$facet.find(".discard-btn").click(this.discardLocation.bind(this));
    }

    initDropdownListener(mapIsInitialized) {
        this.$facet.find(".dropdown").on("shown.bs.dropdown", () => {
            let $radius = this.$facet.find(".new-radius");
            if ($radius.val() < 1) {
                $radius.val($radius.data("default"));
            }
            if (!mapIsInitialized) {
                let $mapElement = this.$facet.find(".location-select-map");
                let initData = $mapElement.data("map-data");
                initData['zoom']--;
                this.leaflet = create_map($mapElement, initData);
                mapIsInitialized = true;

                this.leaflet.on("click", (event) => {
                    this.setLocation(event.latlng);
                    this.updateLocationData();
                });
            }
            let latVal = this.$facet.find("input[name=lat]").val();
            let lngVal = this.$facet.find("input[name=lng]").val();
            if (latVal && lngVal) {
                this.setLocation(new L.LatLng(latVal, lngVal));
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

    update(_) {
        this.updateLocationData();
    }

    updateLocationData() {
        if (this.currPosition && this.$facet.find(".new-radius").val() > 0) {
            this.$inputLat.val(this.currPosition.lat);
            this.$inputLng.val(this.currPosition.lng);
            this.$inputRadius.val(this.$facet.find(".new-radius").val());
            this.$inputRadius.change();
        }
    }

    updateLocationString() {
        let lat = this.$inputLat.val(),
            lng = this.$inputLng.val(),
            radius = this.$inputRadius.val(),
            $desc = this.$facet.find(".location-description");

        if (lat !== "" && lng !== "" && radius > 0) {
            this.$facet.find(".location-not-set").attr('hidden', 'hidden');
            this.$facet.find(".location-description").removeAttr("hidden");

            let $location = $desc.find(".location");
            if ($location.data("lat") === lat && $location.data("lng") === lng) {
                // The location has not changed, so just leave the text label untouched
                return;
            }

            $location.text("").data("lat", "").data("lng", "").attr("title", "");
            let url = this.$facet.data("format-geo-url").replace(/\/23/, "/" + lat).replace(/42\//, lng + "/");
            $.get(url, (data) => {
                $location.text(data["formatted"]).data("lat", lat).data("lng", lng);
                this.$facet.find("button").attr("title", data["formatted"]);
            });
            $desc.find(".radius").text(radius);
        } else {
            this.$facet.find(".location-not-set").removeAttr("hidden");
            $desc.attr("hidden", "hidden");
        }
    }

    getQueryString() {
        if (this.$inputRadius.val() > 0) {
            return 'lat:' + this.$inputLat.val() + ' lng:' + this.$inputLng.val() +
                ' radius:' + this.$inputRadius.val() + ' ';
        } else {
            return '';
        }
    }

    discardLocation() {
        if (this.currMarker) {
            this.leaflet.removeLayer(this.currMarker);
            this.currMarker = null;
        }
        this.currPosition = null;
        this.$inputRadius.val(0).change();
        this.updateLocationString();
        this.$facet.find(".dropdown").dropdown("toggle");
    }

    setFromQueryString(params) {
        if (params['lat'] && params['lng'] && params['radius']) {
            this.$inputLat.val(params['lat']);
            this.$inputLng.val(params['lng']);
            this.$inputRadius.val(params['radius']);
        } else {
            this.$inputLat.val('');
            this.$inputLng.val('');
            this.$inputRadius.val(0);
        }
        this.updateLocationString();
    }
}
