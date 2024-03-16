import glob
from typing import List, Generator, Union, Tuple
import os.path
import json

import tokens


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

    def list(self, obj_type) -> Generator[Tuple[str, dict], None, None]:
        for filename in glob.glob(f"{self._root}/{obj_type}_*.json"):
            _id = os.path.basename(filename)[:-5]
            yield _id, self.get(_id)

    def latest(self, obj_type) -> Tuple[str, dict]:
        # objects are assumed to use token from tokens lib,
        # be ordinal by timestamp.
        objs = sorted(list(self.list(obj_type)))
        if objs:
            return objs[-1]
        return None, None

