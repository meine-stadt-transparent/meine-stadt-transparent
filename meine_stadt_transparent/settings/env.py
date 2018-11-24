import sys

import environ

env = environ.Env()
env_file = ".env"

# This works good enough for the console, pycharm and travis ci
TESTING = sys.argv[1:2] == ["test"]

if env.str("ENV_PATH", None):
    env_file = env.str("ENV_PATH")
elif TESTING:
    env_file = "etc/env-test"

env.read_env(env_file)

TESTING_TRAVIS = env.bool("TRAVIS", False)
