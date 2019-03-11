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
import json
import logging
import pathlib
import sys
import time
import urllib

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
    subparsers = parser.add_subparsers(dest='cmd')
    subparsers.required = True

    download_parser = subparsers.add_parser(
        'download', help='Download a SideFX product.')
    download_parser.add_argument(
        'product', type=str, choices=['houdini', 'houdini-qt4'],
        help='Product to list: houdini, houdini-qt4')
    download_parser.add_argument(
        'version', type=str,
        help='The major version of Houdini. e.g. 16.5, 17.0.')
    download_parser.add_argument(
        'build', type=str,
        help=('Either a specific build number, e.g. 382, or the string '
              '"production" to get the latest production build'))
    download_parser.add_argument(
        'platform', type=str, choices=['win64', 'macos', 'linux'],
        help='The operating system to install Houdini on: win64, macos, linux')
    download_parser.set_defaults(func='download')

    list_builds_parser = subparsers.add_parser(
        'list-builds', help='List SideFX products available for download.')
    list_builds_parser.add_argument(
        'product', type=str, choices=['houdini', 'houdini-qt4'],
        help='Product to list: houdini, houdini-qt4')
    list_builds_parser.add_argument(
        '--version', type=str,
        help='The major version of Houdini. e.g. 16.5, 17.0.')
    list_builds_parser.add_argument(
        '--platform', type=str, choices=['win64', 'macos', 'linux'],
        help='The operating system to install Houdini on: win64, macos, linux')
    list_builds_parser.add_argument(
        '--only-production', action='store_true',
        help='Only return the production builds.')
    list_builds_parser.set_defaults(func='list_builds')

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
    log.debug('Client Secret Key: ******{}'.format(client_secret_key[-6:]))
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

    if args.func == 'list_builds':
        list_builds(args.endpoint_url, token, args.product,
                    version=args.version,
                    platform=args.platform,
                    only_production=args.only_production)
    elif args.func == 'download':
        download(args.endpoint_url, token,
                 args.product, args.version, args.build, args.platform)


def download(endpoint_url, token,
             product,
             version,
             build,
             platform):
    resp = call_api(endpoint_url, token, 'download.get_daily_build_download',
                    product, version, build, platform)
    log.debug(resp)
    download_url = resp.get('download_url')
    filename = resp.get('filename')
    log.info('Downloading {}'.format(filename))
    urllib.request.urlretrieve(download_url, filename)


def list_builds(endpoint_url, token, product,
                version=None,
                platform=None,
                only_production=None):
    resp = call_api(endpoint_url, token, 'download.get_daily_builds_list',
                    product, version, platform, only_production)
    for i in resp:
        log.info(i)


############
# Requests #
############

def call_api(endpoint_url, access_token, function_name, *args, **kwargs):
    """Call into the Web API."""
    response = requests.post(
        endpoint_url,
        headers={
            "Authorization": "Bearer " + access_token,
        },
        data=dict(
            json=json.dumps([function_name, args, kwargs]),
        ))
    if response.status_code == 200:
        return response.json()
    log.debug(response.status_code, response.reason, response.text)


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


#################
# Configuration #
#################

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
