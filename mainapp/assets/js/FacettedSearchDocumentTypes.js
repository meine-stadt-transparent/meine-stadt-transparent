export default class FacettedSearchDocumentTypes {
    constructor($facet) {
        this.$facet = $facet;
        this.$facet.find(".dropdown-item").click(this.selectType.bind(this));
        this.toogleCancel();
        this.$facet.find(".cancel-selection").click(this.cancelSelection.bind(this));
    }

    selectType(event) {
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
        this.toogleCancel();
    }

    toogleCancel() {
        if (this.$facet.find("input:checked").length > 0) {
            this.$facet.find(".cancel-selection").show();
        } else {
            this.$facet.find(".cancel-selection").hide();
        }
    }

    cancelSelection() {
        this.$facet.find("input").prop("checked", false);
    }

    getQueryString() {
        let documentTypes = [];
        this.$facet.find('input[type=checkbox]').each((_, input) => {
            if ($(input).prop('checked')) {
                documentTypes.push($(input).val());
            }
        });
        if (documentTypes.length > 0) {
            return 'document-type:' + documentTypes.join(',') + ' ';
        } else {
            return '';
        }
    }
}
