# Goal: Report latest stillwright version on PyPI and GitHub, whether they match, and GitHub release date, with source URLs.
1. Query PyPI JSON API | who: bash curl | check: HTTP 200 and version printed | after: -
2. Query GitHub releases/latest API | who: bash curl | check: HTTP 200 and tag/published_at printed | after: -
3. Compare and write report | who: self | check: report file lists URLs from steps 1-2 | after: 1,2
Outward: none
