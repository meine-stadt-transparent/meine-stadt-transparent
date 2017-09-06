# Open Source Ratsinformationssystem

Open Source RIS für Prototype Fund

## Development

### Installing the project

Create a virtualenv at `venv`. Add a local domain https://opensourceris.local/ with self-signed certificates in your webserver which redirects to localhost:8080

```bash
pip install -r requirements.txt
```

### Starting the development server

```bash
source venv/bin/activate
./manage.py migrate
./manage.py runserver
```

## Design

The names of the models and the fields are highly inspired by the OParl standard. 
