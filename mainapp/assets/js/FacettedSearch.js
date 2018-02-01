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
        this.$searchterm = this.$form.find("input[name=searchterm]");
        this.currentQueryString = null;

        this.facets = [
            new FacettedSearchSorter($form.find(".search-sort")),
            new FacettedSearchLocationSelector($form.find(".search-facet-location")),
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

        return querystring;
    }

    static parseQuerystring(str) {
        // Keep in sync with: mainapp/functions/search_tools.py
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
        let $data = $(data['results']);
        let $btn = $("#start-endless-scroll");
        let current = $data.find("> li").length;
        let $nothingFound = $('.nothing-found');
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
        $("#endless-scroll-target").html($data.find("> li"));
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
        if (this.currentQueryString === "") {
            // This would fail on the backend side (and it also wouldn't give reasonable results)
            return;
        }
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

        let url = this.$form.attr("action").slice(0, -1) + querystring + "/";

        console.log("Set: ", url);
        window.history.pushState({}, "", url);
        this.searchDo();
    }
}
