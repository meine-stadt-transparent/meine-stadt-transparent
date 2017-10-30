import * as L from "leaflet/src/Leaflet";
import create_map from "./create_map";

export default class SearchForm {
    constructor($, $form) {
        this.$form = $form;
        this.$form.submit(this.submitForm.bind(this));
        this.initLocationSelector();
        this.initDocumentTypeSelector();
    }

    initDocumentTypeSelector() {
        this.$typeSelector = this.$form.find(".type-col");
        this.$typeSelector.find(".dropdown-menu").click((ev) => {
            let $checkbox = $(ev.target).find("input");
            $checkbox.prop("checked", !$checkbox.prop("checked"));
            ev.stopPropagation();
            ev.preventDefault();
        });
        this.$typeSelector.find(".dropdown").on("hidden.bs.dropdown", this.submitForm.bind(this));
    }

    initLocationSelector() {
        this.$locationSelector = this.$form.find(".location-col");
        this.leaflet = null;

        let mapIsInitialized = false;
        let currMarker = null;
        this.currPosition = null;
        this.$locationSelector.find(".dropdown").on("shown.bs.dropdown", () => {
            if (!mapIsInitialized) {
                let $mapElement = this.$form.find(".location-select-map");
                let initData = $mapElement.data("map-data");
                initData['zoom']--;
                this.leaflet = create_map($mapElement, initData);
                mapIsInitialized = true;

                this.leaflet.on("click", (ev) => {
                    if (currMarker) {
                        this.leaflet.removeLayer(currMarker);
                    }
                    this.currPosition = ev.latlng;
                    currMarker = new L.Marker(ev.latlng, {
                        icon: L.icon({
                            iconUrl: '/static/images/marker-icon-2x.png',
                            iconSize: [25, 41],
                            iconAnchor: [12.5, 41],
                            popupAnchor: [0, -35]
                        })
                    });
                    currMarker.addTo(this.leaflet);
                });
            }
        });
        this.$locationSelector.find(".select-btn").click(() => {
            if (this.currPosition) {
                this.$locationSelector.find("input[name=lat]").val(this.currPosition.lat);
                this.$locationSelector.find("input[name=lng]").val(this.currPosition.lng);
                this.$locationSelector.find("input[name=radius]").val(this.$locationSelector.find(".new-radius").val());
                this.$locationSelector.find(".dropdown").dropdown("toggle");
                this.submitForm();
            }
        });
        this.$locationSelector.find(".dropdown-menu").click((ev) => {
            ev.preventDefault();
            ev.stopPropagation();
        });
        this.setLocationString();
    }

    setLocationString() {
        let lat = this.$locationSelector.find("input[name=lat]").val(),
            lng = this.$locationSelector.find("input[name=lng]").val(),
            radius = this.$locationSelector.find("input[name=radius]").val(),
            $desc = this.$locationSelector.find(".location-description");

        if (lat !== "" && lng !== "" && radius > 0) {
            this.$locationSelector.find(".location-not-set").hide();
            $desc.find(".lat").text(Math.round(parseFloat(lat) * 1000) / 1000);
            $desc.find(".lng").text(Math.round(parseFloat(lng) * 1000) / 1000);
            $desc.find(".radius").text(radius);
            $desc.show();
        } else {
            this.$locationSelector.find(".location-not-set").show();
            $desc.hide();
        }
    }

    submitForm(event) {
        if (event) {
            event.preventDefault();
        }

        let searchterm = "";
        let querystring = "";
        let documentTypes = [];
        this.$form.find(':input[name]').each(function () {
            let val = $(this).val();
            let name = this.name;
            // Skip empty values
            if (name === "" || val === "" || (Array.isArray(val) && val.length === 0)) {
                return;
            }

            if (name === "searchterm") {
                searchterm = val
            } else if (name === 'document-type[]') {
                if ($(this).prop("checked")) {
                    documentTypes.push(val);
                }
            } else {
                querystring += "" + name + ":" + val + " ";
            }
        });
        if (documentTypes.length > 0) {
            querystring += "document-type:" + documentTypes.join(",") + " ";
        }

        querystring += searchterm;

        let searchParams = new URLSearchParams(window.location.search);
        searchParams.set("query", querystring);
        window.location.search = searchParams.toString();
    }
}
