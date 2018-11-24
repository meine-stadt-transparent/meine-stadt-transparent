from django.test import TestCase, override_settings

from mainapp.models import Paper, File


@override_settings(
    ELASTICSEARCH_DSL_AUTOSYNC=False, ELASTICSEARCH_DSL_AUTO_REFRESH=False
)
class TestDocumentAccess(TestCase):
    fixtures = ["initdata"]
    base_paper_len = 2

    def test_delete_document(self):
        paper = Paper.objects.get(pk=1)

        file = File.objects.get(pk=2)
        file_papers = file.paper_set.all()
        self.assertEqual(self.base_paper_len, len(file_papers))

        # Now we delete the paper
        paper.deleted = True
        paper.save()

        file_papers = file.paper_set.all()
        self.assertEqual(self.base_paper_len - 1, len(file_papers))

        with self.assertRaises(Paper.DoesNotExist):
            Paper.objects.get(pk=1)

        # Now we restore it
        deleted_paper = Paper.objects_with_deleted.get(pk=1)
        deleted_paper.deleted = False
        deleted_paper.save()

        paper = Paper.objects.get(pk=1)
        self.assertEqual(1, paper.id)
        file_papers = file.paper_set.all()
        self.assertEqual(self.base_paper_len, len(file_papers))
