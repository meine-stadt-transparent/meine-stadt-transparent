import * as L from "leaflet/src/Leaflet";
import create_map from "./createMap";
// noinspection ES6UnusedImports
import style from "../css/datepicker.scss";

require("bootstrap-datepicker/dist/js/bootstrap-datepicker");


export default class FacettedSearch {
    constructor($form) {
        this.$form = $form;
        this.$form.submit(this.search.bind(this));
        this.initLocationSelector();
        this.initDocumentTypeSelector();
        this.initAutocomplete();
        this.initDatePicker();
    }

    initDatePicker() {
        $("input#after").datepicker({
            format: "yyyy-mm-dd"
        });
        $("input#before").datepicker({
            format: "yyyy-mm-dd"
        });
        $(".searchclear").click((event) => {
            $(event.target).parent().parent().find("input").val("");
            this.search();
        });
    }

    initAutocomplete() {
        let $widget = this.$form.find(".searchterm-row input[name=searchterm]");
        let url = $widget.data('suggest-url');

        $widget.typeahead(null,
            {
                name: 'name',
                display: 'name',
                source: (query, syncResults, asyncResults) => {
                    $.get(url + query, function (data) {
                        asyncResults(data);
                    });
                },
                limit: 5
            });

        $widget.on("typeahead:selected", function (ev, obj) {
            if (obj.url !== undefined) window.location.href = obj.url;
        });
    }

    initDocumentTypeSelector() {
        $(".facet-dropdown .dropdown-item").click((ev) => {
            let $checkbox = $(ev.target).find("input");
            $checkbox.prop("checked", !$checkbox.prop("checked"));
            this.search();

            ev.stopPropagation();
            ev.preventDefault();
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

    initLocationSelector() {
        this.$locationSelector = this.$form.find(".location-col");
        this.leaflet = null;

        let mapIsInitialized = false;
        this.currMarker = null;
        this.currPosition = null;
        this.$locationSelector.find(".dropdown").on("shown.bs.dropdown", () => {
            let $radius = this.$locationSelector.find(".new-radius");
            if ($radius.val() < 1) {
                $radius.val($radius.data("default"));
            }
            if (!mapIsInitialized) {
                let $mapElement = this.$form.find(".location-select-map");
                let initData = $mapElement.data("map-data");
                initData['zoom']--;
                this.leaflet = create_map($mapElement, initData);
                mapIsInitialized = true;

                this.leaflet.on("click", (ev) => {
                    this.setLocation(ev.latlng)
                });
            }
            if (this.$locationSelector.find("input[name=lat]").val() && this.$locationSelector.find("input[name=lng]").val()) {
                this.setLocation(new L.LatLng(
                    this.$locationSelector.find("input[name=lat]").val(),
                    this.$locationSelector.find("input[name=lng]").val()
                ));
            }
        });
        this.$locationSelector.find(".select-btn").click(() => {
            if (this.currPosition && this.$locationSelector.find(".new-radius").val() > 0) {
                this.$locationSelector.find("input[name=lat]").val(this.currPosition.lat);
                this.$locationSelector.find("input[name=lng]").val(this.currPosition.lng);
                this.$locationSelector.find("input[name=radius]").val(this.$locationSelector.find(".new-radius").val());
                this.$locationSelector.find(".dropdown").dropdown("toggle");
                this.search();
            }
        });
        this.$locationSelector.find(".dropdown-menu").click((ev) => {
            ev.preventDefault();
            ev.stopPropagation();
        });
    }

    updateLocationString() {
        let lat = this.$locationSelector.find("input[name=lat]").val(),
            lng = this.$locationSelector.find("input[name=lng]").val(),
            radius = this.$locationSelector.find("input[name=radius]").val(),
            $desc = this.$locationSelector.find(".location-description");

        if (lat !== "" && lng !== "" && radius > 0) {
            this.$locationSelector.find(".location-not-set").attr('hidden', 'hidden');
            let latText = (Math.round(parseFloat(lat) * 1000) / 1000).toLocaleString();
            $desc.find(".lat").text(latText);
            let lngText = (Math.round(parseFloat(lng) * 1000) / 1000).toLocaleString();
            $desc.find(".lng").text(lngText);
            $desc.find(".radius").text(radius);
            this.$locationSelector.find(".location-description").removeAttr('hidden');
        } else {
            this.$locationSelector.find(".location-not-set").removeProp('hidden');
            $desc.attr('hidden', 'hidden');
        }
    }

    getQuerystring() {
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

        return querystring;
    }

    updateSearchResults(querystring) {
        let url = this.$form.data("results-only-url").slice(0, -1) + querystring;
        $.get(url, function (data) {
            let $data = $(data);
            let $btn = $("#start-endless-scroll");
            let total = parseInt($data.data("total-hits"));
            let current = $data.find("> li").length;
            if (total > current) {
                $btn.find(".total-hits").text(total - current);
                $btn.removeProp('hidden');
            } else {
                $btn.prop('hidden', 'hidden');
            }
            $("#endless-scroll-target").html($data.find("> li"));
        });
    }

    search(event) {
        if (event) {
            event.preventDefault();
        }
        let querystring = this.getQuerystring();

        let url = this.$form.attr("action").slice(0, -1) + querystring + "/";

        window.history.pushState({}, "", url);
        this.updateSearchResults(querystring);
        this.updateLocationString();
    }
}
