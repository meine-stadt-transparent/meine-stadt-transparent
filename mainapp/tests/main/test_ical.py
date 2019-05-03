import icalendar
from django.conf import settings
from django.test import TestCase

expected_meeting = """
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Meine Stadt Transparent//
BEGIN:VEVENT
SUMMARY:Meeting with Remy
DTSTART;TZID=Europe/Berlin;VALUE=DATE-TIME:20170910T120000
DTEND;TZID=Europe/Berlin;VALUE=DATE-TIME:20170910T180000
UID:meeting-1@meine-stadt-transparent.local
DESCRIPTION:Meeting with Remy Danton
LOCATION:The Captiol
END:VEVENT
END:VCALENDAR
""".strip().replace(
    "\n", "\r\n"
)

expected_meeting_series = """
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Meine Stadt Transparent//
BEGIN:VEVENT
SUMMARY:House Assembly 1
DTSTART;TZID=Europe/Berlin;VALUE=DATE-TIME:20170901T120000
DTEND;TZID=Europe/Berlin;VALUE=DATE-TIME:20170901T140000
UID:meeting-3@meine-stadt-transparent.local
DESCRIPTION:House Assembly Meeting 1
END:VEVENT
BEGIN:VEVENT
SUMMARY:House Assembly 2
DTSTART;TZID=Europe/Berlin;VALUE=DATE-TIME:20170908T120000
DTEND;TZID=Europe/Berlin;VALUE=DATE-TIME:20170908T140000
UID:meeting-4@meine-stadt-transparent.local
DESCRIPTION:House Assembly Meeting 2
END:VEVENT
BEGIN:VEVENT
SUMMARY:House Assembly 3
DTSTART;TZID=Europe/Berlin;VALUE=DATE-TIME:20170915T120000
DTEND;TZID=Europe/Berlin;VALUE=DATE-TIME:20170915T140000
UID:meeting-5@meine-stadt-transparent.local
DESCRIPTION:House Assembly Meeting 3 - Joint Meeting with Inquiry
END:VEVENT
BEGIN:VEVENT
SUMMARY:House Assembly 4
DTSTART;TZID=Europe/Berlin;VALUE=DATE-TIME:20170922T120000
DTEND;TZID=Europe/Berlin;VALUE=DATE-TIME:20170922T140000
UID:meeting-6@meine-stadt-transparent.local
DESCRIPTION:House Assembly Meeting 4
END:VEVENT
END:VCALENDAR
""".strip().replace(
    "\n", "\r\n"
)


class TestICal(TestCase):
    fixtures = ["initdata"]

    def test_meeting(self):
        reponse = self.client.get("/meeting/1/ical/").content.decode().strip()
        self.assertEqual(reponse, expected_meeting)

        event = icalendar.cal.Component.from_ical(reponse).subcomponents[0]
        self.assertEqual(event.get("dtstart").dt.tzinfo.zone, settings.TIME_ZONE)
        self.assertEqual(event.get("dtstart").dt.hour, 12)
        self.assertEqual(event.get("dtend").dt.tzinfo.zone, settings.TIME_ZONE)
        self.assertEqual(event.get("dtend").dt.hour, 18)

    def test_meeting_series(self):
        response = self.client.get("/organization/2/ical/").content.decode().strip()
        self.assertEqual(response, expected_meeting_series)
        self.assertEqual(
            len(icalendar.cal.Component.from_ical(response).subcomponents[0]), 5
        )

    def calendar(self):
        """ Just checks that no excpetion is thrown. """
        response = self.client.get("/calendar/ical")
        self.assertEqual(response.status_code, 200)
