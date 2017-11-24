from allauth.account.adapter import DefaultAccountAdapter
from allauth.utils import generate_unique_username


class AccountAdapter(DefaultAccountAdapter):
    def generate_unique_username(self, txts, regex=None):
        if txts[2] != "":
            return txts[2]
        else:
            return generate_unique_username(txts, regex)
