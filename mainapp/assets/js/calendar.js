// noinspection ES6UnusedImports
import style from '../css/calendar.scss';

import {Calendar} from '@fullcalendar/core';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import listPlugin from '@fullcalendar/list';
import bootstrapPlugin from '@fullcalendar/bootstrap';
import deLocale from '@fullcalendar/core/locales/de';
import enLocale from '@fullcalendar/core/locales/en-gb';

document.addEventListener('DOMContentLoaded', function () {
    let calendarEl = document.getElementById('calendar');
    let calendar = new Calendar(calendarEl, {
        plugins: [dayGridPlugin, timeGridPlugin, listPlugin, bootstrapPlugin],
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,timeGridWeek,timeGridDay listYear'
        },
        themeSystem: 'bootstrap',
        events: document.getElementById('calendar').dataset.src,
        locales: [deLocale, enLocale],
        locale: "de",
        weekends: !document.getElementById('calendar').dataset.hideWeekends,
        slotMinTime: document.getElementById('calendar').dataset.minTime,
        slotMaxTime: document.getElementById('calendar').dataset.maxTime,
        navLinks: true, // can click day/week names to navigate views
        eventLimit: true, // allow "more" link when too many events
        //expandRows: true,

        // Show a loading spinner while data is loaded
        loading: (isLoading) => {
            // That code is managed by fullcalendar so we can't just put this in some template and hide it
            let spinner = '<div id="calendar-loading-spinner"><i class="fa fa-spinner fa-spin" ' +
                'aria-label="The calendar is loading data"></i></div>';
            let base_ = document.getElementsByClassName("fc-toolbar-title")[0]?.parentElement;
            if (base_) {
                if (isLoading) {
                    base_.insertAdjacentHTML('beforeend', spinner);
                    base_.firstChild.hidden = true;
                } else {
                    document.getElementById("calendar-loading-spinner")?.remove();
                    base_.firstChild.hidden = false;
                }
            }
        },

        // Make the single events tabbable; go to the event when the enter-key is pressed
        todoAfterRender: function (event, element, view) {
            console.log("TABBING");
            $(element).attr("tabindex", "0").keyup((ev) => {
                if (ev.originalEvent.keyCode === 13) {
                    window.location.href = event['details'];
                }
            });
        },

        // Change the URL scheme when the view is changed
        todoViewRender: function (view, element) {
            if (view.name === defaultView && defaultDate.isBetween(view.start, view.end)) {
                if (typeof window.history.back !== "undefined") {
                    window.history.pushState({}, "", $calendar.data("url-default"));
                }
            } else {
                let url = $calendar.data("url-template")
                    .replace(/VIEW/, view.name)
                    .replace(/0000-00-00/, view.start.format('YYYY-MM-DD'));
                window.history.pushState({}, "", url);
            }
        },
    })

    calendar.render();
});

// import * as fullcalendar from "fullcalendar";
//
// require("fullcalendar/dist/locale/de");
//
// fullcalendar.defineThemeSystem('mst', FullCalendarMSTTheme);
//
// $(function () {
//     let $calendar = $('#calendar'),
//         language = $('html').attr('lang'),
//         defaultView =min_time $calendar.data('default-view'),
//         defaultDate = moment($calendar.data('default-date'), "YYYY-MM-DD"),
//         initView = $calendar.data('init-view'),
//         initDate = $calendar.data('init-date'),
//         dataSrc = $calendar.data('src');
//
//     $calendar.fullCalendar({
//         header: {
//             left: 'prev,next today',
//             center: 'title',
//             right: 'month,agendaWeek,agendaDay listYear'
//         },
//         themeSystem: 'mst',
//         weekNumbers: true,
//         weekends: !$calendar.data('hide-weekends'),
//         navLinks: true, // can click day/week names to navigate views
//         editable: true,
//         defaultView: initView,
//         defaultDate: initDate,
//         minTime: $calendar.data('min-time'),
//         maxTime: $calendar.data('max-time'),
//         eventLimit: true, // allow "more" link when too many events
//         locale: language,
//         events: dataSrc,
//         timezone: 'local',
//         eventClick: function (calEvent/*, jsEvent, view*/) {
//             window.location.href = calEvent['details'];
//         },
//
//         // Make the single events tabbable; go to the event when the enter-key is pressed
//         eventAfterRender: function (event, element, view) {
//             $(element).attr("tabindex", "0").keyup((ev) => {
//                 if (ev.originalEvent.keyCode === 13) {
//                     window.location.href = event['details'];
//                 }
//             });
//         },
//
//         // Change the URL scheme when the view is changed
//         viewRender: function (view, element) {
//             if (view.name === defaultView && defaultDate.isBetween(view.start, view.end)) {
//                 if (typeof window.history.back !== "undefined") {
//                     window.history.pushState({}, "", $calendar.data("url-default"));
//                 }
//             } else {
//                 let url = $calendar.data("url-template")
//                     .replace(/VIEW/, view.name)
//                     .replace(/0000-00-00/, view.start.format('YYYY-MM-DD'));
//                 window.history.pushState({}, "", url);
//             }
//         },
//
//         // Show a loading spinner while data is loaded
//         loading: (isLoading, view) => {
//             // That code is managed by fullcalendar so we can't just put this in some template and hide it
//             let spinner = '<div id="calendar-loading-spinner"><i class="fa fa-spinner fa-spin" ' +
//                 'aria-label="The calendar is loading data"></i></div>';
//             let $base = $(".fc-center");
//             if (isLoading) {
//                 $base.append(spinner);
//                 $base.find("h2").hide();
//             } else {
//                 $base.find("#calendar-loading-spinner").remove();
//                 $base.find("h2").show();
//             }
//         }
//     });
// });
