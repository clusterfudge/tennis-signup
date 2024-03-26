import datetime
import random
import base62


def generate_token(prefix, generation='0', timestamp=None, entropy=10) -> str:
    ts = timestamp or datetime.datetime.now().timestamp()
    ts = int(ts)
    ts_encoded = base62.encode(ts).zfill(8)
    return f"{prefix}_{generation}{ts_encoded}{''.join(random.sample(base62.CHARSET_DEFAULT, entropy))}"


def is_valid_token(token) -> bool:
    """
    is_valid_token
    :param token: a string, potentially a token
    :return: a boolean based on some loose heuristics of whether this is probably a token
    does not attempt to enforce any generation schema or even parse timestamp. Just charset checks.
    """
    last_delimiter = token.rfind('_')
    prefix, suffix = token[:last_delimiter], token[last_delimiter + 1:]
    for char in prefix:
        if char not in base62.CHARSET_DEFAULT:
            return False
    for char in suffix:
        if char not in base62.CHARSET_DEFAULT:
            return False

    return True

def swap_prefix(token: str, new_prefix: str) -> str:
    suffix = token[token.rfind('_') + 1:]
    return new_prefix + '_' + suffix
