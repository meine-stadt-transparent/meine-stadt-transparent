# Importer implementation notes

The import donwloads all objects using the lists and stores the json as `CachedObject`. The embedded objects are spliced out before storing and replaced by their id, so one object from the api yield multiple flat `CachedObject`s. Since embedded object don't know which object they were contained and the backreferences are elided for embedded objects, we add them as `mst:backref` and the position (for agenda items) as `mst:backrefPosition`.

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

The cli imports up to Body, then imports the outline and the streets and then does the rest. This is done so that errors with the more falllible ags, outline and street import happen early and so that we can show the edit-your-dotenv message before the bulk of log messages.
