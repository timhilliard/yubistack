"""
yubistack.ykauth
~~~~~~~~~~~~~~~~

Python Yubikey Stack - Authentication module
"""

import base64
import logging
import urllib

from passlib.context import CryptContext
import requests

from .config import (
    settings,
    TOKEN_LEN,
)
from .db import DBHandler
from .exceptions import YKAuthError
from .utils import (
    sign,
    generate_nonce,
)

logger = logging.getLogger(__name__)


class DBH(DBHandler):
    """
    Extending the generic DBHandler class with the required queries
    """
    def get_user(self, username):
        """
        Read user information for Yubiauth
        """
        query = """SELECT users.attribute_association_id AS users_attribute_association_id,
                          users.id AS users_id, users.name AS users_name,
                          users.auth AS users_auth
                     FROM users
                    WHERE users.name = %s"""
        self._execute(query, (username,))
        return self._dictfetchone()

    def get_token(self, user_id, token_id):
        """
        Read user attribute information for Yubiauth
        """
        query = """SELECT yubikeys.attribute_association_id AS yubikeys_attribute_association_id,
                          yubikeys.id AS yubikeys_id,
                          yubikeys.prefix AS yubikeys_prefix,
                          yubikeys.enabled AS yubikeys_enabled
                     FROM yubikeys
               INNER JOIN user_yubikeys
                       ON user_yubikeys.yubikey_id = yubikeys.id
                    WHERE user_yubikeys.user_id = %s
                      AND yubikeys.prefix = %s"""
        self._execute(query, (user_id, token_id))
        return self._dictfetchone()


class VerificationClient(object):
    """ Verification Client """
    def __init__(self, urls, client_id=None, apikey=None):
        self.urls = urls
        self.client_id = client_id
        self.apikey = base64.b64decode(apikey)

    def generate_query(self, otp, nonce, timestamp=False, timeout=None,
                       sync_level=None):
        """ Generate query """
        data = [('id', self.client_id),
                ('otp', otp),
                ('nonce', nonce)]
        if timestamp:
            data.append(('timestamp', '1'))

        if sync_level is not None:
            data.append(('sl', sync_level))

        if timeout:
            data.append(('timeout', timeout))

        query_string = urllib.parse.urlencode(data)
        if self.apikey:
            signature = sign(dict(data), self.apikey)
            query_string += '&h=%s' % (signature.replace('+', '%B'))
        return query_string

    def verify(self, otp, timestamp=False, sl=None, timeout=None,
               return_response=False):
        """ Make a HTTP call to the Yubikey Verification servers """
        nonce = generate_nonce()
        query = self.generate_query(otp, nonce, timestamp=timestamp,
                                    timeout=timeout, sync_level=sl)
        req = requests.get(self.urls[0] + '?' + query)
        print(req.text)


class Client(object):
    """ Authentication Client """
    def __init__(self):
        self.db = DBH(db='yubiauth')
        self.pwd_context = CryptContext(**settings['CRYPT_CONTEXT'])
        if settings['USE_NATIVE_YKVAL']:
            # Native verify
            from .ykval import Validator
            self.ykval_client = Validator()
        else:
            # Using yubico_client to verify against remote server
            from yubico_client import Yubico
            self.ykval_client = Yubico(settings['YKVAL_CLIENT_ID'],
                                       settings['YKVAL_CLIENT_SECRET'],
                                       api_urls=settings['YKVAL_SERVERS'])

    def _get_user_info(self, username):
        """
        Get user from DB

        Args:
            username

        Returns:
            dictionary of user data

        Raises:
            AuthFail if user does not exist
        """
        user = self.db.get_user(username)
        if not user:
            raise YKAuthError('UNKNOWN_USER')
        logger.debug('Found user: %s', user)
        return user

    def _check_token(self, user, token_id):
        """
        Check Token association with user

        Args:
            user: User data dict as recieved from _get_user_info()
            token_id: Token prefix (aka. publicname)

        Returns:
            None

        Raises:
            AuthFail if token is not associated with the user
            AithFail if token is disabled
        """
        token = self.db.get_token(user['users_id'], token_id)
        if not token:
            logger.error('Token %s is not associated with %s', token_id, user['users_name'])
            raise YKAuthError('INVALID_TOKEN')
        logger.debug('Found token: %s', token)
        if not token.get('yubikeys_enabled'):
            logger.error('Token %s is disabled for %s', token_id, user['users_name'])
            raise YKAuthError('DISABLED_TOKEN')

    def _validate_password(self, user, password):
        """
        Validate password against the hash in SQL
        """
        valid, new_hash = self.pwd_context.verify_and_update(str(password), user['users_auth'])
        if not valid:
            logger.error('%(users_name)s: Invalid password', user)
            raise YKAuthError('BAD_PASSWORD')
        if new_hash:
            # TODO: update user's hash with new_hash
            logger.warning("User %(users_name)s's hash needs update", user)
        return True

    def _validate_otp(self, otp):
        """
        Use Yubico client to validate OTP
        """
        try:
            if self.ykval_client.verify(otp):
                return True
            return False
        except Exception as err:
            logger.error('OTP Validation failed: %r', err)
            return False

    def authenticate(self, username, password, otp):
        """
        Yubistack user authentication

        Args:
            username: Username of the user
            password: Password/PIN of the user
            otp: Yubikey one time password

        Returns:
            dict of authentication data

        Authentication process:
            1. Check if token is enabled
            2. Check if token is associated with the user & enabled
            3. Validate users password
            4. Validate OTP (YKVal)
        """
        token_id = otp[:-TOKEN_LEN]
        # STEP 1: Check if token is enabled
        user = self._get_user_info(username)
        # STEP 2: Check if token is associated with the user & enabled
        self._check_token(user, token_id)
        # STEP 3: Validate users password
        self._validate_password(user, password)
        # STEP 4: Validate OTP
        self.ykval_client.verify(otp)
        return True
