"""Ratings from MDBList (https://mdblist.com)."""
import json
import urllib.error
import urllib.parse

from .net import request

API = "https://api.mdblist.com"
# The same lists Kometa uses for its Certified Fresh badge, by MDBList media type.
CERTIFIED_FRESH_LISTS = {"movie": "/lists/k0meta/certifiedfreshmovies/items",
                         "show": "/lists/k0meta/certifiedfreshshows/items"}


class RateLimited(Exception):
    pass


class MDBList:
    def __init__(self, api_key):
        self.api_key = api_key

    def _get(self, path, **params):
        params["apikey"] = self.api_key
        try:
            return json.loads(request(API + path + "?" + urllib.parse.urlencode(params)))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                raise RateLimited("MDBList daily request limit reached") from e
            raise

    def item(self, media_type, tmdb_id):
        """Movie or show ("movie" / "show") details including "ratings", or None if MDBList doesn't know it."""
        try:
            return self._get("/tmdb/%s/%s" % (media_type, tmdb_id))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            raise

    def certified_fresh(self, media_type):
        """TMDb ids of all Certified Fresh movies or shows ("movie" / "show")."""
        ids, offset, page = set(), 0, 1000
        while True:
            # The list's items come under "movies" or "shows".
            items = self._get(CERTIFIED_FRESH_LISTS[media_type], limit=page, offset=offset).get(media_type + "s") or []
            ids.update(i["ids"]["tmdb"] for i in items if (i.get("ids") or {}).get("tmdb"))
            if len(items) < page:
                return ids
            offset += page
