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

from oslo.middleware import request_id as oslo_request_id
from oslo.utils import importutils
from oslo_context import context

from senlin.common import exception
from senlin.common import policy
from senlin.common import wsgi
from senlin.db import api as db_api


class RequestContext(context.RequestContext):
    """
    Stores information about the security context under which the user
    accesses the system, as well as additional request information.
    """

    def __init__(self, auth_token=None, auth_token_info=None,
                 username=None, password=None, user_id=None, is_admin=None,
                 tenant=None, tenant_id=None, auth_url=None,
                 roles=None, region_name=None,
                 read_only=False, show_deleted=False,
                 request_id=None, **kwargs):
        """
         :param kwargs: Extra arguments that might be present, but we ignore
            because they possibly came in from older rpc messages.
        """
        super(RequestContext, self).__init__(auth_token=auth_token,
                                             user=username, tenant=tenant,
                                             is_admin=is_admin,
                                             read_only=read_only,
                                             show_deleted=show_deleted,
                                             request_id=request_id)

        self.username = username
        self.user_id = user_id
        self.password = password
        self.region_name = region_name
        self.tenant_id = tenant_id
        self.auth_token_info = auth_token_info
        self.auth_url = auth_url
        self.roles = roles or []
        self._session = None
        self._clients = None
        self.policy = policy.Enforcer()

        if is_admin is None:
            self.is_admin = self.policy.check_is_admin(self)
        else:
            self.is_admin = is_admin

    @property
    def session(self):
        if self._session is None:
            self._session = db_api.get_session()
        return self._session

    def to_dict(self):
        return {'auth_token': self.auth_token,
                'username': self.username,
                'user_id': self.user_id,
                'password': self.password,
                'tenant': self.tenant,
                'tenant_id': self.tenant_id,
                'auth_token_info': self.auth_token_info,
                'auth_url': self.auth_url,
                'roles': self.roles,
                'is_admin': self.is_admin,
                'user': self.user,
                'request_id': self.request_id,
                'show_deleted': self.show_deleted,
                'region_name': self.region_name}

    @classmethod
    def from_dict(cls, values):
        return cls(**values)


def get_admin_context(show_deleted=False):
    return RequestContext(is_admin=True, show_deleted=show_deleted)


class ContextMiddleware(wsgi.Middleware):

    def __init__(self, app, conf, **local_conf):
        # Determine the context class to use
        self.ctxcls = RequestContext
        if 'context_class' in local_conf:
            self.ctxcls = importutils.import_class(local_conf['context_class'])

        super(ContextMiddleware, self).__init__(app)

    def make_context(self, *args, **kwargs):
        """
        Create a context with the given arguments.
        """
        return self.ctxcls(*args, **kwargs)

    def process_request(self, req):
        """
        Extract any authentication information in the request and
        construct an appropriate context from it.
        """
        headers = req.headers
        environ = req.environ

        try:
            username = None
            password = None

            if headers.get('X-Auth-User') is not None:
                username = headers.get('X-Auth-User')
                password = headers.get('X-Auth-Key')

            user_id = headers.get('X-User-Id')
            token = headers.get('X-Auth-Token')
            tenant = headers.get('X-Tenant-Name')
            tenant_id = headers.get('X-Tenant-Id')
            region_name = headers.get('X-Region-Name')
            auth_url = headers.get('X-Auth-Url')
            roles = headers.get('X-Roles')
            if roles is not None:
                roles = roles.split(',')
            token_info = environ.get('keystone.token_info')
            req_id = environ.get(oslo_request_id.ENV_REQUEST_ID)

        except Exception:
            raise exception.NotAuthenticated()

        req.context = self.make_context(auth_token=token,
                                        tenant=tenant, tenant_id=tenant_id,
                                        username=username,
                                        user_id=user_id,
                                        password=password,
                                        auth_url=auth_url,
                                        roles=roles,
                                        request_id=req_id,
                                        auth_token_info=token_info,
                                        region_name=region_name)


def ContextMiddleware_filter_factory(global_conf, **local_conf):
    """
    Factory method for paste.deploy
    """
    conf = global_conf.copy()
    conf.update(local_conf)

    def filter(app):
        return ContextMiddleware(app, conf)

    return filter
