# Goal: Report latest stillwright version on PyPI and GitHub, whether they match, and the GitHub release date, each fact with its exact source URL.
1. PyPI latest version | who: self (curl PyPI JSON API) | check: fetched JSON from https://pypi.org/json shows info.version; quote output | after: -
2. GitHub latest release tag and date | who: self (curl GitHub API, releases/latest + releases list + tags) | check: API JSON shows tag_name and published_at; quote output | after: -
3. Cross-check on human pages and compare | who: self (WebFetch of pypi.org/project/stillwright and github releases page) | check: pages' content agrees with API values or conflict is reported | after: 1,2
Outward: none
