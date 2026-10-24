# Goal: Report latest PyPI and GitHub release versions of stillwright, whether they match, and the GitHub release date, each with exact URL.
1. PyPI latest version via JSON API | who: self (curl) | check: HTTP 200 from https://pypi.org/pypi/stillwright/json and info.version printed | after: -
2. GitHub latest release tag and published date via API | who: self (curl) | check: HTTP 200 from https://api.github.com/repos/HamzaIlyas/stillwright/releases/latest, tag_name and published_at printed | after: -
3. Cross-check with human pages (pypi.org/project page, github releases page) | who: self (curl) | check: page text contains the same version/date | after: 1,2
Outward: none
