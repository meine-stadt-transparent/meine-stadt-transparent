let Mousetrap = require('mousetrap');

export default function trapMice() {
    Mousetrap.bind('alt+f', function () {
        $("#searchfield-mousetrap").focus();
    });
}
