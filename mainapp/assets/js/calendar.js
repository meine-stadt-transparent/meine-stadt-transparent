// noinspection ES6UnusedImports
import style from '../css/calendar.scss';
import moment from "moment";

import * as fullcalendar from "fullcalendar";
require("fullcalendar/dist/locale/de");
import {FullCalendarMSTTheme} from "./FullCalendarMSTTheme";

fullcalendar.defineThemeSystem('mst', FullCalendarMSTTheme);

$(function () {
    let $calendar = $('#calendar'),
        language = $('html').attr('lang'),
        defaultView = $calendar.data('default-view'),
        defaultDate = moment($calendar.data('default-date'), "YYYY-MM-DD"),
        initView = $calendar.data('init-view'),
        initDate = $calendar.data('init-date'),
        dataSrc = $calendar.data('src');

    $calendar.fullCalendar({
        header: {
            left: 'prev,next today',
            center: 'title',
            right: 'month,agendaWeek,agendaDay listYear'
        },
        themeSystem: 'mst',
        weekNumbers: true,
        weekends: !$calendar.data('hide-weekends'),
        navLinks: true, // can click day/week names to navigate views
        editable: true,
        defaultView: initView,
        defaultDate: initDate,
        minTime: $calendar.data('min-time'),
        maxTime: $calendar.data('max-time'),
        eventLimit: true, // allow "more" link when too many events
        locale: language,
        events: dataSrc,
        timezone: 'local',
        eventClick: function (calEvent/*, jsEvent, view*/) {
            window.location.href = calEvent['details'];
        },

        // Make the single events tabbable; go to the event when the enter-key is pressed
        eventAfterRender: function (event, element, view) {
            $(element).attr("tabindex", "0").keyup((ev) => {
                if (ev.originalEvent.keyCode === 13) {
                    window.location.href = event['details'];
                }
            });
        },

        // Change the URL scheme when the view is changed
        viewRender: function (view, element) {
            if (view.name === defaultView && defaultDate.isBetween(view.start, view.end)) {
                if (typeof window.history.back() !== "undefined") {
                    window.history.pushState({}, "", $calendar.data("url-default"));
                }
            } else {
                let url = $calendar.data("url-template")
                    .replace(/VIEW/, view.name)
                    .replace(/0000\-00\-00/, view.start.format('YYYY-MM-DD'));
                window.history.pushState({}, "", url);
            }
        },

        // Show a loading spinner while data is loaded
        loading: (isLoading, view) => {
            // That code is managed by fullcalendar so we can't just put this in some template and hide it
            let spinner = '<div id="calendar-loading-spinner"><i class="fa fa-spinner fa-spin" ' +
                'aria-label="The calendar is loading data"></i></div>';
            let $base = $(".fc-center");
            if (isLoading) {
                $base.append(spinner);
                $base.find("h2").hide();
            } else {
                $base.find("#calendar-loading-spinner").remove();
                $base.find("h2").show();
            }
        }
    });
});
