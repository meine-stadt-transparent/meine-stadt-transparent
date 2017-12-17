import List from "list.js";

export default class FacettedSearchFilterDropdown {
    constructor($facet) {
        this.$facet = $facet;
        this.$input = $facet.find(".value");
        this.$items = this.$facet.find(".filter-item");
        this.key = $facet.data("filter-key");

        this.filterlist = new List($facet[0], {
            valueNames: ['name'],
            listClass: 'filter-list',
            searchClass: 'filter-input'
        });
        this.filterlist.sort('name', {order: "asc"});
        this.$items.click(this.itemSelected.bind(this));
        this.setLabel();
        this.$facet.find(".remove-filter > a").click(this.removeFilter.bind(this));
    }

    setLabel() {
        let id = this.$input.val();
        if (id) {
            let name = this.$items.filter("[data-id=" + id + "]").find(".name").text();
            this.$facet.find(".nothing-selected").hide();
            this.$facet.find(".selection").show().text(name);

            this.$facet.find(".remove-filter").show();
        } else {
            this.$facet.find(".nothing-selected").show();
            this.$facet.find(".selection").hide().text("");

            this.$facet.find(".remove-filter").hide();
        }
    }

    itemSelected(ev) {
        let $item = $(ev.currentTarget),
            id = $item.data("id");
        this.$input.val(id).trigger("change");
        this.setLabel();
        ev.preventDefault();
    }

    getQueryString() {
        if (this.$input.val()) {
            return this.key + ":" + this.$input.val() + " ";
        } else {
            return '';
        }
    }

    removeFilter(event) {
        this.$input.val("").trigger("change");
        this.setLabel();
        event.preventDefault();
    }
}
