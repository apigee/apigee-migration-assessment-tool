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


"""
Generates Apigee Edge SAAS Access Token
"""


import base64
import hashlib
import hmac
import os
import struct
import sys
import time
import requests  # pylint: disable=E0401


def generate_totp(otp_secret, interval=30, digits=6, for_time=None):
    """Generates an RFC 6238 SHA-1 TOTP code using the Python stdlib."""
    cleaned = otp_secret.strip().replace(" ", "").upper()
    if not cleaned:
        raise ValueError("OTP secret must not be empty")
    missing_padding = len(cleaned) % 8
    if missing_padding:
        cleaned += "=" * (8 - missing_padding)
    key = base64.b32decode(cleaned, casefold=True)
    current_time = time.time() if for_time is None else for_time
    counter = int(current_time // interval)
    msg = struct.pack(">Q", counter)
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code_int = (
        ((digest[offset] & 0x7F) << 24)
        | (digest[offset + 1] << 16)
        | (digest[offset + 2] << 8)
        | digest[offset + 3]
    )
    return f"{code_int % (10 ** digits):0{digits}d}"


def fetch_apigee_token():
    """
    Generates an MFA token and uses it to fetch an Apigee OAuth access token.
    Reads credentials from environment variables.
    """
    apigee_user = os.getenv('APIGEE_EDGE_USER')
    apigee_password = os.getenv('APIGEE_EDGE_PASSWORD')
    otp_secret = os.getenv('OTP_SECRET')

    if not all([apigee_user, apigee_password, otp_secret]):
        print(
            "Error: Please set the APIGEE_EDGE_USER, APIGEE_EDGE_PASSWORD, and OTP_SECRET environment variables.",   # noqa pylint: disable=C0301
            file=sys.stderr
        )
        sys.exit(1)

    try:
        mfa_token = generate_totp(otp_secret)
    except Exception as e:    # noqa pylint: disable=W0718
        print(f"Error generating MFA token: {e}", file=sys.stderr)
        sys.exit(1)

    url = "https://login.apigee.com/oauth/token"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded;charset=utf-8",
        "Accept": "application/json;charset=utf-8",
    }
    params = {"mfa_token": mfa_token}
    data = {
        "username": apigee_user,
        "password": apigee_password,
        "grant_type": "password",
    }

    try:
        response = requests.post(
            url,
            headers=headers,
            params=params,
            data=data,
            auth=("edgecli", "edgeclisecret"),
            timeout=3,
        )
        response.raise_for_status()
        access_token = response.json().get("access_token")
        if not access_token:
            print("Error: 'access_token' not found in the response.", file=sys.stderr)   # noqa pylint: disable=C0301
            return None
        return access_token
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP Error occurred: {http_err}", file=sys.stderr)
        print(f"Response Body: {http_err.response.text}", file=sys.stderr)
    except requests.exceptions.RequestException as req_err:
        print(f"A request error occurred: {req_err}", file=sys.stderr)
    return None


if __name__ == "__main__":
    token = fetch_apigee_token()
    if token:
        print(f"::set-output name=access_token::{token}")
    else:
        # Exit with a non-zero status code to fail the workflow step on error
        print("Failed to retrieve access token.", file=sys.stderr)
        sys.exit(1)
