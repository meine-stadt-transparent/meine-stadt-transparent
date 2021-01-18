import sys
from pathlib import Path

import environ

env = environ.Env()
env_file = ".env"

# This works good enough for the console, pycharm and travis ci
TESTING = sys.argv[1:2] == ["test"] or "pytest" in sys.modules
if env.str("ENV_PATH", None):
    env_file = env.str("ENV_PATH")
    assert Path(env_file).is_file()
elif TESTING:
    env_file = "etc/test.env"
    assert Path(env_file).is_file()

env.read_env(env_file)
