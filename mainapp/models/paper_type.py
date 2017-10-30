from django.db import models


class PaperType(models.Model):
    paper_type = models.CharField(max_length=200, unique=True)
