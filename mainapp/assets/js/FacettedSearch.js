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

    onDatePickerChanged(start, end) {
        this.$form.find("input[name=before]").val(end.format("YYYY-MM-DD"));
        this.$form.find("input[name=after]").val(start.format("YYYY-MM-DD"));
        this.$form.find("input[name=after]").change();
        this.setDateRangeStr();
    }

    setDateRangeStr() {
        let before = this.$form.find("input[name=before]").val(),
            after = this.$form.find("input[name=after]").val(),
            found = false;

        if (after && before) {
            this.$openerBtn.find(".time-not-set").attr("hidden", "hidden");
            this.$openerBtn.find(".time-description").removeAttr("hidden");

            // Find an entry in this.dateRanges whose dates matches the selected values.
            // If an entry is found, the key is the descriptive string to be shown, ...
            Object.keys(this.dateRanges).forEach(dateRange => {
                if (
                    this.dateRanges[dateRange][0].format('YYYY-MM-DD') === after &&
                    this.dateRanges[dateRange][1].format('YYYY-MM-DD') === before
                ) {
                    found = true;
                    this.$openerBtn.find(".time-description").text(dateRange);
                }
            });

            // ...otherwise we just show the explicit date
            if (!found) {
                this.$openerBtn.find(".time-description").text(after + ' - ' + before);
            }
        } else {
            this.$openerBtn.find(".time-not-set").removeAttr("hidden");
            this.$openerBtn.find(".time-description").text("").attr("hidden", "hidden");
        }
    }

    onDatePickerCanceled() {
        this.$form.find('input[name=before]').val('');
        this.$form.find('input[name=after]').val('');
        this.$form.find('input[name=after]').change();
        this.setDateRangeStr();
    }

    buildDateRanges(strings) {
        this.dateRanges = {};
        this.dateRanges[strings['today']] = [moment(), moment()];
        this.dateRanges[strings['last_7d']] = [moment().subtract(6, 'days'), moment()];
        this.dateRanges[strings['this_month']] = [moment().startOf('month'), moment().endOf('month')];
        this.dateRanges[strings['last_month']] = [moment().subtract(1, 'month').startOf('month'), moment().subtract(1, 'month').endOf('month')];
        this.dateRanges[strings['this_year']] = [moment().subtract(1, 'year').startOf('year'), moment().subtract(1, 'year').endOf('year')];
    }

    initDatePicker() {
        this.$openerBtn = this.$form.find('#timeRangeButton');
        let strings = this.$openerBtn.data("strings");
        this.buildDateRanges(strings);
        this.setDateRangeStr();

        this.$openerBtn.daterangepicker({
            locale: {
                format: 'YYYY-MM-DD',
                applyLabel: strings['apply'],
                cancelLabel: strings['na'],
                customRangeLabel: strings['custom'],
                monthNames: strings['month_names'].split('|'),
                daysOfWeek: strings['day_names'].split('|'),
                firstDay: 1
            },
            opens: 'center',
            showDropdowns: true,
            showCustomRangeLabel: true,
            ranges: this.dateRanges
        }, this.onDatePickerChanged.bind(this));

        this.$openerBtn.on('cancel.daterangepicker', this.onDatePickerCanceled.bind(this));

        // Workaround to create a "toggling" behavior
        let closeOnClick = () => {
            $(document).trigger("mousedown.daterangepicker");
        };
        this.$openerBtn.on("show.daterangepicker", () => {
            // Wait until the current click event is safely gone
            window.setTimeout(() => {
                this.$openerBtn.on("click", closeOnClick);
            }, 500);
        });
        this.$openerBtn.on("hide.daterangepicker", () => {
            this.$openerBtn.off("click", closeOnClick);
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
            this.$locationSelector.find(".location-description").removeAttr("hidden");

            let $location = $desc.find(".location");
            if ($location.data("lat") == lat && $location.data("lng") == lng) {
                // The location has not changed, so just leave the text label untouched
                return;
            }

            $location.text("").data("lat", "").data("lng", "").attr("title", "");
            let url = this.$locationSelector.data("format-geo-url").replace(/\/23/, "/" + lat).replace(/42\//, lng + "/");
            $.get(url, (data) => {
                $location.text(data["formatted"]).data("lat", lat).data("lng", lng);
                this.$locationSelector.find("button").attr("title", data["formatted"]);
            });
            $desc.find(".radius").text(radius);
        } else {
            this.$locationSelector.find(".location-not-set").removeProp("hidden");
            $desc.attr("hidden", "hidden");
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
