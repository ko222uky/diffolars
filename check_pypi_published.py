"""
CLI used by .gitlab-ci.yml to check whether a package version is already
published on PyPI, so the publish job can skip re-publishing unchanged versions.

Usage: uv run check_pypi_published.py <package> <version>
Exit code 0 if <package>==<version> is already on PyPI, 1 if it is not.
"""

import sys
import urllib.error
import urllib.request


def is_published(package: str, version: str) -> bool:
    url = f"https://pypi.org/pypi/{package}/{version}/json"
    try:
        urllib.request.urlopen(url)
        return True
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False
        raise


if __name__ == "__main__":
    package, version = sys.argv[1], sys.argv[2]
    sys.exit(0 if is_published(package, version) else 1)
