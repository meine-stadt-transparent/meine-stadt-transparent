from django.test import TestCase
from django.utils import timezone

from importer.importer import Importer
from importer.tests.utils import (
    MockLoader,
    make_system,
    make_body,
    make_list,
    make_file,
    make_paper,
)
from mainapp.models import Paper, File

new_date = timezone.now().astimezone().replace(microsecond=0)


def build_mock_loader() -> MockLoader:
    system = make_system()
    body = make_body()
    loader = MockLoader(system)
    old_paper = make_paper([make_file(0), make_file(1)])
    loader.api_data = {
        system["id"]: system,
        system["body"]: make_list([body]),
        body["id"]: body,
        body["paper"]: make_list([old_paper]),
        body["person"]: make_list([]),
        body["organization"]: make_list([]),
        body["meeting"]: make_list([]),
    }

    return loader


def update(loader: MockLoader):
    changed_file = make_file(1)
    changed_file["name"] = "changed"
    new_paper = make_paper([changed_file, make_file(2)])
    loader.api_data[make_body()["paper"]] = make_list([new_paper])
    deleted_file = make_file(0)
    deleted_file["deleted"] = True
    loader.api_data[deleted_file["id"]] = deleted_file

    new_file = make_file(2)
    loader.api_data[new_file["id"]] = new_file


class TestEmbeddedUpdate(TestCase):
    body = make_body()

    def test_embedded_update(self):
        loader = build_mock_loader()
        importer = Importer(loader, force_singlethread=True)
        importer.run(self.body["id"])
        paper_id = make_paper([])["id"]
        self.assertEqual(Paper.objects.count(), 1)
        file_ids = Paper.by_oparl_id(paper_id).files.values_list("oparl_id", flat=True)
        self.assertEqual(sorted(file_ids), [make_file(0)["id"], make_file(1)["id"]])
        self.assertEqual(File.objects.count(), 2)

        update(loader)
        importer.update(self.body["id"])
        self.assertEqual(Paper.objects.count(), 1)
        self.assertEqual(File.objects.count(), 2)
        file_ids = Paper.by_oparl_id(paper_id).files.values_list("oparl_id", flat=True)
        self.assertEqual(sorted(file_ids), [make_file(1)["id"], make_file(2)["id"]])
        self.assertEqual(File.objects_with_deleted.count(), 3)

    def test_update_without_change_is_ignored(self):
        loader = build_mock_loader()
        importer = Importer(loader, force_singlethread=True)
        importer.run(self.body["id"])
        [paper] = Paper.objects.all()
        self.assertEqual(paper.history.count(), 1)

        # The "updated" list still contains the same paper object
        importer.update(self.body["id"])
        [paper] = Paper.objects.all()
        self.assertEqual(paper.history.count(), 1)

        # Consistency check: The count is increased if there is actual change
        update(loader)
        importer.update(self.body["id"])
        [paper] = Paper.objects.all()
        self.assertEqual(paper.history.count(), 2)
