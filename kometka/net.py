"""Small HTTP helper on top of urllib, with retries for transient errors."""
import time
import urllib.error
import urllib.request

from . import __version__

USER_AGENT = "kometka/" + __version__
NO_RETRY = (400, 401, 403, 404, 429)


def request(url, method="GET", body=None, headers=None, attempts=3, timeout=60):
    headers = {"User-Agent": USER_AGENT, **(headers or {})}
    for attempt in range(1, attempts + 1):
        try:
            req = urllib.request.Request(url, data=body, headers=headers, method=method)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            if e.code in NO_RETRY or attempt == attempts:
                raise
        except (urllib.error.URLError, TimeoutError):
            if attempt == attempts:
                raise
        time.sleep(5 * attempt)
