#!/usr/bin/python

# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License

"""Provides a REST client for interacting with
Apigee Management APIs.

This module offers a versatile `RestClient` class
for making HTTP requests to Apigee Management APIs.
It supports various authentication methods, handles
different response formats (JSON, plain text,
raw bytes), and provides error handling for
Apigee-specific error codes. It simplifies
interaction with Apigee by abstracting away
low-level request details and providing a
Pythonic interface.
"""

import json
import requests  # pylint: disable=E0401
from urllib3.exceptions import InsecureRequestWarning  # pylint: disable=E0401
from base_logger import logger, EXEC_INFO

# Suppress the warnings from urllib3
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)   # noqa pylint: disable=E1101

UNKNOWN_ERROR = 'internal.unknown'


class ApigeeError(Exception):
    """Represents an error during interaction with
    the Apigee management API.
    """
    def __init__(self, status_code, error_code, message):
        """Initializes an ApigeeError.

        Args:
            status_code (int): The HTTP status code.
            error_code (str): The Apigee error code.
            message (str):  A descriptive error message.
        """
        self.status_code = status_code
        self.error_code = error_code
        self.message = message

    def __str__(self):
        """Returns a string representation of the error.

        Returns:
            str: A string containing the status
                 code and message.
        """
        return f'{self.status_code}: {self.message}'


