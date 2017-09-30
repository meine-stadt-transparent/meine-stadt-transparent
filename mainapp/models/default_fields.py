from django.db import models


class DefaultFields(models.Model):
    """
    These fields are mainly inspired and required by oparl
    """
    oparl_id = models.CharField(max_length=2000, null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    deleted = models.BooleanField(default=False)

    @staticmethod
    def by_oparl_id(oparl_id):
        return DefaultFields.objects.get(oparl_id=oparl_id)

    class Meta:
        abstract = True
