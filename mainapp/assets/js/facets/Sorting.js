/** The default is relevance, the others are newest first and oldest first */
export default class FacetSorter {
    constructor($widget) {
        this.$widget = $widget;
        this.$input = $widget.find("input[type=hidden]");
        this.$items = $widget.find(".dropdown-item");
        this.setLabel();
        this.$items.on("click", this.sortSelected.bind(this));
        this.$input.on("change", this.setLabel.bind(this));
    }

    setLabel() {
        let val = this.$input.val();
        if (val === '') {
            val = this.$widget.data("default");
        }
        let name = this.$items.filter("[data-sort=" + val + "]").text();
        this.$widget.find(".current-mode").text(name);
    }

    sortSelected(ev) {
        let val = $(ev.currentTarget).data('sort');
        this.$input.val(val).trigger("change");
        ev.preventDefault();
    }

    getQueryString() {
        if (this.$input.val() !== this.$widget.data("default") && this.$input.val() !== "") {
            return "sort:" + this.$input.val() + " ";
        } else {
            return "";
        }
    }

    setFromQueryString(params) {
        if (params['sort']) {
            this.$input.val(params['sort']);
        } else {
            this.$input.val('relevance');
        }
        this.setLabel();
    }
}
