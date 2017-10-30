import style from '../css/mainapp.scss';

import HomeMap from "./HomeMap";
import SearchWidget from "./SearchWidget";
import SearchForm from "./SearchForm";

window.jQuery = require('jquery');

$(function () {
    $(".js-home-map").each(function () {
        new HomeMap($(this));
    });

    $(".search-autocomplete input").each(function() {
        new SearchWidget($, $(this));
    });
    $(".detailed-searchform").each(function() {
        new SearchForm($, $(this));
    })
});
