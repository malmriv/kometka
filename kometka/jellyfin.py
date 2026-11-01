"""The few Jellyfin API calls Kometka needs."""
import base64
import json
import urllib.parse

from .net import request


class Jellyfin:
    def __init__(self, url, api_key):
        self.url = url.rstrip("/")
        self.headers = {"Authorization": 'MediaBrowser Token="%s"' % api_key}

    def _get(self, path, **params):
        query = ("?" + urllib.parse.urlencode(params)) if params else ""
        return request(self.url + path + query, headers=self.headers)

    def _items(self, **params):
        params.update(EnableImageTypes="Primary", ImageTypeLimit=1)
        return json.loads(self._get("/Items", **params)).get("Items", [])

    def library_ids(self, names):
        folders = json.loads(self._get("/Library/VirtualFolders"))
        found = {f["Name"]: f["ItemId"] for f in folders}
        missing = [n for n in names if n not in found]
        if missing:
            raise ValueError("Unknown Jellyfin libraries: %s (available: %s)"
                             % (", ".join(missing), ", ".join(found)))
        return [found[n] for n in names]

    def movies(self, libraries=()):
        """Movies with their TMDb id (ProviderIds) and poster tag (ImageTags)."""
        params = dict(IncludeItemTypes="Movie", Recursive="true", Fields="ProviderIds")
        if not libraries:
            return self._items(**params)
        movies = []
        for parent in self.library_ids(libraries):
            movies += self._items(ParentId=parent, **params)
        return movies

    def poster_tag(self, item_id):
        items = self._items(Ids=item_id)
        return (items[0].get("ImageTags") or {}).get("Primary") if items else None

    def get_poster(self, item_id):
        return self._get("/Items/%s/Images/Primary" % item_id)

    def set_poster(self, item_id, jpeg):
        # Jellyfin expects the image body base64-encoded.
        request(self.url + "/Items/%s/Images/Primary" % item_id, method="POST",
                body=base64.b64encode(jpeg),
                headers={**self.headers, "Content-Type": "image/jpeg"})
