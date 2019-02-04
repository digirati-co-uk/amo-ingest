import requests
import logging


class JWTClient:

    def __init__(self, login_uri, username, password):

        self.login_uri = login_uri
        self.username = username
        self.password = password
        self.token = self.get_token(refresh=True)

    def get_token(self, refresh=False):

        if refresh or self.token is None:
            logging.debug("Refreshing token")
            body = {
                'username': self.username,
                'password': self.password
             }
            response = requests.post(self.login_uri, json=body)
            if response.status_code == requests.codes.ok:
                self.token = response.json().get('token')
                logging.debug("Token refreshed: {token}".format(token=self.token))
            else:
                logging.error("Could not obtain authentication token")
                self.token = None

        return self.token

    def handle_request(self, method, url, **kwargs):

        imp = getattr(requests, method)
        logging.debug("Handling request for {method}".format(method=method))

        if self.token is None:
            logging.debug("Found None token")
            raise ValueError("Authentication token not available")

        kwargs = self.ensure_auth_header(kwargs)
        response = imp(url, **kwargs)
        logging.debug("Initial response code was {code}".format(code=response.status_code))
        if response.status_code == requests.codes.forbidden or response.status_code == requests.codes.unauthorized:
            kwargs = self.ensure_auth_header(kwargs, refresh=True)
            response = imp(url, **kwargs)
            logging.debug("Subsequent response code was {code}".format(code=response.status_code))
        return response

    def ensure_auth_header(self, kw, refresh=False):

        if 'headers' not in kw:
            kw['headers'] = {}
        kw['headers']['Authorization'] = 'Bearer ' + self.get_token(refresh=refresh)
        logging.debug("Header set")
        return kw

    def get(self, url, **kwargs):

        return self.handle_request('get', url, **kwargs)

    def post(self, url, **kwargs):

        return self.handle_request('post', url, **kwargs)

    def put(self, url, **kwargs):

        return self.handle_request('put', url, **kwargs)

    def delete(self, url, **kwargs):

        return self.handle_request('delete', url, **kwargs)

    def head(self, url, **kwargs):

        return self.handle_request('head', url, **kwargs)

    def patch(self, url, **kwargs):

        return self.handle_request('patch', url, **kwargs)
