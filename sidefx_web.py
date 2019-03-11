# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT
##############################################################################
# MIT License
#
# Copyright (c) 2019 Thanh Ha
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
##############################################################################
"""CLI for SideFX Web API."""
import argparse
import base64
import configparser
import logging
import pathlib
import sys
import time

import requests

CONFIG_DIR = '/'.join([str(pathlib.Path.home()), '.config', 'sidefx-web'])
CONFIG_FILE = '/'.join([CONFIG_DIR, 'config.ini'])


def cli():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--access-token-url', type=str,
        default='https://www.sidefx.com/oauth2/application_token',
        help='URL for the SideFX OAuth application token.')
    parser.add_argument(
        '--endpoint-url', type=str, default='https://www.sidefx.com/api/',
        help='URL for the SideFX Web API endpoint.')
    parser.add_argument('--debug', action='store_true',
                        help='Enable DEBUG output.')
    parser.add_argument('--setup', '-s', action='store_true',
                        help='Setup configuration for SideFX Web API.')
    args = parser.parse_args()

    if args.debug:
        logging.getLogger("").setLevel(logging.DEBUG)

    if args.setup:
        setup()

    cfg = get_config()
    client_id = cfg.get('Auth', 'client_id')
    client_secret_key = cfg.get('Auth', 'client_secret_key')
    token = cfg.get('Cache', 'access_token', fallback=None)
    token_expiry = cfg.get('Cache', 'access_token_expiry', fallback=None)
    if token_expiry:
        token_expiry = float(token_expiry)

    log.debug('Access Token URL: {}'.format(args.access_token_url))
    log.debug('Client ID: {}'.format(client_id))
    log.debug('Client Secret Key: {}'.format(client_secret_key))
    log.debug('Cached Access Token: {}'.format(token))
    log.debug('Cached Access Token Expiry: {}'.format(token_expiry))

    if (token is None or token_expiry is None or token_expiry < time.time()):
        log.info('Fetching a new token.')
        token, token_expiry = get_access_token(
            args.access_token_url, client_id, client_secret_key)

        if not cfg.has_section('Cache'):
            cfg.add_section('Cache')
        cfg.set('Cache', 'access_token', token)
        cfg.set('Cache', 'access_token_expiry', str(token_expiry))
        save_config(cfg)

    log.debug('Access Token: {}'.format(token))
    log.debug('Access Token Expiry Time: {}'.format(token_expiry))


def get_access_token(url, client_id, client_secret_key):
    auth = base64.b64encode("{}:{}".format(
        client_id, client_secret_key).encode()
    ).decode('utf-8')
    headers = {
        'Authorization': 'Basic {0}'.format(auth),
    }
    req = requests.post(url, headers=headers)

    if req.status_code != 200:
        print('ERROR: {} {}'.format(req.status_code, req.reason))
        sys.exit(1)

    data = req.json()
    expiry_time = time.time() - 2 + data['expires_in']
    return data['access_token'], expiry_time


def get_config():
    cfg = configparser.ConfigParser()
    try:
        with open(CONFIG_FILE, 'r') as f:
            cfg.read(CONFIG_FILE)
    except FileNotFoundError:
        setup()
        cfg.read(CONFIG_FILE)
    return cfg


def save_config(cfg):
    cfgfile = pathlib.Path(CONFIG_FILE)
    with open(CONFIG_FILE, 'w') as f:
        cfg.write(f)
        log.debug('Saved config file.')


def setup():
    log.info('Credentials are needed in order to use the SideFX Web API. '
             'Detailed instructions available at '
             'https://www.sidefx.com/docs/api/credentials/index.html')
    client_id = input('Enter your Client ID: ')
    client_secret_key = input('Enter your Client Secret Key: ')
    log.debug('Set Client ID to {}'.format(client_id))
    log.debug('Set Client Secret Key to {}'.format(client_secret_key))

    cfg = configparser.ConfigParser()
    if not cfg.has_section('Auth'):
        cfg.add_section('Auth')
    cfg.set('Auth', 'client_id', client_id)
    cfg.set('Auth', 'client_secret_key', client_secret_key)

    cfgdir = pathlib.Path(CONFIG_DIR)
    cfgdir.mkdir(parents=True, exist_ok=True)
    save_config(cfg)


class LogFormatter(logging.Formatter):
    """Custom log formatter."""

    default_fmt = logging.Formatter('%(levelname)s: %(message)s')
    debug_fmt = logging.Formatter(
        '%(levelname)s: %(name)s:%(lineno)d: %(message)s')
    info_fmt = logging.Formatter('%(message)s')

    def format(self, record):
        """Format log messages depending on log level."""
        if record.levelno == logging.INFO:
            return self.info_fmt.format(record)
        if record.levelno == logging.DEBUG:
            return self.debug_fmt.format(record)
        else:
            return self.default_fmt.format(record)


console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(LogFormatter())
logging.getLogger("").setLevel(logging.INFO)
logging.getLogger("").addHandler(console_handler)
log = logging.getLogger(__name__)
