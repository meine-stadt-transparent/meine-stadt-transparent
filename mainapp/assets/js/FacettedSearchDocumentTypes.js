export default class FacettedSearchDocumentTypes {
    constructor($facet) {
        this.$facet = $facet;
        this.$facet.find(".dropdown-item").click(this.selectType.bind(this));
        this.toggleCancel();
        this.$facet.find(".cancel-selection").click(this.cancelSelection.bind(this));
        this.key = "document-type";
    }

    selectType(event) {
        if (event.target && event.target.nodeName === 'INPUT') {
            // Default behavior for the checkbox, however...
        } else {
            // ...for the surrounding label we need to explicitly code the behavior as otherwise
            // bootstrap would catch the event and use it to close the dropdown.
            event.stopPropagation();
            event.preventDefault();

            let $checkbox;
            if (event.target.nodeName === "LABEL") {
                $checkbox = $(event.target).find("input");
            } else {
                $checkbox = $(event.target).parents("label").first().find("input");
            }
            $checkbox.prop("checked", !$checkbox.prop("checked"));
            $checkbox.change();
        }
        this.toggleCancel();
    }

    toggleCancel() {
        if (this.$facet.find("input:checked").length > 0) {
            this.$facet.find(".cancel-selection").show();
        } else {
            this.$facet.find(".cancel-selection").hide();
        }
    }

    cancelSelection() {
        this.$facet.find("input").prop("checked", false);
        this.$facet.find(".cancel-selection").hide();
        this.$facet.find("input").change();
    }

    getQueryString() {
        let documentTypes = [];
        this.$facet.find('input[type=checkbox]').each((_, input) => {
            if ($(input).prop('checked')) {
                documentTypes.push($(input).val());
            }
        });
        documentTypes.sort();
        if (documentTypes.length > 0) {
            return 'document-type:' + documentTypes.join(',') + ' ';
        } else {
            return '';
        }
    }

    /**
     * Adds the item count to the values and hides away those with a count of zero. Also disables the button
     * when there is no value with a count biger than zero, unless a value is selected
     */
    update(data) {
        let $filter_list = $("#filter-" + this.key + "-list");

        for (let bucket_entry of data['new_facets']['document_type']['list']) {
            let $obj = $filter_list.find("[data-id=" + bucket_entry["name"] + "]");
            $obj.find(".facet-item-count").text(bucket_entry["count"]);
        }
    }

    setFromQueryString(params) {
        if (params['document-type']) {
            let types = params['document-type'].split(',');
            this.$facet.find("input").each((i, el) => {
                $(el).prop("checked", types.indexOf($(el).val()) !== -1);
            });
            this.$facet.find(".cancel-selection").show();
        } else {
            this.$facet.find("input").prop("checked", false);
            this.$facet.find(".cancel-selection").hide();
        }
    }
}
