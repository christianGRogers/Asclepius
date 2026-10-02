#!/usr/bin/env python3
"""List what Girder is holding, over the API, when the web UI will not load.

    python scripts/girder-files.py --url https://janus.bradensbay.com --login admin

Girder 5 serves its browser UI from ``girder/web/dist`` at ``/``. When that mount
is missing the API is unaffected -- it is a separate tree -- so every question
the UI would have answered is still answerable, which is what this does: walk
collections, folders, items and files and print the tree with sizes.

Standard library only, so it runs on the server itself with nothing installed,
inside the girder container, or on a laptop.

The password is never taken as an argument. It comes from ``GIRDER_PASSWORD`` or
an interactive prompt, because an argument is visible in ``ps`` to every other
account on the machine and lands in shell history besides.
"""

import argparse
import base64
import getpass
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


def human(size):
    size = float(size or 0)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:,.0f} {unit}" if unit == "B" else f"{size:,.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


class Girder:
    def __init__(self, url, timeout=30):
        self.base = url.rstrip("/") + "/api/v1"
        self.token = None
        self.timeout = timeout

    def _call(self, path, params=None, headers=None):
        query = ("?" + urllib.parse.urlencode(params)) if params else ""
        request = urllib.request.Request(self.base + path + query)
        for key, value in (headers or {}).items():
            request.add_header(key, value)
        if self.token:
            request.add_header("Girder-Token", self.token)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8") or "null")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", "replace")[:300]
            raise SystemExit(f"{path} -> HTTP {exc.code}: {body}") from None
        except urllib.error.URLError as exc:
            raise SystemExit(f"Could not reach {self.base}: {exc.reason}") from None

    def login(self, user, password):
        raw = base64.b64encode(f"{user}:{password}".encode()).decode()
        data = self._call("/user/authentication",
                          headers={"Authorization": "Basic " + raw})
        self.token = data["authToken"]["token"]
        return data["user"]

    def paged(self, path, params=None):
        """Every page of a Girder list endpoint.

        Girder caps `limit`, and a project with five thousand cases is well past
        any single page, so a one-shot request would quietly show a prefix of the
        data and look complete.
        """
        params = dict(params or {})
        offset, out = 0, []
        while True:
            params.update({"limit": 100, "offset": offset})
            page = self._call(path, params) or []
            out.extend(page)
            if len(page) < 100:
                return out
            offset += len(page)


def walk(api, parent_type, parent_id, depth, max_depth, show_files, totals, prefix=""):
    folders = api.paged("/folder", {"parentType": parent_type, "parentId": parent_id})
    for folder in folders:
        items = api.paged("/item", {"folderId": folder["_id"]})
        size = folder.get("size", 0)
        totals["folders"] += 1
        totals["items"] += len(items)
        print(f"{prefix}  {folder['name']}/  ({len(items)} item(s), {human(size)})")
        if show_files:
            # One request per item, so this is off by default: a case pool of a
            # few thousand would otherwise make several thousand round trips to
            # answer a question the folder sizes above already answer.
            for item in items:
                for file in api.paged(f"/item/{item['_id']}/files"):
                    totals["files"] += 1
                    totals["bytes"] += file.get("size", 0)
                    print(f"{prefix}      {file['name']}  {human(file.get('size'))}")
        if depth < max_depth:
            walk(api, "folder", folder["_id"], depth + 1, max_depth, show_files,
                 totals, prefix + "  ")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", default="https://janus.bradensbay.com")
    parser.add_argument("--login", required=True)
    parser.add_argument("--depth", type=int, default=2,
                        help="How far to recurse into folders (default 2).")
    parser.add_argument("--files", action="store_true",
                        help="List individual files, not just folder totals.")
    args = parser.parse_args(argv)

    password = os.environ.get("GIRDER_PASSWORD") or getpass.getpass(
        f"Girder password for {args.login}: ")

    api = Girder(args.url)
    user = api.login(args.login, password)
    print(f"Signed in as {user.get('login')} "
          f"({'admin' if user.get('admin') else 'not an admin'})\n")

    try:
        stores = api._call("/assetstore")
    except SystemExit:
        stores = []
    if stores:
        print("Assetstores")
        for store in stores:
            used = store.get("capacity", {}).get("used")
            free = store.get("capacity", {}).get("free")
            print(f"  {store.get('name')}  root={store.get('root')}  "
                  f"used={human(used)} free={human(free)}")
        print()

    totals = {"folders": 0, "items": 0, "files": 0, "bytes": 0}

    collections = api.paged("/collection")
    print(f"Collections ({len(collections)})")
    for collection in collections:
        print(f"  {collection['name']}  ({human(collection.get('size'))})")
        walk(api, "collection", collection["_id"], 1, args.depth, args.files,
             totals, prefix="  ")

    # Optional, like the assetstore block: listing users is admin-only, and a
    # reviewer running this to see the case pool should get the pool rather than
    # a permissions error where the collections would have been.
    try:
        users = api.paged("/user")
    except SystemExit as exc:
        print(f"\nUser home folders: skipped ({exc})")
        users = []
    print(f"\nUser home folders ({len(users)})")
    for person in users:
        folders = api.paged("/folder", {"parentType": "user",
                                        "parentId": person["_id"]})
        if folders:
            print(f"  {person.get('login')}")
            walk(api, "user", person["_id"], 1, args.depth, args.files,
                 totals, prefix="  ")

    print(f"\n{totals['folders']} folder(s), {totals['items']} item(s)"
          + (f", {totals['files']} file(s), {human(totals['bytes'])}"
             if args.files else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
