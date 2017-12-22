let Mousetrap = require('mousetrap');

export default function trapMice() {
    Mousetrap.bind('alt+f', function () {
        $(".search-autocomplete input").focus();
    });
}