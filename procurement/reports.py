"""Escaped portable exports; formula-safe CSV."""
import csv
import html
import io
import json
from .engine import decision_brief


def safe_cell(value):
    value = str(value)
    return "'"+value if value.lstrip().startswith(('=', '+', '-', '@', '\t', '\r')) else value


def csv_report(result):
    out = io.StringIO(newline='')
    fields = ['rank','id','name','sku','eligible','ordered_qty','excess_qty','landed_cost','cash_outlay',
              'cost_per_required_unit','lead_days','quality_pct','otif_pct','score','reasons']
    writer = csv.writer(out)
    writer.writerow(fields)
    for r in result['results']:
        writer.writerow([safe_cell('; '.join(r[k]) if isinstance(r[k], list) else '' if r[k] is None else r[k]) for k in fields])
    return '\ufeff'+out.getvalue()


def html_report(result):
    esc = lambda x: html.escape(str(x))
    rows = ''.join('<tr>'+''.join('<td>'+esc(v)+'</td>' for v in [r['name'],r['rank'] or 'Excluded',f"{r['landed_cost']:,.2f}",
                f"{r['cash_outlay']:,.2f}",r['ordered_qty'],r['lead_days'],r['score'] if r['eligible'] else '; '.join(r['reasons'])])+'</tr>' for r in result['results'])
    assumptions = ''.join('<li>'+esc(a)+'</li>' for a in result['assumptions'])
    return f'''<!doctype html><html lang="en"><meta charset="utf-8"><title>Procurement decision report</title>
<style>body{{font:15px/1.6 system-ui,sans-serif;color:#152a36;max-width:1100px;margin:40px auto;padding:20px}}h1{{font-size:32px}}table{{width:100%;border-collapse:collapse;font-size:13px}}td,th{{border-bottom:1px solid #ccd7dd;text-align:left;padding:10px}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:#f2f6f8;padding:20px;font:inherit}}small{{color:#536977}}@media print{{body{{margin:0;padding:0}}tr{{break-inside:avoid}}}}</style>
<small>AI PROCUREMENT ASSISTANT · DECISION SUPPORT · ENGINE {esc(result['engine_version'])}</small>
<h1>Supplier comparison & cost analysis</h1><p>Evaluation date: {esc(result['scenario']['as_of'])} · SKU: {esc(result['scenario']['sku'])}</p>
<h2>Deterministic decision brief</h2><pre>{esc(decision_brief(result))}</pre>
<table><thead><tr><th>Supplier</th><th>Rank</th><th>Landed THB</th><th>Cash THB</th><th>Order qty</th><th>Days</th><th>Score / exclusion</th></tr></thead><tbody>{rows}</tbody></table>
<h2>Scenario and exchange rates</h2><pre>{esc(json.dumps(result['scenario'],indent=2))}</pre>
<h2>Assumptions & limitations</h2><ul>{assumptions}</ul><p>Human approval required. No purchase order has been placed.</p></html>'''
