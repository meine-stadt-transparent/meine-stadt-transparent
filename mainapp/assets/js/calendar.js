// noinspection ES6UnusedImports
import style from '../css/calendar.scss';
import moment from "moment";

require('fullcalendar');
require('fullcalendar/dist/locale/de');

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
            right: 'month,agendaWeek,agendaDay,listYear'
        },
        weekNumbers: true,
        navLinks: true, // can click day/week names to navigate views
        editable: true,
        defaultView: initView,
        defaultDate: initDate,
        eventLimit: true, // allow "more" link when too many events
        locale: language,
        events: dataSrc,
        timezone: 'local',
        eventClick: function (calEvent/*, jsEvent, view*/) {
            window.location.href = calEvent['details'];
        },
        viewRender: function (view/*, element*/) {
            if (view.name === defaultView && defaultDate.isBetween(view.start, view.end)) {
                window.history.pushState({}, "", $calendar.data("url-default"));
            } else {
                let url = $calendar.data("url-template")
                    .replace(/VIEW/, view.name)
                    .replace(/0000\-00\-00/, view.start.format('YYYY-MM-DD'));
                window.history.pushState({}, "", url);
            }
        }
    });
});