class RestClient(object):  # noqa pylint: disable=R0205
    """A client for making HTTP requests to RESTful
    APIs, especially Apigee.

    This client simplifies interaction with REST APIs
    by providing methods for common HTTP operations
    (GET, POST, PUT, PATCH, DELETE) with support for
    different authentication mechanisms (Basic,
    OAuth2), various content types, and streamlined
    error handling. It's particularly useful for
    working with Apigee Management APIs.

    Attributes:
        auth_type (str): The authentication type
            ('basic' or 'oauth').
        token (str): The authentication token
            (Basic auth credentials or OAuth2 token).
        ssl_verify (bool): Whether to verify SSL
            certificates (default: True).
        session (requests.Session): The underlying
            requests session object.
        base_headers (dict): Default headers for
            all requests.
    """

    def __init__(self, auth_type, token, ssl_verify=True):
        self._allowed_auth_types = ['basic', 'oauth']
        self.session = requests.Session()
        self.session.verify = ssl_verify
        if auth_type not in self._allowed_auth_types:
            raise ValueError(
                f'Unknown Auth type , Allowed types are {" ,".join(self._allowed_auth_types)}')   # noqa pylint: disable=C0301
        self.auth_type = auth_type

        self.base_headers = {
            'Authorization': f'Basic {token}' if auth_type == 'basic' else f'Bearer {token}'   # noqa pylint: disable=C0301
        }

    def get(self, url, params=None):
        """Makes a GET request.

        Args:
            url (str): The URL to send the request to.
            params (dict, optional): Query parameters.

        Returns:
            The response content.

        Raises:
            ApigeeError: If the API request returns
                an error.
        """
        headers = self.base_headers.copy()
        response = self.session.get(url, params=params, headers=headers)
        logger.debug(f"Response: {response.content}")  # noqa pylint: disable=W1203
        return self._process_response(response)

    def file_get(self, url, params=None):
        """Makes a GET request for file download.

        Args:
            url (str): The URL.
            params (dict, optional): Query parameters.

        Returns:
            The raw response content.

        Raises:
            ApigeeError: If an error occurs.
        """
        headers = self.base_headers.copy()
        response = self.session.get(
            url, params=params, headers=headers, stream=True)
        logger.debug(f"Response: {response.content}")  # noqa pylint: disable=W1203
        return self._process_response(response)

    def post(self, url, data=None):
        """Makes a POST request.

        Args:
            url (str): The URL.
            data (dict, optional): Request body data.

        Returns:
            The response content.

        Raises:
            ApigeeError: If an error occurs.
        """
        headers = self.base_headers.copy()
        response = self.session.post(
            url, data=json.dumps(data or {}), headers=headers)
        logger.debug(f"Response: {response.content}")  # noqa pylint: disable=W1203
        return self._process_response(response)

    def file_post(self, url, params=None, data=None, files=None):
        """Makes a file upload POST request.

        Args:
            url (str): The URL.
            params (dict, optional): Query params.
            data (dict, optional):  Request body.
            files (dict, optional): Files to upload.

        Returns:
            The response content.

        Raises:
            ApigeeError: If an error occurs.

        """
        headers = self.base_headers.copy()
        headers['Content-Type'] = 'application/octet-stream'
        response = self.session.post(
            url, data=data, files=files, headers=headers, params=params)
        logger.debug(f"Response: {response.content}")  # noqa pylint: disable=W1203
        return self._process_response(response)

    def patch(self, url, data=None):
        """Makes a PATCH request.

        Args:
            url (str): The URL.
            data (dict, optional): Request body data.

        Returns:
            The response content.

        Raises:
            ApigeeError:  If an error occurs.
        """
        headers = self.base_headers.copy()
        response = self.session.patch(
            url, data=json.dumps(data or {}), headers=headers)
        logger.debug(f"Response: {response.content}")  # noqa pylint: disable=W1203
        return self._process_response(response)

    def put(self, url, data=None):
        """Makes a PUT request.

        Args:
            url (str): The URL.
            data (dict, optional): The request body.

        Returns:
            The response content.

        Raises:
            ApigeeError: If an error occurs.
        """
        headers = self.base_headers.copy()
        response = self.session.put(
            url, data=json.dumps(data or {}), headers=headers)
        logger.debug(f"Response: {response.content}")  # noqa pylint: disable=W1203
        return self._process_response(response)

    def delete(self, url, params=None):
        """Makes a DELETE request.

        Args:
            url (str): The URL.
            params (dict, optional): Query parameters.

        Returns:
            The response content.

        Raises:
            ApigeeError: If an error occurs.
        """
        headers = self.base_headers.copy()
        response = self.session.delete(url, headers=headers, params=params or {})     # noqa pylint: disable=C0301
        logger.debug(f"Response: {response.content}")  # noqa pylint: disable=W1203
        return self._process_response(response)

    def _process_response(self, response):
        """Processes the response from an HTTP request.

        Args:
            response: The HTTP response object.

        Returns:
            The content of the response.
        """
        return self._parse(response).content()

    def _parse(self, response):
        """Parses the response content based on content type.

        Args:
            response: The HTTP response object.

        Returns:
            A Response object (JsonResponse, PlainResponse,
            EmptyResponse, or RawResponse).
        """
        if not response.text:
            return EmptyResponse(response.status_code)
        try:
            if response.headers['Content-Type'] == 'application/octet-stream':
                return RawResponse(response)
            if response.headers['Content-Type'].startswith('application/json'):
                return JsonResponse(response)
            return PlainResponse(response)
        except ValueError:
            logger.error('Unable to parse response as JSON',
                         exc_info=EXEC_INFO)
            return ""


class Response(object):  # noqa pylint: disable=R0205,R0903
    """Represents an HTTP response.

    Base class for different response types
    (JSON, plain text, raw, etc.).  Handles
    common response processing like status code
    checking and error raising.

    Attributes:
        _status_code (int): The HTTP status code.
        _content: The response content.
    """
    def __init__(self, status_code, content):
        """Initializes a Response object.

        Args:
            status_code (int):  The HTTP status code.
            content: The response content.
        """
        self._status_code = status_code
        self._content = content

    def content(self):
        """Returns the response content.

        Raises:
            ApigeeError: If the response represents
                an error.

        Returns:
             The response content if successful.
        """
        if self._is_error():
            raise ApigeeError(status_code=self._status_code,
                              error_code=self._error_code(),
                              message=self._error_message())
        return self._content

    def _is_error(self):
        """Checks if the response is an error.

        Returns:
            True if error, False otherwise.
        """
        return self._status_code is None  # or self._status_code >= 400   # noqa pylint: disable=C0301

    # Adding these methods to force implementation in subclasses because they are references in this parent class     # noqa pylint: disable=C0301
    def _error_code(self):
        """Returns the error code.

        Must be implemented by subclasses.

        Raises:
            NotImplementedError:  If not
                implemented.
        """
        raise NotImplementedError

    def _error_message(self):
        """Returns the error message.

        Must be implemented by subclasses.

        Raises:
            NotImplementedError: If not
                implemented.
        """
        raise NotImplementedError


