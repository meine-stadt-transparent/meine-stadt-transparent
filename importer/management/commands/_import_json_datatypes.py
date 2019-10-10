from datetime import date, datetime
from typing import List
from typing import Optional, Union

from dataclasses import dataclass, field
from dataclasses_json import dataclass_json, config
from marshmallow import fields
from marshmallow.utils import from_iso_date, from_iso_datetime

date_metadata = config(
    encoder=lambda x: x.isoformat() if x else None,
    decoder=lambda x: from_iso_date(x) if x else None,
    mm_field=fields.Date(format="iso"),
)

datetime_metadata = config(
    encoder=lambda x: x.isoformat() if x else None,
    decoder=lambda x: from_iso_datetime(x) if x else None,
    mm_field=fields.DateTime(format="iso"),
)

# Hack for the meeting start which can be both a date and a datetime
date_or_datetime_metadata = config(
    encoder=lambda x: x.isoformat(),
    decoder=lambda x: from_iso_date(x) if len(x) == 10 else from_iso_datetime(x),
    mm_field=fields.DateTime(format="iso"),
)


@dataclass_json
@dataclass(frozen=True)
class Person:
    name: str
    party: Optional[str]
    begin: Optional[date] = field(metadata=date_metadata, default=None)
    end: Optional[date] = field(metadata=date_metadata, default=None)


@dataclass_json
@dataclass(frozen=True)
class Paper:
    short_title: str
    title: str
    reference_number: str
    paper_type: Optional[str]
    original_id: Optional[int] = None


@dataclass_json
@dataclass(frozen=True)
class File:
    title: str
    original_id: int
    url: str
    claimed_size: Optional[int]
    paper_original_id: Optional[int]


@dataclass_json
@dataclass(frozen=True)
class Meeting:
    organization_name: str
    title: str
    location: Optional[str]
    note: Optional[str]
    original_id: Optional[int]
    start: Union[date, datetime] = field(metadata=date_or_datetime_metadata)
    end: Optional[datetime] = field(metadata=datetime_metadata, default=None)
    cancelled: bool = False


@dataclass(frozen=True)
class Organization:
    name: str
    original_id: Optional[int]


@dataclass_json
@dataclass(frozen=True)
class Membership:
    organization_original_id: int
    person_original_id: Optional[int]
    person_name: str
    role: str
    on_behalf_of: Optional[str]
    start_date: Optional[date] = field(metadata=date_metadata, default=None)
    end_date: Optional[date] = field(metadata=date_metadata, default=None)


@dataclass_json
@dataclass(frozen=True)
class AgendaItem:
    key: str
    position: int
    title: str
    meeting_id: int
    paper_reference_number: Optional[str]
    paper_original_id: Optional[int]
    original_id: Optional[int]
    result: Optional[str]
    voting: Optional[str]
    note: Optional[str]


@dataclass_json
@dataclass(frozen=True)
class RisData:
    name: str
    main_organization: Optional[Organization]
    persons: List[Person]
    organizations: List[Organization]
    papers: List[Paper]
    files: List[File]
    meetings: List[Meeting]
    memberships: List[Membership]
    agenda_items: List[AgendaItem]
