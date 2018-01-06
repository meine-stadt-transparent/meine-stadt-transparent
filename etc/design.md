# Design

This document shall explain the important design decision, assumptions and trade-offs.

## Assumptions

 * The data has the structure that is used for the OParl format. This is a well tested assumptions as the big comercial vendors have implemented OParl and approved that structure
 * There is one main body. In Munich e.g. there is the city of Munich in distinction to the 25 city districts.
 * There is one main committee (Mostly the city council)
 * There are mutliple factions / parliamentary groups in the main committee. The filters on the organization page are based on that assumption.
 * There are three main organizatin types: Committee, Department and Parliamentary Group. There are also others, though those three are the most important.
 * One deployment contains data which is in one timezone.
 * No meeting starting before 8:00 or after 21:00 is a good default

## Design Decisions
 * We use docker-composer for quickly getting things up and running. Docker is becoming more and more of an industry standard in the whole server worlds, so this is a safe bet.
 * We support the last few versions of current browsers, but no old internet explorer oder android browser versions. We wont encourage using crappy insecure browsers.

## Trade-Offs 
 * It is expected that the site is deployed for users of only one language, e.g. there is no dynamically imported data that has to be translated. This is propably safe to assume for quite some time in the future as currently the comercial vendors afaik can't do localization at all.
 * You don't want to apply your cities (most likely crappy) corporate design. It will be possible to replace header and footer and it's easy to do some bootstrap theming, but we won't do that tight-yet-ugly integration into cities' websites.
 * No support for ancient servers. I'd even call that a feature and not a trade-off
 
## Keyboard Shortcuts
 * `alt+f` focuses the search 