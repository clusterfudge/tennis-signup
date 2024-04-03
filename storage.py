import datetime
import glob
import logging
from datetime import timedelta
from typing import List, Generator, Union, Tuple
import os.path
import json

import tokens


def matches_query(obj: dict, query: dict) -> bool:
    result = True

    for k, v in query.items():
        cur = obj.get(k)
        if isinstance(cur, dict):
            result = result and matches_query(cur, v)
        else:
            result = result and cur == v
        if not result:
            break

    return result


class Storage(object):
    def __init__(self, root_directory: str):
        self._root = root_directory
        os.makedirs(self._root, exist_ok=True)

    def put(self, _id: str, obj: dict) -> None:
        if not tokens.is_valid_token(_id):
            raise ValueError(f"Invalid _id: {_id}")

        filename = self._filename_for_id(_id)
        with open(filename, 'w') as f:
            json.dump(obj, f)

    def get(self, _id) -> Union[dict, None]:
        if not tokens.is_valid_token(_id):
            raise ValueError(f"Invalid _id: {_id}")

        filename = self._filename_for_id(_id)
        if not os.path.isfile(filename):
            return None

        with open(filename, 'r') as f:
            return json.load(f)

    def _filename_for_id(self, _id):
        filename = os.path.join(self._root, f"{_id}.json")
        return filename

    def list(self, obj_type: str, query: dict = None) -> Generator[Tuple[str, dict], None, None]:
        for filename in glob.glob(f"{self._root}/{obj_type}_*.json"):
            _id = os.path.basename(filename)[:-5]
            value = self.get(_id)
            if query is None or matches_query(value, query):
                yield _id, value

    def latest(self, obj_type: str, query: dict = None) -> Union[tuple[str, dict], tuple[None, None]]:
        # objects are assumed to use token from tokens lib,
        # be ordinal by timestamp.

        objs = sorted([(tokens.parse(t)['timestamp'], t, o) for t, o in list(self.list(obj_type, query=query))])
        if objs:
            return objs[-1][1:]
        return None, None

    def cleanup(self, obj_type: str, retention_count: int = None, retention_window: timedelta = None, dry_run=True) -> List[Tuple[str, dict]]:
        to_delete = []
        now = datetime.datetime.now()
        remaining_count = retention_count or 1
        for token, obj in sorted(self.list(obj_type)):
            if retention_count:
                remaining_count -= 1
            if remaining_count < 0:
                to_delete.append((token, obj))
                continue
            parsed = tokens.parse(token)
            delta = now - datetime.datetime.fromtimestamp(parsed['timestamp'])
            if retention_window and delta > retention_window:
                to_delete.append((token, obj))
                continue

        if not dry_run:
            for _id, _ in to_delete:
                filename = self._filename_for_id(_id)
                try:
                    os.unlink(filename)
                except Exception:
                    logging.exception(f"Failed to delete {_id}")

        return to_delete


