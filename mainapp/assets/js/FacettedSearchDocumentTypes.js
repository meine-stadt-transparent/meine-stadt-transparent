export default class FacettedSearchDocumentTypes {
    constructor($facet) {
        this.$facet = $facet;
        $facet.find(".dropdown-item").click(this.onClick.bind(this));
    }

    onClick(event) {
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
