import List from "list.js";

export default class FacettedSearchFilterDropdown {
    constructor($facet) {
        this.$facet = $facet;
        console.log("init");
    }

    getQueryString() {
        return '';
    }
}
