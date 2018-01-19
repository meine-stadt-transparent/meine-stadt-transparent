import environ

env = environ.Env()
env.read_env(env.str('ENV_PATH', '.env'))
