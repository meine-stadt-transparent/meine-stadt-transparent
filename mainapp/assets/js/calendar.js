import style from '../css/calendar.scss';

require('fullcalendar');
require('fullcalendar/dist/locale/de');

$(function () {
    let $calendar = $('#calendar'),
        language = $('html').attr('lang'),
        defaultView = $calendar.data('default-view'),
        dataSrc = $calendar.data('src');

    $calendar.fullCalendar({
        header: {
            left: 'prev,next today',
            center: 'title',
            right: 'month,agendaWeek,agendaDay,listMonth'
        },
        weekNumbers: true,
        navLinks: true, // can click day/week names to navigate views
        editable: true,
        defaultView: defaultView,
        eventLimit: true, // allow "more" link when too many events
        locale: language,
        events: dataSrc,
        timezone: 'local',
        eventClick: function(calEvent/*, jsEvent, view*/) {
            window.location.href = calEvent['details'];
        }
    });
});
