import hashlib
import re
import pytest


class WordTokenizer:
    pad_token_id = 0

    def __call__(self, text, add_special_tokens=False):
        assert add_special_tokens is False
        pieces = re.findall(r"\w+|[^\w\s]", text)
        return {"input_ids": [1+int(hashlib.sha256(p.encode()).hexdigest()[:6],16)%1024 for p in pieces]}


@pytest.fixture
def tok():
    return WordTokenizer()
