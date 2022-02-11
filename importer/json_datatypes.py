from datetime import date, datetime
from typing import List, Dict
from typing import Optional, Union

import attr
from cattr.converters import Converter
from dateutil import tz

converter = Converter()
converter.register_unstructure_hook(datetime, lambda dt: dt.isoformat())
converter.register_structure_hook(datetime, lambda ts, _: datetime.fromisoformat(ts))
converter.register_unstructure_hook(date, lambda dt: dt.isoformat())
converter.register_structure_hook(date, lambda ts, _: date.fromisoformat(ts))
converter.register_structure_hook(
    Optional[Union[date, datetime]],
    lambda ts, _: date.fromisoformat(ts)
    if len(ts) == 10
    else datetime.fromisoformat(ts),
)

format_version = 4


@attr.frozen()
class Person:
    # Overview page
    name: str
    party: Optional[str]
    # Possible are "kp0051" and "pe0051"
    view_type: Optional[str] = None
    begin: Optional[date] = None
    end: Optional[date] = None
    original_id: Optional[int] = None
    # Detail page
    location: Optional[str] = None
    street_address: Optional[str] = None
    phone_private: Optional[str] = None
    phone_office: Optional[str] = None
    fax_private: Optional[str] = None
    fax_office: Optional[str] = None
    mobile_office: Optional[str] = None
    mobile_private: Optional[str] = None
    email: Optional[str] = None
    occupation: Optional[str] = None
    web: Optional[str] = None
    birthday: Optional[str] = None
    image: Optional[str] = None

    def get_unique(self):
        return self.name


@attr.frozen()
class Paper:
    short_name: str
    name: str
    reference: str
    paper_type: Optional[str]
    sort_date: datetime
    original_id: Optional[int] = None

    def get_unique(self):
        return self.reference


@attr.frozen()
class File:
    name: str
    original_id: int
    url: str
    claimed_size: Optional[int]
    paper_original_id: Optional[int]

    def get_unique(self):
        return self.original_id


@attr.frozen()
class Meeting:
    organization_name: str
    name: str
    location: Optional[str]
    note: Optional[str]
    original_id: Optional[int]
    start: Optional[Union[date, datetime]] = None
    end: Optional[datetime] = None
    cancelled: bool = False

    def get_unique(self):
        return self.name, self.start.astimezone(tz.tzutc())


@attr.frozen()
class Organization:
    name: str
    original_id: Optional[int]
    # Whether there is a page with memberships (which may be empty)
    has_memberships: bool

    def get_unique(self):
        return self.name


@attr.frozen()
class Membership:
    organization_original_id: int
    person_original_id: Optional[int]
    person_name: str
    role: str
    on_behalf_of: Optional[str]
    start_date: Optional[date]
    end_date: Optional[date]

    def get_unique(self):
        return self.organization_original_id, self.person_name


@attr.frozen()
class AgendaItem:
    key: str
    position: int
    name: str
    meeting_id: int
    paper_reference: Optional[str]
    paper_original_id: Optional[int]
    original_id: Optional[int]
    result: Optional[str]
    voting: Optional[str]
    note: Optional[str]

    def get_unique(self):
        return self.meeting_id, self.name


@attr.frozen()
class RisMeta:
    name: str
    vendor: str
    url: str
    population: int
    wikidata_item: str
    website: str
    ags: str
    version: Optional[str]

    @property
    def wikidata_id(self) -> str:
        return self.wikidata_item.split("/")[-1]

    @property
    def escaped_name(self) -> str:
        return self.name.replace("/", "-")


@attr.frozen()
class RisData:
    meta: RisMeta
    main_organization: Optional[Organization]
    persons: List[Person]
    organizations: List[Organization]
    papers: List[Paper]
    files: List[File]
    meetings: List[Meeting]
    memberships: List[Membership]
    agenda_items: List[AgendaItem]
    format_version: int = format_version

    def get_counts(self) -> Dict[str, int]:
        files_size_mb = sum((i.claimed_size or 0) for i in self.files) // 10**6
        return {
            "Population": self.meta.population,
            "Paper": len(self.papers),
            "File": len(self.files),
            "Size (MB)": files_size_mb,
            "Person": len(self.persons),
            "Meeting": len(self.meetings),
            "Organization": len(self.organizations),
            "Membership": len(self.memberships),
            "Agenda Item": len(self.agenda_items),
        }
