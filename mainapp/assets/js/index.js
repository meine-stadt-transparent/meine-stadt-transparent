// noinspection ES6UnusedImports
import style from '../css/mainapp.scss';

import HomeMap from "./HomeMap";
import SearchBar from "./SearchBar";
import FacettedSearch from "./FacettedSearch";
import EnlessScrolling from "./EndlessScrolling";
// Force loading these images, as they are not referenced in the stylesheet but required by the JS library
// noinspection ES6UnusedImports
import img1 from "../../../node_modules/leaflet/dist/images/marker-icon-2x.png";
// noinspection ES6UnusedImports
import img2 from "../../../node_modules/leaflet/dist/images/marker-shadow.png";


window.jQuery = require('jquery');

$(function () {
    $(".js-home-map").each(function () {
        new HomeMap($(this));
    });

    $(".search-autocomplete").each(function () {
        new SearchBar($(this));
    });

    $(".detailed-searchform").each(function() {
        new FacettedSearch($(this));
    });

    $("#start-endless-scroll").each(function() {
        new EnlessScrolling($(this));
    });
});
