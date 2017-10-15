require('typeahead.js/dist/typeahead.jquery');

export default class SearchWidget {
    constructor($, $widget) {
        let url = $widget.data('suggest-url');

        $widget.typeahead(null,
            {
                name: 'name',
                display: 'name',
                source: function (query, syncResults, asyncResults) {
                    $.get(url + query, function (data) {
                        console.log(data);
                        asyncResults(data);
                    });
                },
                limit: 10
            });

        $widget.on("typeahead:selected", function (ev, obj) {
            if (obj.url !== undefined) window.location.href = obj.url;
        })
    }
}
