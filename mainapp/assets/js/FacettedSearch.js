import * as L from "leaflet/src/Leaflet";
import create_map from "./createMap";
// noinspection ES6UnusedImports
import style from "../css/datepicker.scss";

const moment = require('moment');

export default class FacettedSearch {
    constructor($form) {
        this.$form = $form;
        this.$refreshSpinner = $(".search-refreshing-spinner");

        this.initLocationSelector();
        this.initDocumentTypeSelector();
        this.initAutocomplete();
        this.initDatePicker();

        this.$form.submit(this.search.bind(this));
        this.$form.find("input").change(this.search.bind(this));
        this.$form.find("input").keyup(this.search.bind(this));
        this.$form.find("select").change(this.search.bind(this));
    }

    initDatePicker() {
        let $openerBtn = this.$form.find('#timeRangeButton'),
            $inputBefore = this.$form.find('input[name=before]'),
            $inputAfter = this.$form.find('input[name=after]');

        let ranges = {
            'Today': [moment(), moment()],
            'Last 7 Days': [moment().subtract(6, 'days'), moment()],
            'This Month': [moment().startOf('month'), moment().endOf('month')],
            'Last Month': [moment().subtract(1, 'month').startOf('month'), moment().subtract(1, 'month').endOf('month')],
            'This Year': [moment().startOf('year'), moment().endOf('year')],
            'Last Year': [moment().subtract(1, 'year').startOf('year'), moment().subtract(1, 'year').endOf('year')],
        };

        $openerBtn.daterangepicker({
            locale: {
                format: 'YYYY-MM-DD'
            },
            opens: 'center',
            showDropdowns: true,
            showCustomRangeLabel: true,
            ranges: ranges
        }, (start, end, label) => {
            if (ranges[label] !== undefined) {
                $openerBtn.find(".time-description").text(label);
            } else {
                $openerBtn.find(".time-description").text(start.format('YYYY-MM-DD') + ' - ' + end.format('YYYY-MM-DD'));
            }
            $openerBtn.find(".time-not-set").attr('hidden', 'hidden');
            $inputBefore.val(end.format('YYYY-MM-DD'));
            $inputAfter.val(start.format('YYYY-MM-DD'));
            $inputAfter.change();
        });

        $openerBtn.on('cancel.daterangepicker', () => {
            $openerBtn.find(".time-description").text('');
            $openerBtn.find(".time-not-set").removeAttr('hidden');
            $inputBefore.val('');
            $inputAfter.val('');
            $inputAfter.change();
        });

        // Workaround to create a "toggling" behavior
        let closeOnClick = () => {
            $(document).trigger("mousedown.daterangepicker");
        };
        $openerBtn.on("show.daterangepicker", () => {
            $openerBtn.on("click", closeOnClick);
        });
        $openerBtn.on("hide.daterangepicker", () => {
            $openerBtn.off("click", closeOnClick);
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
        $(".facet-dropdown .dropdown-item").click((event) => {
            if (event.target && event.target.nodeName === 'INPUT') {
                // Default behavior for the checkbox, however...
            } else {
                // ...for the surrounding label we need to explicitly code the behavior as otherwise
                // bootstrap would catch the event and use it to close the dropdown.
                event.stopPropagation();
                event.preventDefault();
                let $checkbox = $(event.target).find("input");
                $checkbox.prop("checked", !$checkbox.prop("checked"));
                $checkbox.change();
            }
        });
    }

    initLocationSelector() {
        this.$locationSelector = this.$form.find(".location-col");
        this.leaflet = null;

        let mapIsInitialized = false;
        this.currMarker = null;
        this.currPosition = null;
        this.initDropdownListener(mapIsInitialized);

        this.$locationSelector.find("input.new-radius").keyup((event) => {
            this.updateLocationData();
            event.preventDefault();
            event.stopPropagation();
        });
        this.$locationSelector.find(".select-btn").click(() => {
            this.updateLocationData();
            this.$locationSelector.find(".dropdown").dropdown("toggle");
        });
        this.$locationSelector.find(".dropdown-menu").click((event) => {
            event.preventDefault();
            event.stopPropagation();
        });
    }

    initDropdownListener(mapIsInitialized) {
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

                this.leaflet.on("click", (event) => {
                    this.setLocation(event.latlng);
                    this.updateLocationData();
                });
            }
            let latVal = this.$locationSelector.find("input[name=lat]").val();
            let lngVal = this.$locationSelector.find("input[name=lng]").val();
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

    updateLocationData() {
        if (this.currPosition && this.$locationSelector.find(".new-radius").val() > 0) {
            this.$locationSelector.find("input[name=lat]").val(this.currPosition.lat);
            this.$locationSelector.find("input[name=lng]").val(this.currPosition.lng);
            this.$locationSelector.find("input[name=radius]").val(this.$locationSelector.find(".new-radius").val());
            this.$locationSelector.find("input[name=radius]").change();
        }
    }

    updateLocationString() {
        let lat = this.$locationSelector.find("input[name=lat]").val(),
            lng = this.$locationSelector.find("input[name=lng]").val(),
            radius = this.$locationSelector.find("input[name=radius]").val(),
            $desc = this.$locationSelector.find(".location-description");

        if (lat !== "" && lng !== "" && radius > 0) {
            this.$locationSelector.find(".location-not-set").attr('hidden', 'hidden');

            $desc.find(".location").text("").attr("title", "");
            let url = this.$locationSelector.data('format-geo-url').replace(/\/23/, '/' + lat).replace(/42\//, lng + '/')
            $.get(url, (data) => {
                $desc.find(".location").text(data['formatted']);
                this.$locationSelector.find("button").attr("title", data['formatted']);
            });
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
        this.$form.find(':input[name]').each((_, input) => {
            let val = $(input).val();
            let name = input.name;
            // Skip empty values
            if (name === "" || val === "" || (Array.isArray(val) && val.length === 0)) {
                return;
            }

            if (name === "searchterm") {
                searchterm = val
            } else if (name === 'document-type[]') {
                if ($(input).prop("checked")) {
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
        $.get(url, (data) => {
            let $data = $(data['results']);
            let $btn = $("#start-endless-scroll");
            let current = $data.find("> li").length;
            let $nothingFound = $('.nothing-found');
            let $subscribeWidget = $(".subscribe-widget"); // Outside of this form to prevent nested forms
            if (parseInt(data['total_results'], 10) === 0) {
                $btn.attr('hidden', 'hidden');
                $nothingFound.removeAttr('hidden');
            } else if (data['total_results'] > current) {
                $btn.find('.total-hits').text(data['total_results'] - current);
                $btn.removeAttr('hidden');
                $nothingFound.attr('hidden', 'hidden');
            } else {
                $btn.attr('hidden', 'hidden');
                $nothingFound.attr('hidden', 'hidden');
            }
            $subscribeWidget.html(data['subscribe_widget']);
            $("#endless-scroll-target").html($data.find("> li"));
        });
    }

    search(event) {
        if (event) {
            event.preventDefault();
        }
        this.$refreshSpinner.removeAttr("hidden");
        let querystring = this.getQuerystring();

        let url = this.$form.attr("action").slice(0, -1) + querystring + "/";

        window.history.pushState({}, "", url);
        this.updateSearchResults(querystring);
        this.updateLocationString();
        this.$refreshSpinner.attr("hidden", "hidden");
    }
}
