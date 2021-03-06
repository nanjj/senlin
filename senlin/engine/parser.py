# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import json
import os
import requests
import six
from six.moves import urllib
import yaml

from senlin.common import i18n
from senlin.openstack.common import log as logging

_LE = i18n._LE
LOG = logging.getLogger(__name__)

# Try LibYAML if available
if hasattr(yaml, 'CSafeLoader'):
    Loader = yaml.CSafeLoader
else:
    Loader = yaml.SafeLoader

if hasattr(yaml, 'CSafeDumper'):
    Dumper = yaml.CSafeDumper
else:
    Dumper = yaml.SafeDumper


class YamlLoader(Loader):
    def __init__(self, stream):
        if isinstance(stream, file):
            self._curdir = os.path.split(stream.name)[0]
        else:
            self._curdir = './'
        super(YamlLoader, self).__init__(stream)

    def include(self, node):
        url = self.construct_scalar(node)
        components = urllib.parse.urlparse(url)

        if components.scheme == '':
            try:
                url = os.path.join(self._curdir, url)
                with open(url, 'r') as f:
                    return yaml.load(f, Loader)
            except Exception as ex:
                raise Exception('Failed loading file %s: %s' % (url,
                                six.text_type(ex)))
        try:
            resp = requests.get(url, stream=True)
            resp.raise_for_status()
            reader = resp.iter_content(chunk_size=1024)
            result = ''
            for chunk in reader:
                result += chunk
            return yaml.load(result, Loader)
        except Exception as ex:
            raise Exception('Failed retrieving file %s: %s' % (url,
                            six.text_type(ex)))

    def process_unicode(self, node):
        # Override the default string handling function to always return
        # unicode objects
        return self.construct_scalar(node)


YamlLoader.add_constructor('!include', YamlLoader.include)
YamlLoader.add_constructor(u'tag:yaml.org,2002:str',
                           YamlLoader.process_unicode)
YamlLoader.add_constructor(u'tag:yaml.org,2002:timestamp',
                           YamlLoader.process_unicode)


def simple_parse(in_str):
    try:
        out_dict = json.loads(in_str)
    except ValueError:
        try:
            out_dict = yaml.load(in_str, Loader=YamlLoader)
        except yaml.YAMLError as yea:
            yea = six.text_type(yea)
            msg = _('Error parsing input: %s') % yea
            raise ValueError(msg)
        else:
            if out_dict is None:
                out_dict = {}

    if not isinstance(out_dict, dict):
        msg = _('The input is not a JSON object or YAML mapping.')
        raise ValueError(msg)

    return out_dict


def parse_profile(profile_str):
    '''
    Parse and validate the specified string as a profile.
    '''
    data = simple_parse(profile_str)

    # TODO(Qiming):
    # Construct a profile object based on the type specified

    return data


def parse_policy(policy_str):
    '''
    Parse and validate the specified string as a policy.
    '''
    data = simple_parse(policy_str)

    # TODO(Qiming):
    # Construct a policy object based on the type specified

    return data


def parse_action(action):
    '''
    Parse and validate the specified string as a action.
    '''
    if not isinstance(action, six.string_types):
        # TODO(Qiming): Throw exception
        return None

    data = {}
    try:
        data = yaml.load(action, Loader=Loader)
    except Exception as ex:
        # TODO(Qiming): Throw exception
        LOG.error(_LE('Failed parsing given data as YAML: %s'),
                  six.text_type(ex))
        return None

    # TODO(Qiming): Construct a action object based on the type specified

    return data
