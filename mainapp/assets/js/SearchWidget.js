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

// Build a querystring from the form
$("#searchform").submit(function (event) {
    event.preventDefault();
    let $inputs = $('#searchform :input');

    let searchterm = "";
    let querystring = "";
    let values = {};
    $inputs.each(function () {
        if ('searchterm' in values) {
            searchterm = values["searchterm"]
            delete values["searchterm"];
        }
        if (this.name !== "" && $(this).val() !== "") {
            if (this.name === "searchterm") {
                searchterm = $(this).val()
            } else {
                values[this.name] = $(this).val();
                querystring += "" + this.name + ":" + $(this).val() + " ";
            }
        }
    });

    querystring += searchterm;

    let searchParams = new URLSearchParams(window.location.search);
    searchParams.set("query", querystring);
    window.location.search = searchParams.toString();
});
