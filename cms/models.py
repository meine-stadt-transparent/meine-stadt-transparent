from django.db import models
from django.utils.translation import gettext as _
from modelcluster.fields import ParentalKey
from wagtail.admin.edit_handlers import FieldPanel, InlinePanel
from wagtail.core.fields import RichTextField
from wagtail.core.models import Page, Orderable


class CMSPage(Page):
    # noinspection PyMethodOverriding
    def get_context(self, request):
        context = super().get_context(request)
        context["can_edit"] = self.permissions_for_user(request.user).can_edit()
        return context

    class Meta:
        abstract = True


class IndexPage(CMSPage):
    body = RichTextField(blank=True)

    content_panels = Page.content_panels + [FieldPanel("body", classname="full")]

    class Meta:
        verbose_name = _("The landing page for the cms section")


class ContentPage(CMSPage):
    body = RichTextField(blank=True)

    content_panels = Page.content_panels + [FieldPanel("body", classname="full")]

    class Meta:
        verbose_name = _("A page with a title and some content")


class GlossaryPage(CMSPage):
    body = RichTextField(blank=True)

    content_panels = Page.content_panels + [InlinePanel("entries")]

    class Meta:
        verbose_name = _("A glossary")


class GlossaryEntry(Orderable):
    page = ParentalKey(GlossaryPage, on_delete=models.CASCADE, related_name="entries")
    key = models.CharField(max_length=512)
    value = RichTextField()

    panels = [FieldPanel("key"), FieldPanel("value")]
