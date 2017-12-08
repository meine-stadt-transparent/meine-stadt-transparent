import List from "list.js";

export default class MultiListFilter {
    constructor($baseElement) {
        this.$baseElement = $baseElement;
        let options = {
            valueNames: ['multi-list-filter-value']
        };

        this.sublists = this.$baseElement.find(".multi-list-filter-sublist").map((_, val) => {
            return new List(val, options);
        });

        this.$baseElement.find(".multi-list-filter-input").keyup((event) => {
            this.sublists.each((_, elem) => {
                elem.search($(event.currentTarget).val());
            });
        });
    }
}