class JsonResponse(Response):  # noqa pylint: disable=R0903
    """Represents a JSON HTTP response.

    Parses and handles JSON response content,
    including error checking. Inherits from
    the `Response` base class.
    """
    def __init__(self, response):
        """Initializes a JsonResponse.

        Args:
            response: The HTTP response object.
        """
        content = json.loads(response.text)
        super(JsonResponse, self).__init__(response.status_code, content)   # noqa pylint: disable=R1725

    def _error_code(self):
        """Returns the JSON error code.

        Checks various keys for the error code
        in the JSON content.

        Returns:
            str: The error code, or a default
                if not found.
        """

        if 'errorCode' in self._content:
            return self._content.get('errorCode')
        if 'error' in self._content:
            return self._content.get('error')
        return UNKNOWN_ERROR

    def _error_message(self):
        """Returns the JSON error message.

        Extracts the error message from the
        JSON content.

        Returns:
             str: The error message or an empty string.
        """
        message = self._content.get('message', '')
        if message is not None and message != '':
            return message
        return self._content.get('error', '')


class PlainResponse(Response):  # noqa pylint: disable=R0903
    """Represents a plain text HTTP response.

    Handles plain text content. Inherits from
    the `Response` base class.
    """
    def __init__(self, response):
        """Initializes a PlainResponse.

        Args:
            response: The HTTP response object.
        """
        super(PlainResponse, self).__init__(   # noqa pylint: disable=R1725
            response.status_code, response.text)

    def _error_code(self):
        """Returns the error code.

        Returns:
            str: The default unknown error code.
        """
        return UNKNOWN_ERROR

    def _error_message(self):
        """Returns the error message.

        Returns:
            str: The plain text content as the error message.
        """
        return self._content


class EmptyResponse(Response):  # noqa pylint: disable=R0903
    """Represents an empty HTTP response.

    Handles responses with no content. Inherits
    from the `Response` base class.
    """
    def __init__(self, status_code):
        """Initializes an EmptyResponse.

        Args:
            status_code (int): The HTTP status code.
        """
        super(EmptyResponse, self).__init__(status_code, '')   # noqa pylint: disable=R1725

    def _error_code(self):
        """Returns the error code.

        Returns:
            str: The default unknown error code.
        """
        return UNKNOWN_ERROR

    def _error_message(self):
        """Returns the error message.

        Returns:
            str: An empty string.
        """
        return ''


class RawResponse(Response):  # noqa pylint: disable=R0903
    """Represents a raw byte HTTP response.

    Handles responses with raw byte content,
    typically for file downloads. Inherits
    from the `Response` base class.
    """
    def __init__(self, response):
        """Initializes a RawResponse.

        Args:
            response: The HTTP response object.
        """
        content = response.content
        super(RawResponse, self).__init__(response.status_code, content)   # noqa pylint: disable=R1725

    def _error_code(self):
        """Returns the error code.

        Returns:
            str: The default unknown error code.
        """
        return UNKNOWN_ERROR

    def _error_message(self):
        """Returns the error message.

        Returns:
            bytes: The raw byte content as the error message. # noqa
        """
        return self._content
