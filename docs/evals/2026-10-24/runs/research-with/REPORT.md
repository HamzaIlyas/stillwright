# stillwright: latest version on PyPI vs GitHub

**Answer: they match. Both are 0.1.1. The GitHub release v0.1.1 was published 2026-10-24 at 10:49:05 UTC.**

All values were fetched on 2026-10-24 with curl from the URLs below.

## Evidence

| Fact | Value | Source URL |
|---|---|---|
| Latest PyPI version | `0.1.1` (`info.version`) | https://pypi.org/pypi/stillwright/json |
| PyPI release list | `0.1.1` is the only version (6 files, wheels for macOS x86_64/arm64, Linux x86_64/aarch64, Windows, plus the sdist) | https://pypi.org/pypi/stillwright/json and https://pypi.org/simple/stillwright/ (JSON form with `Accept: application/vnd.pypi.simple.v1+json`) |
| PyPI upload time of 0.1.1 | 2026-10-24, 10:48:25Z to 10:48:32Z (files uploaded in sequence) | https://pypi.org/pypi/stillwright/json |
| Latest GitHub release | tag `v0.1.1`, name "0.1.1 - 2026-10-24", `draft: false`, `prerelease: false` | https://api.github.com/repos/HamzaIlyas/stillwright/releases/latest |
| GitHub release date | **2026-10-24**, `published_at` = `2026-10-24T10:49:05Z` | https://api.github.com/repos/HamzaIlyas/stillwright/releases/latest |
| Same date on the release page | `<relative-time datetime="2026-10-24T10:49:05Z">` | https://github.com/HamzaIlyas/stillwright/releases/tag/v0.1.1 |
| All GitHub releases | `v0.1.1` (published 2026-10-24T10:49:05Z) and `v0.1.0` (published 2026-10-24T03:41:39Z) | https://api.github.com/repos/HamzaIlyas/stillwright/releases |
| GitHub tags | `v0.1.1` (commit 7e8f542f369762af0c5d933a6da38ce42e0bcaff) and `v0.1.0` | https://api.github.com/repos/HamzaIlyas/stillwright/tags |
| PyPI metadata points at this repo | Homepage and Changelog link to github.com/HamzaIlyas/stillwright | https://pypi.org/pypi/stillwright/json |

## Notes

- PyPI's 0.1.1 files were uploaded about 40 seconds before the GitHub release was published, so the two releases look like one release run. The release author is `github-actions[bot]`, per the releases/latest API response above.
- The v0.1.0 release is named "0.1.0 - 2026-10-23" but its `published_at` is 2026-10-24T03:41:39Z. Only the name carries the 23rd. This does not affect the latest release.
- "Latest" means GitHub's releases/latest, which excludes drafts and prereleases. The releases list has none of either.

## Unverified

- The human-facing PyPI page https://pypi.org/project/stillwright/ returned HTTP 200 but only a bot "Client Challenge" page, so I could not read it. The PyPI version rests on the JSON API and the simple index, which agree with each other. Both are PyPI's own endpoints.
- I did not check whether the 0.1.1 PyPI files were built from the GitHub v0.1.1 tag. I only compared the version numbers.
