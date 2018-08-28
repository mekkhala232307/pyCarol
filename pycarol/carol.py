from .tenants import *
from .storage import *
from .connectors import *
from .carolina import *
from .staging import *
from .tasks import *

from urllib3.util.retry import Retry
import requests
from requests.adapters import HTTPAdapter


class Carol:
    def __init__(self, domain, app_name, auth, connector_id='0a0829172fc2433c9aa26460c31b78f0', port=443, verbose=False):
        self.domain = domain
        self.app_name = app_name
        self.port = port
        self.verbose = verbose
        self.tenants = Tenants(self)
        self.storage = Storage(self)
        self.connectors = Connectors(self)
        self.carolina = Carolina(self)
        self.staging = Staging(self)
        self.tasks = Tasks(self)
        self.tenant = self.tenants.get_tenant_by_domain(domain)
        self.connector_id = connector_id
        self.auth = auth
        self.auth.set_connector_id(self.connector_id)
        self.auth.login(self)
        self.response = None

    @staticmethod
    def _retry_session(retries=5, session=None, backoff_factor=0.3, status_forcelist=(500, 502, 503, 504)):
        session = session or requests.Session()
        retry = Retry(
            total=retries,
            read=retries,
            connect=retries,
            backoff_factor=backoff_factor,
            status_forcelist=status_forcelist,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session


    def call_api(self, path, method=None, data=None, auth=True, params=None, content_type='application/json',
                 retries=5, session=None, backoff_factor=0.3, status_forcelist=(500, 502, 503, 504)):
        url = 'https://{}.carol.ai:{}/api/{}'.format(self.domain, self.port, path)

        if method is None:
            if data is None:
                method = 'GET'
            else:
                method = 'POST'

        headers = {'accept': 'application/json'}
        if auth:
            self.auth.authenticate_request(headers)

        data_json = None
        if method == 'GET':
            pass
            
        elif (method == 'POST') or (method == 'DELETE') or (method == 'PUT'):
            headers['content-type'] = content_type

            if content_type == 'application/json':
                data_json = data
                data = None


        section = self._retry_session(retries=retries, session=session, backoff_factor=backoff_factor,
                                      status_forcelist=status_forcelist)
        response = section.request(method=method, url=url, data=data, json=data_json,
                                   headers=headers, params=params)
        
        if self.verbose:
            if data_json is not None:
                print("Calling {} {}. Payload: {}. Params: {}".format(method, url, data_json, params))
            else:
                print("Calling {} {}. Payload: {}. Params: {}".format(method, url, data, params))
            print("        Headers: {}".format(headers))

        response.encoding = 'utf-8'
        self.response = response
        if response.ok:
            return json.loads(response.text)
        else:
            raise Exception(json.loads(response.text))

    def issue_api_key(self):
        resp = self.call_api('v2/apiKey/issue', data={
            'connectorId': self.connector_id
        }, content_type='application/x-www-form-urlencoded')
        return resp

    def api_key_details(self, api_key, connector_id):

        resp = self.call_api('v2/apiKey/details',
                             params = {"apiKey": api_key,
                                            "connectorId": connector_id})

        return resp

    def api_key_revoke(self, connector_id):

        resp = self.call_api('v2/apiKey/revoke', method='DELETE',
                             content_type='application/x-www-form-urlencoded',
                             params = {"connectorId": connector_id})

        return resp