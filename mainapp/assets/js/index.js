// noinspection ES6UnusedImports
import style from '../css/mainapp.scss';

//import * as Sentry from '@sentry/browser';

import HomeMap from "./HomeMap";
import SearchBar from "./SearchBar";
import FacettedSearch from "./FacettedSearch";
import EndlessScrolling from "./EndlessScrolling";
import MultiListFilter from "./MultiListFilter";
import LocationDropdown from "./LocationDropdown";
import PgpUi from "./pgp-ui";

import trapMice from "./mousetrap";
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

let REGISTERED_CLASSES = {
    ".js-home-map": HomeMap,
    ".search-autocomplete": SearchBar,
    ".detailed-searchform": FacettedSearch,
    "#start-endless-scroll": EndlessScrolling,
    ".multi-list-filter": MultiListFilter,
    ".location-dropdown": LocationDropdown,
    "#select-pgp-key-box": PgpUi
};

// initialize everything
$(function () {
    /*let dsnElement = document.getElementById("sentry-dsn");
    if (dsnElement !== null) {
        Sentry.init({
            dsn: dsnElement.dataset["sentryDsn"],
        });
    }*/

    // Allow webpack to optimize bootstrap into the vendor bundle
    import('bootstrap').then(_ => {
        for (let selector in REGISTERED_CLASSES) {
            if (REGISTERED_CLASSES.hasOwnProperty(selector)) {
                $(selector).each(function () {
                    $(this).data("widget", new REGISTERED_CLASSES[selector]($(this)));
                });
            }
        }
    });

    trapMice();
    // block: end prevents the page from scrolling down
    $(".scroll-into-view").each((_, element) => element.scrollIntoView({block: "end"}));
});

// Easy linking to tabs e.g. on the organization page
$(function () {
    import('bootstrap').then(bootstrap => {
        // https://github.com/twbs/bootstrap/issues/25220#issuecomment-379216474
        const anchor = window.location.hash;
        let tab;
        if (anchor !== "") {
            tab = document.querySelector(`a[href="${anchor}"]`);
        } else {
            tab = document.querySelector('a.nav-link.mst-active');
        }
        if (tab !== null) {
            (new bootstrap.Tab(tab)).show();
        }
        // https://getbootstrap.com/docs/5.0/components/list-group/#events
        let tabElms = document.querySelectorAll('a[data-bs-toggle="tab"]')
        tabElms.forEach(function (tabElm) {
            tabElm.addEventListener('shown.bs.tab', function (event) {
                history.pushState({}, '', event.target.hash);
            })
        });
    });
});

$(function () {
    // Styling inspired by the public domain https://github.com/b44rd/jsbug/blob/master/jsbug.js
    //let style = "color: #000;font-size:12pt;font-weight:normal;padding:2px;background-color: #44A2C0";
    //console.log("%cHey there!", style);
    //console.log("%cWant to help to make Meine Stadt Transparent even better?", style);
    //console.log("%cWe're small, friendly and well-documented project always happy about contributions, whether it is code, design or something else", style);
    //console.log("%chttps://github.com/meine-stadt-transparent/meine-stadt-transparent", style)
});
