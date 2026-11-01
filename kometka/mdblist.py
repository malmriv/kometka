"""Ratings from MDBList (https://mdblist.com)."""
import json
import urllib.error
import urllib.parse

from .net import request

API = "https://api.mdblist.com"
# The same list Kometa uses for its Certified Fresh badge.
CERTIFIED_FRESH_LIST = "/lists/k0meta/certifiedfreshmovies/items"


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

    def movie(self, tmdb_id):
        """Movie details including "ratings", or None if MDBList doesn't know it."""
        try:
            return self._get("/tmdb/movie/%s" % tmdb_id)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            raise

    def certified_fresh(self):
        """TMDb ids of all Certified Fresh movies."""
        ids, offset, page = set(), 0, 1000
        while True:
            movies = self._get(CERTIFIED_FRESH_LIST, limit=page, offset=offset).get("movies") or []
            ids.update(m["ids"]["tmdb"] for m in movies if (m.get("ids") or {}).get("tmdb"))
            if len(movies) < page:
                return ids
            offset += page
