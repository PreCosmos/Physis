#!/usr/bin/env python3
"""Small local client for Unreal's built-in MCP server. No external packages."""
import argparse
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, ProxyHandler


class UnrealMCP:
    def __init__(self, timeout=30):
        self.url = 'http://127.0.0.1:8000/mcp'
        self.timeout = timeout
        self.session = None
        self.version = '2025-03-26'
        self.counter = 0
        self.http = build_opener(ProxyHandler({}))

    def request(self, method, params=None, notification=False):
        payload = {'jsonrpc': '2.0', 'method': method}
        if params is not None:
            payload['params'] = params
        if not notification:
            self.counter += 1
            payload['id'] = self.counter
        headers = {'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream'}
        if self.session:
            headers['Mcp-Session-Id'] = self.session
            headers['Mcp-Protocol-Version'] = self.version
        request = Request(self.url, data=json.dumps(payload).encode(), headers=headers)
        with self.http.open(request, timeout=self.timeout) as response:
            self.session = response.headers.get('Mcp-Session-Id', self.session)
            raw = response.read().decode()
        if not raw.strip():
            return None
        result = json.loads(raw)
        if 'error' in result:
            raise RuntimeError(json.dumps(result['error']))
        return result.get('result')

    def initialize(self):
        result = self.request('initialize', {
            'protocolVersion': self.version,
            'capabilities': {},
            'clientInfo': {'name': 'Physis Local MCP Client', 'version': '1.0'},
        })
        self.version = result['protocolVersion']
        self.request('notifications/initialized', notification=True)
        return result

    def call(self, name, arguments=None):
        return self.request('tools/call', {'name': name, 'arguments': arguments or {}})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--timeout', type=float, default=30)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('tools', help='List the MCP entry points and their schemas.')
    call = commands.add_parser('call', help='Call a discovered tool with JSON arguments.')
    call.add_argument('name')
    call.add_argument('arguments', nargs='?', default='{}')
    args = parser.parse_args()
    client = UnrealMCP(args.timeout)
    client.initialize()
    result = (client.request('tools/list') if args.command == 'tools'
              else client.call(args.name, json.loads(args.arguments)))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 1 if isinstance(result, dict) and result.get('isError') else 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except HTTPError as error:
        raise SystemExit('Unreal MCP HTTP error %s: %s' % (error.code, error.read().decode()))
    except (URLError, TimeoutError, RuntimeError) as error:
        raise SystemExit('Unreal MCP request failed: %s. Check the editor before retrying a write.' % error)
