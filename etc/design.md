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
 * We felt the headers were always one level to big, so we made each one level lower (i.e. h1 now has `$h2-font-size`) 

## Trade-Offs 
 * It is expected that the site is deployed for users of only one language, e.g. there is no dynamically imported data that has to be translated. This is propably safe to assume for quite some time in the future as currently the comercial vendors afaik can't do localization at all.
 * You don't want to apply your cities (most likely crappy) corporate design. It will be possible to replace header and footer and it's easy to do some bootstrap theming, but we won't do that tight-yet-ugly integration into cities' websites.
 * No support for ancient servers. I'd even call that a feature and not a trade-off
 
## Keyboard Shortcuts
 * `alt+f` focuses the search 
 
## Pages
 * Persons 
 * Papers
 * Displaying a file, mainly with pdf.js
 * Kalendar
 * Meeting with agenda items and attendees 
 * Organization with persons and papaer
 * Login and profile
 * Search with facets ✓ 
 * One Pager alike landing page ✓ 
 * animal photos ✓

## Links on the landing page
 * Persons 
 * Meetings
 * Login / Notifications
 * Search
 * Map
 * Latest papers
 * Organizations

## Linter 
 * https://www.ssllabs.com/ssltest/analyze.html?d=meine%2dstadt%2dtransparent.de&s=185.183.157.234&hideResults=on (A+)
 * https://observatory.mozilla.org/analyze.html?host=meine-stadt-transparent.de (A+)
 * https://codeclimate.com/github/meine-stadt-transparent/meine-stadt-transparent (A)
 * https://app.fossa.io/projects/git%2Bgithub.com%2Fmeine-stadt-transparent%2Fmeine-stadt-transparent (Passing)
 * ![Docker image size](https://img.shields.io/microbadger/image-size/konstin2/meine-stadt-transparent.svg)

## pdfjs

Since the pdfjs maintainers don't the default viewer in the npm package, but we need that default viewer, we've forked pdfjs ([#9127](https://github.com/mozilla/pdf.js/issues/9127), [#9144](https://github.com/mozilla/pdf.js/pull/9144)). The integration works as follows (and can be updated thereby):

 * pdfjs is forked to https://github.com/meine-stadt-transparent/pdf.js
 * Those sources are then build into the embedable distribution by running `npm install && gulp dist` in the repo root.
 * `cd build/dist/; git push --tags https://github.com/meine-stadt-transparent/pdfjs-dist master; cd ../..` pushes the build to https://github.com/meine-stadt-transparent/pdfjs-dist, which is our version of https://github.com/mozilla/pdfjs-dist
 * This dist repo is than install as npm dependency; `gulp dist` had generated a custom package.json for the repo.
 * STATICFILES_DIRS includes 'node_modules/pdfjs-dist/viewer', so that django copies the contents viewer folder to the static files folder
 * The `file` view loads that with `static('web/viewer.html')`.
 * The viewer loads the (already minified) css and js using relative paths.
 
## PGP

I thought it would be really cool to have an option to send pgp encrypted notifications that would be dead easy to use. The UI i just a dropdown on the profile page where you can select the key for your e-mail address from a keyserver. But it turns out that when sending a multipart email, enigmail, for whatever reason, chooses to display the source of the html part. I also couldn't find any documentation about this. This effectively means we can only send encrypted notifications as plaintext, which defeats the whole point of a modern, user-friendly service. So the feature is written and tested, but disabled by default (it can be enabled with `ENABLE_PGP=True`).
