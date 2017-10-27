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

// Build a querystring from the form
$("#searchform").submit(function (event) {
    event.preventDefault();

    let searchterm = "";
    let querystring = "";
    $('#searchform').find(':input').each(function () {
        let val = $(this).val();
        let name = this.name;
        // Skip empty values
        if (name === "" || val === "" || (Array.isArray(val) && val.length === 0)) {
            return;
        }

        if (name === "searchterm") {
            searchterm = val
        } else {
            querystring += "" + name + ":" + val + " ";
        }
    });

    querystring += searchterm;

    let searchParams = new URLSearchParams(window.location.search);
    searchParams.set("query", querystring);
    window.location.search = searchParams.toString();
});
