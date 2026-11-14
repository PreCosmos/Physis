#!/usr/bin/env python3
"""Stdio bridge from the Claude desktop app to Unreal's built-in MCP server.

The desktop app starts this script and talks MCP over stdin/stdout; every message
is forwarded to http://127.0.0.1:8000/mcp. Standard library only (no Node needed).
If Unreal is restarted, the bridge re-initializes its Unreal session on its own.
"""
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, ProxyHandler

URL = 'http://127.0.0.1:8000/mcp'
http = build_opener(ProxyHandler({}))
state = {'session': None, 'version': None, 'init': None}


def log(*parts):
    print('[unreal-bridge]', *parts, file=sys.stderr, flush=True)


def post(message):
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream'}
    if state['session']:
        headers['Mcp-Session-Id'] = state['session']
    if state['version']:
        headers['Mcp-Protocol-Version'] = state['version']
    request = Request(URL, data=json.dumps(message).encode(), headers=headers)
    with http.open(request, timeout=600) as response:
        state['session'] = response.headers.get('Mcp-Session-Id', state['session'])
        raw = response.read().decode()
    replies = []
    if raw.lstrip().startswith(('{', '[')):
        replies.append(json.loads(raw))
    else:  # server-sent events
        for line in raw.splitlines():
            if line.startswith('data:') and line[5:].strip():
                replies.append(json.loads(line[5:].strip()))
    return replies


def reconnect():
    """Open a fresh Unreal session by replaying the client's initialize."""
    state['session'] = None
    state['version'] = None
    if state['init']:
        for reply in post(state['init']):
            version = reply.get('result', {}).get('protocolVersion')
            if version:
                state['version'] = version
        post({'jsonrpc': '2.0', 'method': 'notifications/initialized'})


def forward(message):
    if message.get('method') == 'initialize':
        state['init'] = message
        state['session'] = None
        state['version'] = None
    try:
        replies = post(message)
    except HTTPError as error:
        if error.code in (400, 404) and message.get('method') != 'initialize' and state['init']:
            log('Unreal session expired; reconnecting')
            reconnect()
            replies = post(message)
        else:
            raise
    for reply in replies:
        version = reply.get('result', {}).get('protocolVersion') if isinstance(reply, dict) else None
        if version:
            state['version'] = version
    return replies


def main():
    log('started; forwarding to', URL)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        message = json.loads(line)
        try:
            replies = forward(message)
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as error:
            log('request failed:', error)
            if 'id' in message:
                replies = [{'jsonrpc': '2.0', 'id': message['id'], 'error': {
                    'code': -32000,
                    'message': 'Unreal MCP is not reachable at %s (%s). Open the Physis project '
                               'in Unreal with the MCP server running, then try again.' % (URL, error)}}]
            else:
                replies = []
        for reply in replies:
            sys.stdout.write(json.dumps(reply) + '\n')
            sys.stdout.flush()


if __name__ == '__main__':
    main()
