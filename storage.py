import datetime
import glob
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

        filename = os.path.join(self._root, f"{_id}.json")
        with open(filename, 'w') as f:
            json.dump(obj, f)

    def get(self, _id) -> Union[dict, None]:
        if not tokens.is_valid_token(_id):
            raise ValueError(f"Invalid _id: {_id}")

        filename = os.path.join(self._root, f"{_id}.json")
        if not os.path.isfile(filename):
            return None

        with open(filename, 'r') as f:
            return json.load(f)

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
        deleted = []
        now = datetime.datetime.now()
        remaining_count = retention_count or 1
        for token, obj in sorted(self.list(obj_type)):
            if retention_count:
                remaining_count -= 1
            if remaining_count < 0:
                # TODO: delete
                deleted.append((token, obj))
                continue
            parsed = tokens.parse(token)
            delta = now - datetime.datetime.fromtimestamp(parsed['timestamp'])
            if retention_window and delta > retention_window:
                # TODO: delete
                deleted.append((token, obj))
                continue

        return deleted


