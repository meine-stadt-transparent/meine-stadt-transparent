import logging

from importer.loader import CCEgovLoader
from importer.tests.utils import spurious_500

logger = logging.getLogger(__name__)


def test_spurious_500(caplog):
    spurious_500(CCEgovLoader)
    assert caplog.messages == [
        "Got an 500 for a CC e-gov request, retrying: 500 Server Error: "
        "Internal Server Error for url: https://ratsinfo.leipzig.de/bi/oparl/1.0/papers.asp?body=2387&p=2"
    ]
