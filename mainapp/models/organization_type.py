from django.db import models


class OrganizationType(models.Model):
    name = models.CharField(
        max_length=200, null=True
    )  # Null represents the unknown type

    def __str__(self):
        return self.name
