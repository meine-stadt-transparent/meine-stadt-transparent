// noinspection ES6UnusedImports
import style from '../css/mainapp.scss';

import HomeMap from "./HomeMap";
import SearchBar from "./SearchBar";
import FacettedSearch from "./FacettedSearch";
import EndlessScrolling from "./EndlessScrolling";
import MultiListFilter from "./MultiListFilter";
import LocationDropdown from "./LocationDropdown";
import trapMice from "./mousetrap";
// Force loading these images, as they are not referenced in the stylesheet but required by the JS library
// noinspection ES6UnusedImports
import img1 from "../../../node_modules/leaflet/dist/images/marker-icon-2x.png";
// noinspection ES6UnusedImports
import img2 from "../../../node_modules/leaflet/dist/images/marker-shadow.png";


window.jQuery = require('jquery');


/*
 Convention: Each widget has an assigned object that handles the behavior.
 The object SHOULD only modify elements that lie within the root element,
 though there are several cases where this is not feasible.

 In case the widget should be modified from another object, a method on the object should be used,
 using the $(el).data("widget")-reference
 */

let REGISTERED_CLASSES = {
    ".js-home-map": HomeMap,
    ".search-autocomplete": SearchBar,
    ".detailed-searchform": FacettedSearch,
    "#start-endless-scroll": EndlessScrolling,
    ".multi-list-filter": MultiListFilter,
    ".location-dropdown": LocationDropdown
};

$(function () {
    for (let selector in REGISTERED_CLASSES) {
        if (REGISTERED_CLASSES.hasOwnProperty(selector)) {
            $(selector).each(function () {
                try {
                    $(this).data("widget", new REGISTERED_CLASSES[selector]($(this)));
                } catch (e) {
                    console.error("Failed to initialize", selector, e)
                }
            });
        }
    }

    trapMice();
    // block: end prevents the page from scrolling down
    $(".scroll-into-view").each((_ ,element) => element.scrollIntoView({block: "end"}));
});
