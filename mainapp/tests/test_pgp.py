from django.contrib.auth.models import User
from django.test import TestCase

from mainapp.models import UserProfile


class TestPGP(TestCase):
    def test_key_handling(self):
        user = User.objects.create_user(username="John Doe", email="doe@example.com")
        profile = UserProfile.objects.create(user=user)
        self.assertEqual(profile.get_pgp_key(), None)
        profile.add_pgp_key("FINGERPRINT", "CONTENTS")
        self.assertEqual(profile.get_pgp_key(), b"CONTENTS")
        profile.remove_pgp_key()
        self.assertEqual(profile.get_pgp_key(), None)
        user.delete()
