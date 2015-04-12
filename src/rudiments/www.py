# -*- coding: utf-8 -*-
# pylint: disable=bad-continuation
""" WWW access helpers.
"""
# Copyright ©  2015 Jürgen Hermann <jh@web.de>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from __future__ import absolute_import, unicode_literals, print_function

import os
import re
import tempfile
from contextlib import contextmanager

import requests

from ._compat import urlparse


__all__ = ['url_as_file']


@contextmanager
def url_as_file(url, ext=None):
    """
        Context manager that GETs a given ``url`` and provides it as a local file.

        The file is in a closed state upon entering the context,
        and removed when leaving it, if still there.

        To give the file name a specific extension, use ``ext``;
        the extension can optionally include a separating dot,
        otherwise it will be added.

        >>> with url_as_file('https://api.github.com/meta', ext='json') as meta:
        ...     print(re.match(r'.+/(.+)-[^.]+?(\.[^.]+?)$', meta).groups())
        ...     print(json.load(open(meta))['hooks'])
        (u'www-api.github.com', u'.json')
        [u'192.30.252.0/22']
    """
    if ext:
        ext = '.' + ext.strip('.')  # normalize extension
    url_hint = 'www-{}-'.format(urlparse(url).hostname or 'any')

    content = requests.get(url).text
    with tempfile.NamedTemporaryFile(suffix=ext, prefix=url_hint, delete=False) as handle:
        handle.write(content)

    try:
        yield handle.name
    finally:
        if os.path.exists(handle.name):
            os.remove(handle.name)