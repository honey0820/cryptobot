import sys

import pytest

sys.path.append('.')
# pylint: disable=import-error
from controllers.PyCryptoBot import PyCryptoBot

app = PyCryptoBot()

def test_get_version_from_readme():
    global app
    version = app.get_version_from_readme(app)
    assert version != 'v0.0.0'
