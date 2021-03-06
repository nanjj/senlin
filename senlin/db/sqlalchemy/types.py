#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import json

from sqlalchemy.dialects import mysql
from sqlalchemy import types


dumps = json.dumps
loads = json.loads


class LongText(types.TypeDecorator):
    impl = types.Text

    def load_dialect_impl(self, dialect):
        if dialect.name == 'mysql':
            return dialect.type_descriptor(mysql.LONGTEXT())
        else:
            return self.impl


class Json(LongText):

    def process_bind_param(self, value, dialect):
        return dumps(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return loads(value)


def associate_with(sqltype):
    # TODO(leizhang) When we removed sqlalchemy 0.7 dependence
    # we can import MutableDict directly and remove ./mutable.py
    try:
        from sqlalchemy.ext import mutable
        mutable.MutableDict.associate_with(Json)
    except ImportError:
        from senlin.db.sqlalchemy import mutable
        mutable.MutableDict.associate_with(Json)

associate_with(LongText)
associate_with(Json)
