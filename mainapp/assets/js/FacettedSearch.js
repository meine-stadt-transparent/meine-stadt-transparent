// noinspection ES6UnusedImports
import style from "../css/datepicker.scss";
import FacetFilterDropdown from "./facets/FilterDropdown";
import FacetDateRange from "./facets/DateRange";
import FacetLocationSelector from "./facets/LocationSelector";
import FacetDocumentTypes from "./facets/DocumentTypes";
import FacetSorter from "./facets/Sorting";

/**
 * General notes: All of the factes have inputs, which are used for passing the selected value around and for
 * communicating changed values (though jquery's change method)
 */
export default class FacettedSearch {
    constructor($form) {
        this.$form = $form;
        this.$refreshSpinner = $(".search-refreshing-spinner");
        this.$searchterm = this.$form.find("input[name=searchterm]");
        this.currentQueryString = null;
        this.orginalTitle = $form.attr("data-title-base");

        this.facets = [
            new FacetSorter($form.find(".search-sort")),
            new FacetLocationSelector($form.find(".search-facet-location")),
            new FacetDateRange($form.find(".search-facet-daterange")),
            new FacetDocumentTypes($form.find(".search-facet-document-type")),
        ];
        $form.find(".search-facet-filter-dropdown").each((_, el) => {
            this.facets.push(new FacetFilterDropdown($(el)));
        });

        this.$form.submit(this.search.bind(this));
        this.$form.find("input:not(.facet-internal)").change(this.search.bind(this));
        this.$form.find("input:not(.facet-internal)").keyup(this.search.bind(this));
        this.$form.find("select:not(.facet-internal)").change(this.search.bind(this));

        $(window).on("hashchange", this.hashchanged.bind(this));
        $(window).on("popstate", this.hashchanged.bind(this));
    }


    getQuerystring() {
        let querystring = "";
        this.facets.forEach((facet) => {
            querystring += facet.getQueryString();
        });
        querystring += this.$searchterm.val();
        querystring = querystring.replace(/^\s/, '').replace(/\s$/, '');

        document.title = this.orginalTitle + ': ' + this.$searchterm.val();

        return querystring;
    }

    static parseQuerystring(str) {
        // Keep in sync with: mainapp/functions/search.py
        const known_params = ["document-type", "radius", "lat", "lng", "person", "organization", "after", "before", "sort"];

        str = str.replace(/ {2,}/, ' ').replace(/^ /, '').replace(/ $/, '');
        let params = {},
            search_words = [];
        str.split(' ').forEach((str_part) => {
            let str_split = str_part.split(':');
            if (str_split.length === 2 && known_params.indexOf(str_split[0]) !== -1) {
                params[str_split[0]] = str_split[1];
            } else {
                search_words.push(str_part);
            }
        });
        if (search_words.length > 0) {
            params['searchterm'] = search_words.join(' ');
        }
        return params;
    }

    static updateEndlessScroll(data) {
        // noinspection JSJQueryEfficiency
        let endlessScroll = $("#start-endless-scroll").data('widget');
        let $data = $(data['results']);
        // Replace the complete search results section with the new content
        $("#results-section").html($data);
        // noinspection JSJQueryEfficiency
        let $newBtn = $("#start-endless-scroll");
        endlessScroll.reset();
        endlessScroll.retarget($newBtn);
        $newBtn.data("widget", endlessScroll);
    }

    updateSearchResults(querystring) {
        let url = this.$form.data("results-only-url").slice(0, -1) + querystring + "/";
        $.get(url, (data) => {
            if (querystring !== this.currentQueryString) {
                // This request probably had too much latency and there is another request going on (or completed) already
                return;
            }
            FacettedSearch.updateEndlessScroll(data);

            // Outside of the form to prevent nested forms
            $(".subscribe-widget").html(data['subscribe_widget']);

            for (let facet of this.facets) {
                if (typeof facet.update === 'function') {
                    facet.update(data);
                }
            }

            let url = this.$form.attr("action").slice(0, -1) + data['query'] + "/";

            window.history.pushState({}, "", url);

            $(".search-feed").attr("href", url + "feed/")

            this.$refreshSpinner.attr("hidden", "hidden");
        });
    }

    setFields(params) {
        this.$searchterm.val(params['searchterm'] ? params['searchterm'] : '');
        this.facets.forEach((facet) => {
            facet.setFromQueryString(params);
        });
    }

    hashchanged() {
        let query = decodeURI(window.location.href);
        if (query.indexOf(this.$form.attr("action").slice(0, -1)) === -1) {
            return;
        }
        query = query.split(this.$form.attr("action").slice(0, -1))[1].replace(/\/$/, '');
        if (query === this.currentQueryString) {
            return;
        }

        this.setFields(FacettedSearch.parseQuerystring(query));

        this.currentQueryString = this.getQuerystring();
        this.searchDo();
    }

    searchDo() {
        this.$refreshSpinner.removeAttr("hidden");
        this.updateSearchResults(this.currentQueryString);
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

        // We only need this for the tests, but conditional compilation with js is painful so it stays either way
        this.$searchterm.attr("data-querystring", querystring);

        this.searchDo();
    }
}
