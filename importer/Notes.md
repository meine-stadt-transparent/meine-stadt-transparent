# Importer implementation notes

The import downloads all objects using the lists and stores the json as `CachedObject`. The embedded objects are spliced out before storing and replaced by their id, so one object from the api yield multiple flat `CachedObject`s. Since embedded object don't know which object they were contained and the backreferences are elided for embedded objects, we add them as `mst:backref` and the position (for agenda items) as `mst:backrefPosition`.

Once everything is in the database, we import the objects in an order so that if A links to B, then B is imported first.

Import order and dependencies:

* LegislativeTerm: /
* Location: /
* Body: LegislativeTerm, Location
* File: Location
* Person: Location
* Organization: Body, LegislativeTerm, Location
* Membership: Person, Organization
* Meeting: Location, Organization, Person
* Paper: Organization, Person, File
* Consultation: Meeting, Organization
* AgendaItem: Meeting, Consultation, File

The current assumption is you have one body that you want to import, but it isn't hard to change that.

The cli imports up to Body, then imports the outline and the streets and then does the rest. This is done so that errors with the more fallible ags, outline and street import happen early and so that we can show the edit-your-dotenv message before the bulk of log messages.

## Json Importer - Meetings

Some meetings have a visible id, while others don't, meaning the they can't be identified by id alone. In addition, the meeting name is often only the organization without a number, the start time is sometimes changed to reflect the actual start of a meeting after it took place and there are cases where two meetings are entered in the same day. This means that there is no reliable way to find the correct meeting to update and we can only use heuristics that don't violate the unique constraint on `oparl_id`.

If an object has an id but a changed name/start, name and start ar updated before the incremental import. The incremental import can than use id/name/start as unique key.

If a meeting gained an id, this will make the old meeting by deleted while the new meeting will be created. Duplicate meetings with same start/name can be differentiated by their id as the scraper ensures that there are never two meetings with the same name/start, both without ids.
