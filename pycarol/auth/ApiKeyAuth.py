class ApiKeyAuth:
    def __init__(self, api_key):
        self.api_key = api_key
        self.carol = None

    def login(self, carol):
        self.carol = carol
        pass

    def authenticate_request(self, headers):
        headers['x-auth-key'] = self.api_key
        headers['x-auth-connectorid'] = self.carol.connector_id
