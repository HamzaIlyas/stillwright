# stillwright: latest release on PyPI vs GitHub

Checked 2026-10-24, using public web sources only.

## Result

The latest version matches. PyPI and GitHub both show 0.1.1. The GitHub release was published on 2026-10-24 (10:49:05 UTC).

## Facts and sources

1. PyPI latest version is 0.1.1.
   - Source: https://pypi.org/pypi/stillwright/json (`info.version` = 0.1.1).
   - 0.1.1 is the only release listed there.
   - Its files were uploaded 2026-10-24 between 10:48:25 and 10:48:32 UTC. The first file is the macOS x86_64 wheel.
   - The project URLs point to https://github.com/HamzaIlyas/stillwright, so the PyPI package is linked to that repository.

2. GitHub latest release is tag `v0.1.1`.
   - Source: https://api.github.com/repos/HamzaIlyas/stillwright/releases/latest
   - The release is named "0.1.1 - 2026-10-24". It is not a pre-release and not a draft.
   - Release page: https://github.com/HamzaIlyas/stillwright/releases/tag/v0.1.1

3. GitHub release date for v0.1.1 is 2026-10-24.
   - Source: https://api.github.com/repos/HamzaIlyas/stillwright/releases/latest
   - `published_at` is 2026-10-24T10:49:05Z. `created_at` is 2026-10-24T10:46:28Z.
   - The PyPI upload (10:48:25 to 10:48:32 UTC) came about 30 to 40 seconds before the GitHub release was published.

4. GitHub has one earlier release, v0.1.0.
   - Source: https://api.github.com/repos/HamzaIlyas/stillwright/releases
   - It was published 2026-10-24T03:41:39Z. It is not a pre-release and not a draft.
   - That is the full release list: only v0.1.1 and v0.1.0.
   - v0.1.0 does not appear in the PyPI release list (source 1). I did not investigate why. It may never have been uploaded or may have been removed.

## Caveats

- The https://pypi.org/project/stillwright/ web page did not load usable content in my fetch. It showed a "required part of the site couldn't load" message. The PyPI facts therefore come from the PyPI JSON API only.
- The PyPI and GitHub API pages were read through a summarising fetch tool, not as raw JSON. I did not independently re-verify the values against another source.
