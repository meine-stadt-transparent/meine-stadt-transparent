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
                limit: 5
            });

        $widget.on("typeahead:selected", function (ev, obj) {
            if (obj.url !== undefined) window.location.href = obj.url;
        })
    }
}

// Remove empty fields from url
// https://stackoverflow.com/a/8029581/3549270
$("#searchform").submit(function () {
    $(this)
        .find('input[name]')
        .filter(function () {
            return !this.value;
        })
        .prop('name', '');
});
