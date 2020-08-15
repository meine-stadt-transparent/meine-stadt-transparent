#!/usr/bin/env python3

import json
import os
import subprocess
import sys
from concurrent.futures import as_completed
from concurrent.futures.thread import ThreadPoolExecutor
from select import select
from subprocess import PIPE
from typing import Tuple
from urllib.request import urlopen

# noinspection PyUnresolvedReferences
import yaml
from slugify import slugify


def runner(title: str, system_url) -> Tuple[str, int]:
    bodies_url = json.load(urlopen(system_url))["body"]
    body_url = json.load(urlopen(bodies_url))["data"][0]["id"]

    slug = slugify(title, separator="_")
    db_env = {
        **os.environ,
        **{"DATABASE_URL": f"mysql://root:dummy@127.0.0.1/{slug}?charset=utf8mb4"},
    }

    subprocess.check_call(
        ["mysql", "-uroot", "-pdummy", "-e", f"CREATE DATABASE {slug};"]
    )
    subprocess.check_call(
        ["/app/.venv/bin/python", "/app/manage.py", "migrate"], env=db_env
    )

    command = [
        "/app/.venv/bin/python",
        "/app/manage.py",
        "import",
        "--skip-body-extra",
        "--skip-files",
        body_url,
    ]
    with subprocess.Popen(command, env=db_env, stdout=PIPE, stderr=PIPE) as p:
        readable = {
            p.stdout: "OUT",
            p.stderr: "ERR",
        }
        while readable:
            for fd in select(readable, [], [])[0]:
                data = fd.readline()
                if not data:  # EOF
                    del readable[fd]
                else:
                    msg = f"{title:>20} {readable[fd]} " + data.decode(
                        "utf-8", "replace"
                    )
                    if readable[fd] == "OUT":
                        sys.stdout.write(msg)
                    else:
                        sys.stderr.write(msg)
        status_code = p.wait()
        print(f"{title:>20} DONE", status_code)
        return title, status_code


def main():
    index = "https://oparl.github.io/resources/endpoints.yml"

    skip_list = [
        "OParl Mirror",
        "Politik bei Uns - Aufbereitete Daten",
        "kleineAnfragen",
    ]

    endpoints = yaml.safe_load(urlopen(index))

    results = dict()
    with ThreadPoolExecutor() as executor:
        tasks = []
        for endpoint in endpoints:
            if endpoint["title"] not in skip_list:
                tasks.append(
                    executor.submit(runner, endpoint["title"], endpoint["url"])
                )
        for done in as_completed(tasks):
            title, status_code = done.result()
            print(f"{title:>2}", "FINISHED", status_code)
            results[title] = status_code

    print(results)


if __name__ == "__main__":
    main()
