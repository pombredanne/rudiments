# *- coding: utf-8 -*-
# pylint: disable=wildcard-import, missing-docstring, no-self-use, bad-continuation
# pylint: disable=invalid-name
""" Test ``rudiments.reamed.click``.
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
import unittest
import StringIO
from contextlib import contextmanager

import pytest
import configobj
from bunch import Bunch

from rudiments.reamed import click
from rudiments.reamed.click import *  # pylint: disable=unused-wildcard-import


class PrettyPathTests(unittest.TestCase):

    def test_pretty_path_replaces_home_folder(self):
        path = os.path.expanduser('~/foobar')
        assert os.path.isabs(path[0]), "Test path is absolute"
        path = pretty_path(path)
        assert path[:2] == '~' + os.sep, "Path was changed to short form"
        assert path.split(os.sep) == ['~', 'foobar'], "Path is semantically the same"


class SerrorTests(unittest.TestCase):
    RECORDER = []

    @contextmanager
    def monkey_patched_secho(self):
        self.RECORDER = []
        try:
            click.secho = lambda msg, **_: self.RECORDER.append(msg)
            yield
        finally:
            click.secho = secho

    def test_serror_calls_secho(self):
        with self.monkey_patched_secho():
            click.serror("foobar")
            assert self.RECORDER[-1] == 'foobar'


    def test_serror_formats_its_message(self):
        with self.monkey_patched_secho():
            click.serror("{0} {foo}", 1, foo=2)
            assert self.RECORDER[-1] == '1 2'


class LoggedFailureTests(unittest.TestCase):

    def test_logged_failure_is_usage_error(self):
        exc = LoggedFailure("foo")
        assert isinstance(exc, UsageError), "Exception has UsageError as a base"

    def test_logged_failure_is_styled(self):
        exc = LoggedFailure("foo")
        assert exc.message[0] == '\x1b', "Message starts with ANSI sequence"


class ConfigurationTests(unittest.TestCase):

    def test_configuration_from_context_creation_work(self):
        ctx = Bunch(info_name='foobarbaz', obj=None)
        cfg = Configuration.from_context(ctx)
        assert isinstance(cfg, Configuration), "Configuration has expected type"
        assert ctx.obj.cfg is cfg, "Configuration is added to context"
        assert cfg.name == 'foobarbaz'
        assert len(cfg.config_paths) >= 2, "Default config paths are used"
        assert cfg.config_paths[0] == '/etc/foobarbaz.conf', "Default config paths are used"

    def test_configuration_from_context_with_existing_context_object(self):
        ctx_obj = Bunch()
        ctx = Bunch(info_name='foobarbaz', obj=ctx_obj)
        cfg = Configuration.from_context(ctx)
        assert ctx_obj.cfg is cfg

    def test_configuration_paths_taken_from_environment(self):
        env_paths = ['foo.conf', 'bar.conf']
        os.environ['FOOBARBAZ_CONFIG'] = os.pathsep.join(env_paths)
        cfg = Configuration('foobarbaz')
        del os.environ['FOOBARBAZ_CONFIG']
        assert cfg.config_paths[-2:] == env_paths

    def test_explicit_configuration_paths_override_defaults(self):
        cfg = Configuration('foo', ['foobarbaz.conf'])
        assert cfg.config_paths == ['foobarbaz.conf']

    def test_empty_path_element_inserts_defaults(self):
        cfg = Configuration('foo', ['', 'foobarbaz.conf'])
        assert cfg.config_paths[0] == '/etc/foo.conf', "Default config paths are used"
        assert cfg.config_paths[-1] == 'foobarbaz.conf'

    def test_multiple_empty_path_elements_are_expanded(self):
        cfg = Configuration('foo', ['', 'foobarbaz.conf', ''])
        assert cfg.config_paths[0] == '/etc/foo.conf', "Default config paths are used"
        assert cfg.config_paths[len(cfg.config_paths) // 2] == 'foobarbaz.conf'

    def test_configuration_locations_filters_by_existence(self):
        cfg = Configuration('foobarbaz_wont_exist_ever')
        assert len(cfg.config_paths) > 0
        assert len(cfg.locations()) == 0
        assert len(cfg.locations(exists=False)) == len(cfg.config_paths)

    def test_configuration_default_uses_app_dir(self):
        name = 'foobarbaz_wont_exist_ever'
        cfg = Configuration(name)
        assert cfg.locations(exists=False)[1] == click.get_app_dir(name) + '.conf'

    def test_configuration_locations_eliminates_dupes(self):
        cfg = Configuration('foobarbaz_wont_exist_ever', ['', ''])
        assert len(cfg.locations(exists=False)) == len(cfg.config_paths) // 2

    # TODO: def test_configuration_locations_expands_directories(self):

    def test_configuration_load_with_no_files_works(self):
        cfg = Configuration('foobarbaz_wont_exist_ever')
        assert not cfg.loaded
        values = cfg.load()
        assert cfg.loaded
        assert values is cfg.values
        assert isinstance(values, configobj.ConfigObj)

    def test_configuration_dump_writes_to_stream(self):
        out = StringIO.StringIO()
        cfg = Configuration('foobarbaz_wont_exist_ever')
        cfg.dump(out)
        assert out.getvalue() == '\n'

    def test_configuration_dump_with_value(self):
        out = StringIO.StringIO()
        cfg = Configuration('foobarbaz_wont_exist_ever')
        cfg.load().merge(dict(foo='bar'))
        cfg.dump(out)
        assert out.getvalue() == 'foo = bar\n'

    def test_configuration_section_access_works(self):
        ctx = Bunch(info_name='section')
        section = dict(foo='bar')
        cfg = Configuration('foobarbaz_wont_exist_ever')
        cfg.load().merge(dict(section=section))
        assert cfg.section(ctx) == section

    def test_configuration_section_raises_on_unknown_name(self):
        ctx = Bunch(info_name='section')
        cfg = Configuration('foobarbaz_wont_exist_ever')
        with pytest.raises(click.LoggedFailure):
            cfg.section(ctx)

    def test_configuration_get_works(self):
        cfg = Configuration('foobarbaz_wont_exist_ever')
        cfg.load().merge(dict(foo='bar'))
        assert cfg.get('foo') == 'bar'

    def test_configuration_get_returns_default(self):
        cfg = Configuration('foobarbaz_wont_exist_ever')
        assert cfg.get('foo', None) is None

    def test_configuration_get_raises_without_default(self):
        cfg = Configuration('foobarbaz_wont_exist_ever')
        with pytest.raises(click.LoggedFailure):
            cfg.get('foo')
