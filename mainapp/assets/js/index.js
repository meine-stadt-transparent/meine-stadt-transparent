import style from '../css/mainapp.scss';
import HomeMap from "./HomeMap";

window.jQuery = require('jquery');

$(function() {
    console.log("Hello 🌍");

    $(".js-home-map").each(function() {
        new HomeMap($(this));
    });
});
