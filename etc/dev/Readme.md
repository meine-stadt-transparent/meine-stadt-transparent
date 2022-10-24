# Dev setup

This folder contains an easy to use dev setup where everything but the application itself runs in docker. To use it, you need to add the following to your `/etc/hosts`:

```
127.0.0.1 opensourceris.local
127.0.0.1 meine-stadt-transparent.local
```

Then run `docker compose up nginx-dev mariadb-dev elasticsearch-dev` (or whatever services you need), configure `opensourceris.local` or `meine-stadt-transparent.local` as real host and open https://opensourceris.local or https://meine-stadt-transparent.local.
