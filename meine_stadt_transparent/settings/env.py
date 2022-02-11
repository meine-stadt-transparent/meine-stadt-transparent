import os
import sys
from pathlib import Path

import environ
from django.core.exceptions import ImproperlyConfigured

env = environ.Env()
env_file = Path(".env")

# This works good enough for the console, pycharm and travis ci
TESTING = sys.argv[1:2] == ["test"] or "pytest" in sys.modules
if env.str("ENV_PATH", None):
    env_file = Path(env.str("ENV_PATH"))
elif TESTING:
    # This anchoring allows to run tests below the project root
    env_file = Path(__file__).parent.parent.parent.joinpath("etc/test.env")
    assert env_file.is_file(), "The test env is missing"

if not env_file.is_file() and not os.environ.get("REAL_HOST"):
    raise ImproperlyConfigured(
        f"There is no configuration file at {env_file} "
        f"but also no configuration through environment variables (REAL_HOST is missing)"
    )

env.read_env(env_file)
