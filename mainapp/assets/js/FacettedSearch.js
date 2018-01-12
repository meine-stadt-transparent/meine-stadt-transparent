// noinspection ES6UnusedImports
import style from "../css/datepicker.scss";
import FacettedSearchFilterDropdown from "./FacettedSearchFilterDropdown";
import FacettedSearchDateRange from "./FacettedSearchDateRange";
import FacettedSearchLocationSelector from "./FacettedSearchLocationSelector";
import FacettedSearchDocumentTypes from "./FacettedSearchDocumentTypes";
import FacettedSearchSorter from "./FacettedSearchSorter";

export default class FacettedSearch {
    constructor($form) {
        this.$form = $form;
        this.$refreshSpinner = $(".search-refreshing-spinner");
        this.currentQueryString = null;

        this.initAutocomplete();

        this.locationSelector = new FacettedSearchLocationSelector($form.find(".search-facet-location"));
        this.facets = [
            new FacettedSearchSorter($form.find(".search-sort")),
            this.locationSelector,
            new FacettedSearchDateRange($form.find(".search-facet-daterange")),
            new FacettedSearchDocumentTypes($form.find(".search-facet-document-type")),
        ];
        $form.find(".search-facet-filter-dropdown").each((_, el) => {
            this.facets.push(new FacettedSearchFilterDropdown($(el)));
        });

        this.$form.submit(this.search.bind(this));
        this.$form.find("input:not(.facet-internal)").change(this.search.bind(this));
        this.$form.find("input:not(.facet-internal)").keyup(this.search.bind(this));
        this.$form.find("select:not(.facet-internal)").change(this.search.bind(this));
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

    getQuerystring() {
        let querystring = "";
        this.facets.forEach((facet) => {
            querystring += facet.getQueryString();
        });
        querystring += this.$form.find("input[name=searchterm]").val();
        querystring = querystring.replace(/^\s/, '').replace(/\s$/, '');

        return querystring;
    }

    updateSearchResults(querystring) {
        let url = this.$form.data("results-only-url").slice(0, -1) + querystring + "/";
        $.get(url, (data) => {
            if (querystring !== this.currentQueryString) {
                // This request probably had too much latency and there is another request going on (or completed) already
                return;
            }

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
            $btn.data('url', data['more_link']);
            $btn.data('widget').reset();
            $subscribeWidget.html(data['subscribe_widget']);
            $("#endless-scroll-target").html($data.find("> li"));

            this.locationSelector.updateLocationString();

            for (let facet of this.facets) {
                if (typeof facet.update === 'function') {
                    facet.update(data);
                }
            }
            this.$refreshSpinner.attr("hidden", "hidden");
        });
    }

    search(event) {
        if (event) {
            event.preventDefault();
        }
        let querystring = this.getQuerystring();
        if (querystring === this.currentQueryString) {
            // Prevents double loading of the same result when additional change-events occur
            return;
        }
        this.currentQueryString = querystring;

        let url = this.$form.attr("action").slice(0, -1) + querystring + "/";

        window.history.pushState({}, "", url);

        if (querystring === "") {
            // This would fail on the backend side (and it also wouldn't give reasonable results)
            return;
        }
        this.$refreshSpinner.removeAttr("hidden");
        this.updateSearchResults(querystring);
    }
}
