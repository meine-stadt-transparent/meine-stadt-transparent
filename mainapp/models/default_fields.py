from django.db import models


class DefaultFields(models.Model):
    """
    These fields are mainly inspired and required by oparl
    """
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)
    deleted = models.BooleanField(default=False)

    class Meta:
        abstract = True
