export default class FacettedSearchSorter {
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
    }

    getQueryString() {
        if (this.$input.val() !== this.$widget.data("default") && this.$input.val() !== "") {
            return "sort:" + this.$input.val() + " ";
        } else {
            return "";
        }
    }
}
