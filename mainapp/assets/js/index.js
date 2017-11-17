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


/*
 Convention: Each widget has an assigned object that handles the behavior.
 The object SHOULD only modify elements that lie within the root element,
 though there are several cases where this is not feasible.

 In case the widget should be modified from another object, a method on the object should be used,
 using the $(el).data("widget")-reference
 */

window.jQuery = require('jquery');

$(function () {
    $(".js-home-map").each(function () {
        $(this).data("widget", new HomeMap($(this)));
    });

    $(".search-autocomplete").each(function () {
        $(this).data("widget", new SearchBar($(this)));
    });

    $(".detailed-searchform").each(function() {
        $(this).data("widget", new FacettedSearch($(this)));
    });

    $("#start-endless-scroll").each(function() {
        $(this).data("widget", new EnlessScrolling($(this)));
    });
});
