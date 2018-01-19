import sys

import environ

env = environ.Env()
env.read_env(env.str('ENV_PATH', '.env'))

TESTING = sys.argv[1:2] == ['test']
