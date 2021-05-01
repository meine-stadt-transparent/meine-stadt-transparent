from django.test import TestCase


class TestViews(TestCase):
    fixtures = ["initdata"]

    def test_meeting_navigation(self):
        """5 is joined with another committee, so it's skipped in this meeting series"""
        contexts = {}
        for i in [3, 4, 5, 6]:
            contexts[i] = self.client.get("/meeting/{}/".format(i)).context
        self.assertEqual(contexts[3]["previous"], None)
        self.assertEqual(contexts[3]["following"].id, 4)
        self.assertEqual(contexts[4]["previous"].id, 3)
        self.assertEqual(contexts[4]["following"].id, 6)
        self.assertTrue("previous" not in contexts[5])
        self.assertTrue("previous" not in contexts[5])
        self.assertEqual(contexts[6]["previous"].id, 4)
        self.assertEqual(contexts[6]["following"], None)
