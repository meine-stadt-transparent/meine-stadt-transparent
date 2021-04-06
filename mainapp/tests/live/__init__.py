import os

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("SKIP_SLOW_TESTS"),
    reason="Live test are slow as they need to run chrome",
)
