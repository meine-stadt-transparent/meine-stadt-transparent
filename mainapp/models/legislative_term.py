from django.db import models

from mainapp.models.default_fields import DefaultFields


class LegislativeTerm(DefaultFields):
    name = models.CharField(max_length=200)
    start_date = models.DateField()
    end_date = models.DateField()