import style from '../css/mainapp.scss';
import HomeMap from "./HomeMap";

window.jQuery = require('jquery');

require('popper.js/dist/popper.js');
require('bootstrap/dist/js/bootstrap.js');

$(function() {
    console.log("Hello 🌍");

    $(".js-home-map").each(function() {
        new HomeMap($(this));
    });
});
