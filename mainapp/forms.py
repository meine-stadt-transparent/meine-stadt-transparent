from django import forms
from django.contrib.auth.models import User


class EmailForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["email"]

    def __init__(self, *args, **kwargs):
        super(EmailForm, self).__init__(*args, **kwargs)
        self.fields["email"].required = True
