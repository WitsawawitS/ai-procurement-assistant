#!/usr/bin/env python3
"""Run locally with Python 3.10+: python app.py. No third-party dependencies."""
from __future__ import annotations
import argparse
import json
import mimetypes
import os
import secrets
import threading
import webbrowser
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from procurement.engine import ValidationError, analyze, parse_csv, sensitivity, text, decision_brief
from procurement.reports import csv_report, html_report
from procurement.storage import Store
from procurement import ai

ROOT = Path(__file__).resolve().parent
MAX_BODY = 750_000


def sample():
    quotes = parse_csv((ROOT/'data/sample_quotes.csv').read_text(encoding='utf-8'))
    return {'quotes': quotes, 'scenario': {'sku':'BRG-6205', 'quantity':1000,'deadline_days':21,
        'min_quality':95,'min_otif':90,'vat_recoverable':True,'as_of':date.today().isoformat(),
        'baseline_id':'Q001','weights':{'cost':45,'lead':20,'quality':20,'reliability':15},
        'fx':{'THB':1,'USD':35,'EUR':38,'JPY':.24,'CNY':4.9,'GBP':45,'SGD':26}}}


def make_server(port=8765, db_path=None):
    token = secrets.token_urlsafe(32)
    store = Store(db_path or os.getenv('PROCUREMENT_DB', str(ROOT/'runtime/analyses.sqlite3')))

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            # Avoid logging payloads, quote data or keys.
            pass

        def reply(self, code, data, content_type='application/json; charset=utf-8', filename=None):
            if isinstance(data, (dict,list)):
                data = json.dumps(data, ensure_ascii=False, allow_nan=False).encode('utf-8')
            elif isinstance(data, str):
                data = data.encode('utf-8')
            self.send_response(code)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('X-Frame-Options','DENY')
            self.send_header('Referrer-Policy','no-referrer')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            if filename:
                self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
            self.end_headers()
            self.wfile.write(data)

        def allowed_host(self):
            actual = self.server.server_address[1]
            return self.headers.get('Host') in {f'127.0.0.1:{actual}',f'localhost:{actual}'}

        def do_GET(self):
            if not self.allowed_host():
                return self.reply(403, {'error':'Local host required.'})
            path = urlsplit(self.path).path
            if path == '/api/bootstrap':
                return self.reply(200, {**sample(), 'token':token, 'ai_available':ai.configured()})
            if path == '/api/history':
                return self.reply(200, store.list())
            if path.startswith('/api/history/'):
                try:
                    ident = int(path.rsplit('/',1)[1])
                    item = store.get(ident)
                except ValueError:
                    return self.reply(400, {'error':'Invalid or corrupt snapshot.'})
                return self.reply(200 if item else 404, item or {'error':'Snapshot not found.'})
            files = {'/':'index.html','/app.js':'app.js','/style.css':'style.css','/favicon.svg':'favicon.svg'}
            if path == '/api/template':
                return self.reply(200, (ROOT/'data/sample_quotes.csv').read_bytes(), 'text/csv; charset=utf-8', 'supplier-quotes-template.csv')
            if path not in files:
                return self.reply(404, {'error':'Not found.'})
            file = ROOT/'web'/files[path]
            return self.reply(200, file.read_bytes(), (mimetypes.guess_type(str(file))[0] or 'text/plain')+'; charset=utf-8')

        def do_POST(self):
            actual = self.server.server_address[1]
            origin = self.headers.get('Origin')
            if not self.allowed_host() or origin not in {None, f'http://127.0.0.1:{actual}', f'http://localhost:{actual}'} or self.headers.get('X-CSRF-Token') != token:
                return self.reply(403, {'error':'Session expired or cross-origin request blocked. Reload the app.'})
            if self.headers.get('Content-Type','').split(';')[0] != 'application/json':
                return self.reply(415, {'error':'JSON required.'})
            try:
                length = int(self.headers.get('Content-Length','0'))
                if not 0 < length <= MAX_BODY:
                    return self.reply(413, {'error':'Request is empty or exceeds 750 KB.'})
                self.connection.settimeout(10)
                data = json.loads(self.rfile.read(length), parse_constant=lambda x: (_ for _ in ()).throw(ValueError('Non-finite JSON number')))
                if not isinstance(data, dict):
                    raise ValidationError('Expected a JSON object.')
                path = urlsplit(self.path).path
                if path == '/api/import':
                    return self.reply(200, {'quotes':parse_csv(data.get('csv'))})
                if path not in {'/api/analyze','/api/sensitivity','/api/save','/api/export','/api/explain'}:
                    return self.reply(404, {'error':'Not found.'})
                result = analyze(data.get('quotes'), data.get('scenario'))
                if path == '/api/analyze':
                    return self.reply(200, {**result,'brief':decision_brief(result)})
                if path == '/api/sensitivity':
                    return self.reply(200, sensitivity(data['quotes'], result['scenario']))
                if path == '/api/save':
                    title = text(data.get('title'), 'Snapshot name', 80)
                    return self.reply(201, store.save(title, {'quotes':data['quotes'],'scenario':result['scenario'],'analysis':result}))
                if path == '/api/explain':
                    return self.reply(200, ai.explain(result, data.get('question',''), data.get('consent',False)))
                kind = data.get('format')
                if kind == 'csv':
                    return self.reply(200, csv_report(result), 'text/csv; charset=utf-8', 'supplier-comparison.csv')
                if kind == 'html':
                    return self.reply(200, html_report(result), 'text/html; charset=utf-8', 'procurement-report.html')
                if kind == 'json':
                    return self.reply(200, result, filename='procurement-analysis.json')
                raise ValidationError('Unknown export format.')
            except (ValidationError, ValueError, TypeError, KeyError) as e:
                return self.reply(400, {'error':str(e) or 'Invalid request.'})
            except TimeoutError:
                return self.reply(408, {'error':'Request timed out.'})
            except Exception:
                return self.reply(500, {'error':'Unable to complete the request. Check local storage permissions and retry.'})

    return ThreadingHTTPServer(('127.0.0.1',port), Handler)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--open', action='store_true', help='Open the dashboard in your default browser')
    args = parser.parse_args()
    server = make_server(args.port)
    url = f'http://127.0.0.1:{server.server_address[1]}'
    print(f'AI Procurement Assistant: {url}\nLocal only. Ctrl+C to stop.', flush=True)
    if args.open:
        threading.Timer(.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nStopped.')
    finally:
        server.server_close()
