require('corejs-typeahead/dist/typeahead.jquery');

export default class SearchWidget {
    constructor($, $widget) {
        this.$widget = $widget;
        this.$input = $widget.find("input");
        let url = this.$input.data('suggest-url');

        this.$input.typeahead(null,
            {
                name: 'name',
                display: 'name',
                source: function (query, syncResults, asyncResults) {
                    $.get(url + query, function (data) {
                        asyncResults(data);
                    });
                },
                limit: 5
            });

        this.$input.on("typeahead:selected", function (ev, obj) {
            if (obj.url !== undefined) window.location.href = obj.url;
        });

        this.$widget.submit(this.onSubmit.bind(this));
    }

    onSubmit(event) {
        event.preventDefault();

        let url = this.$widget.attr("action").slice(0, -1);
        let val = this.$widget.find(':input[name]').val();
        url = url + val + "/";

        window.location = url;
    }
}
