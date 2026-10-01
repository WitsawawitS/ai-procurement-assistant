"""Deterministic procurement decisions. Decimal money; no model-generated arithmetic."""
from __future__ import annotations

import csv
import io
import math
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_CEILING, ROUND_HALF_UP

VERSION = '1.0.0'
FIELDS = ['id', 'name', 'country', 'sku', 'currency', 'unit_price', 'moq', 'pack_size',
          'freight', 'insurance', 'other_cost', 'duty_pct', 'vat_pct', 'lead_days',
          'quality_pct', 'otif_pct', 'capacity', 'incoterm', 'valid_until']
NUMERIC = FIELDS[5:17]
INTEGER = {'moq', 'pack_size', 'lead_days', 'capacity'}
PERCENT = {'duty_pct', 'vat_pct', 'quality_pct', 'otif_pct'}
WEIGHTS = ('cost', 'lead', 'quality', 'reliability')


class ValidationError(ValueError):
    pass


def number(value, field, low=0, high=1_000_000_000, integer=False):
    if isinstance(value, bool):
        raise ValidationError(f'{field}: enter a number, not true/false.')
    try:
        n = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValidationError(f'{field}: enter a valid number.') from None
    if not n.is_finite() or n < low or n > high or (integer and n != n.to_integral_value()):
        raise ValidationError(f'{field}: must be {"an integer " if integer else ""}between {low} and {high}.')
    return n


def money(value):
    return float(Decimal(value).quantize(Decimal('.01'), rounding=ROUND_HALF_UP))


def text(value, field, limit=100):
    if not isinstance(value, str) or not value.strip() or len(value) > limit or any(ord(c) < 32 for c in value):
        raise ValidationError(f'{field}: enter text (1–{limit} characters, no control characters).')
    return value.strip()


def validate_quotes(rows):
    if not isinstance(rows, list) or not 1 <= len(rows) <= 50:
        raise ValidationError('Provide 1–50 supplier quotes.')
    result, seen = [], set()
    for i, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            raise ValidationError(f'Row {i}: expected a quote object.')
        missing = set(FIELDS) - set(row)
        if missing:
            raise ValidationError(f'Row {i}: missing {", ".join(sorted(missing))}.')
        q = {k: text(row[k], f'Row {i} / {k}') for k in FIELDS if k not in NUMERIC}
        if q['id'] in seen:
            raise ValidationError(f'Duplicate quote ID: {q["id"]}.')
        seen.add(q['id'])
        if q['currency'] not in {'THB', 'USD', 'EUR', 'JPY', 'CNY', 'GBP', 'SGD'}:
            raise ValidationError(f'Row {i}: unsupported currency {q["currency"]}.')
        if q['incoterm'] not in {'EXW', 'FCA', 'FOB', 'CFR', 'CIF', 'CPT', 'CIP', 'DAP', 'DPU', 'DDP', 'FAS'}:
            raise ValidationError(f'Row {i}: invalid Incoterm label.')
        try:
            parsed_date = date.fromisoformat(q['valid_until'])
            if parsed_date.isoformat() != q['valid_until']:
                raise ValueError('Use ISO date format')
        except ValueError:
            raise ValidationError(f'Row {i}: valid_until must be YYYY-MM-DD.') from None
        for k in NUMERIC:
            n = number(row[k], f'Row {i} / {k}', low=1 if k in INTEGER else Decimal('.000001') if k == 'unit_price' else 0,
                       high=100 if k in PERCENT else 1_000_000, integer=k in INTEGER)
            q[k] = int(n) if k in INTEGER else float(n)
        result.append(q)
    return result


def parse_csv(content):
    if not isinstance(content, str) or len(content.encode('utf-8')) > 500_000:
        raise ValidationError('CSV must be text below 500 KB.')
    try:
        reader = csv.DictReader(io.StringIO(content.lstrip('\ufeff')), strict=True)
        if reader.fieldnames != FIELDS:
            raise ValidationError('CSV headers or order do not match. Download the template and keep all columns.')
        rows = []
        for row in reader:
            if None in row or any(v is None for v in row.values()):
                raise ValidationError('CSV contains a row with the wrong number of columns.')
            rows.append(row)
            if len(rows) > 50:
                raise ValidationError('Maximum 50 quotes per upload.')
        return validate_quotes(rows)
    except csv.Error as e:
        raise ValidationError(f'Invalid CSV: {e}') from None


def validate_scenario(raw, quotes):
    if not isinstance(raw, dict):
        raise ValidationError('Scenario must be an object.')
    s = {}
    for k, low, high in [('quantity', 1, 1_000_000), ('deadline_days', 1, 3650), ('min_quality', 0, 100), ('min_otif', 0, 100)]:
        s[k] = float(number(raw.get(k), k, low, high, k in {'quantity', 'deadline_days'}))
    s['quantity'] = int(s['quantity'])
    s['deadline_days'] = int(s['deadline_days'])
    s['sku'] = text(raw.get('sku'), 'sku')
    if s['sku'] not in {q['sku'] for q in quotes}:
        raise ValidationError('Select a product present in the quote data.')
    if type(raw.get('vat_recoverable')) is not bool:
        raise ValidationError('vat_recoverable must be true or false.')
    s['vat_recoverable'] = raw['vat_recoverable']
    try:
        s['as_of'] = date.fromisoformat(raw.get('as_of', '')).isoformat()
    except (ValueError, TypeError):
        raise ValidationError('Set a valid evaluation date (YYYY-MM-DD).') from None
    weights = raw.get('weights')
    if not isinstance(weights, dict) or set(weights) != set(WEIGHTS):
        raise ValidationError('Provide cost, lead, quality and reliability weights.')
    s['weights'] = {k: float(number(weights[k], f'{k} weight', 0, 100)) for k in WEIGHTS}
    if sum(Decimal(str(v)) for v in s['weights'].values()) != 100:
        raise ValidationError('Score weights must total exactly 100%.')
    fx = raw.get('fx')
    if not isinstance(fx, dict):
        raise ValidationError('Provide exchange rates as THB per 1 currency unit.')
    currencies = {q['currency'] for q in quotes if q['sku'] == s['sku']} | {'THB'}
    s['fx'] = {k: float(number(fx.get(k), f'{k} exchange rate', Decimal('.000001'), 1_000_000)) for k in currencies}
    if s['fx']['THB'] != 1:
        raise ValidationError('THB exchange rate must be 1.')
    s['baseline_id'] = str(raw.get('baseline_id', ''))
    if s['baseline_id'] and s['baseline_id'] not in {q['id'] for q in quotes if q['sku'] == s['sku']}:
        raise ValidationError('Baseline must be a quote for the selected product.')
    return s


def _cost(q, s):
    d = lambda k: Decimal(str(q[k]))
    fx = Decimal(str(s['fx'][q['currency']]))
    ordered = int((Decimal(max(s['quantity'], q['moq'])) / d('pack_size')).to_integral_value(rounding=ROUND_CEILING)) * q['pack_size']
    goods = d('unit_price') * ordered * fx
    freight, insurance, other = [d(k) * fx for k in ('freight', 'insurance', 'other_cost')]
    customs = goods + freight + insurance
    duty = customs * d('duty_pct') / 100
    vat = (customs + duty) * d('vat_pct') / 100
    net = customs + duty + other
    total = net if s['vat_recoverable'] else net + vat
    reasons, flags = [], []
    if ordered > q['capacity']:
        reasons.append('Order exceeds supplier capacity')
    if q['lead_days'] > s['deadline_days']:
        reasons.append('Lead time exceeds deadline')
    if q['quality_pct'] < s['min_quality']:
        reasons.append('Quality below minimum')
    if q['otif_pct'] < s['min_otif']:
        reasons.append('OTIF below minimum')
    if q['valid_until'] < s['as_of']:
        reasons.append('Quote expired on evaluation date')
    if ordered > s['quantity']:
        flags.append(f'{ordered - s["quantity"]:,} excess units (MOQ / pack size)')
    if q['currency'] != 'THB':
        flags.append(f'{q["currency"]} exchange-rate exposure')
    if q['incoterm'] in {'CIF', 'CIP', 'CFR', 'DDP'}:
        flags.append('Confirm included charges to avoid double counting')
    return {**q, 'ordered_qty': ordered, 'excess_qty': ordered-s['quantity'],
            'goods_thb': money(goods), 'freight_thb': money(freight), 'insurance_thb': money(insurance),
            'other_thb': money(other), 'duty_thb': money(duty), 'vat_thb': money(vat),
            'cash_outlay': money(net+vat), 'landed_cost': money(total),
            'cost_per_required_unit': money(total/s['quantity']), 'cost_per_ordered_unit': money(total/ordered),
            'eligible': not reasons, 'reasons': reasons, 'flags': flags, '_total': total}


def analyze(quotes, scenario):
    quotes = validate_quotes(quotes)
    s = validate_scenario(scenario, quotes)
    rows = [_cost(q, s) for q in quotes if q['sku'] == s['sku']]
    eligible = [r for r in rows if r['eligible']]
    min_cost = min((r['_total'] for r in eligible), default=Decimal(0))
    min_lead = min((r['lead_days'] for r in eligible), default=1)
    for r in rows:
        r['score'] = None
        r['components'] = {}
        if r['eligible']:
            components = {'cost': min_cost/r['_total']*100,
                          'lead': Decimal(min_lead)/r['lead_days']*100,
                          'quality': Decimal(str(r['quality_pct'])), 'reliability': Decimal(str(r['otif_pct']))}
            r['components'] = {k: money(v) for k, v in components.items()}
            r['_score'] = sum(v*Decimal(str(s['weights'][k]))/100 for k, v in components.items())
            r['score'] = money(r['_score'])
    rows.sort(key=lambda r: (not r['eligible'], -r.get('_score', Decimal(-1)), r['_total'], r['id']))
    rank = 0
    for r in rows:
        if r['eligible']:
            rank += 1
        r['rank'] = rank if r['eligible'] else None
        r.pop('_score', None)
        r.pop('_total', None)
    winner = next((r for r in rows if r['eligible']), None)
    cheapest = min((r for r in rows if r['eligible']), key=lambda r: (r['landed_cost'], r['id']), default=None)
    baseline = next((r for r in rows if r['id'] == s['baseline_id']), None)
    delta = money(Decimal(str(baseline['landed_cost']))-Decimal(str(winner['landed_cost']))) if baseline and winner else None
    notes = ['All example suppliers, prices, FX rates and performance values are synthetic.',
             'THB is the base currency. FX means THB per 1 foreign currency unit; rates are manual, not live.',
             'Freight, insurance and other costs are incremental per-shipment amounts in the quote currency. Enter only buyer-paid amounts not already in unit price.',
             'Illustrative tax model: duty on goods + freight + insurance; VAT on that base + duty. Other costs are outside this simplified tax base.',
             'No preferential tariffs, excise, VAT timing, financing, inventory holding cost or defect cost is modeled.',
             'All quotes for a SKU must have equivalent technical specification, unit of measure and delivery scope. Incoterms are descriptive labels, not automatic cost rules.',
             'Lead time is assumed to cover all calendar days from order to delivery; capacity is available quantity for this order. Historical quality/OTIF are user inputs, not forecasts.']
    return {'engine_version': VERSION, 'scenario': s, 'results': rows, 'winner_id': winner['id'] if winner else None,
            'cheapest_id': cheapest['id'] if cheapest else None, 'eligible_count': len(eligible),
            'baseline_delta': delta, 'assumptions': notes}


def sensitivity(quotes, scenario):
    base = analyze(quotes, scenario)
    scenario = base['scenario']
    cases = []
    for label, change in [('Base case', {}), ('Demand −25%', {'quantity': max(1, math.floor(scenario['quantity']*.75))}),
                          ('Demand +25%', {'quantity': min(1_000_000, math.ceil(scenario['quantity']*1.25))}),
                          ('Foreign FX +10%', {'fx': {k: min(1_000_000, v*(1 if k == 'THB' else 1.1)) for k,v in scenario['fx'].items()}}),
                          ('Deadline −7 days', {'deadline_days': max(1, scenario['deadline_days']-7)}),
                          ('Cost-first weights', {'weights': {'cost': 75, 'lead': 10, 'quality': 10, 'reliability': 5}})]:
        r = base if not change else analyze(quotes, {**scenario, **change})
        winner = next((x for x in r['results'] if x['id'] == r['winner_id']), None)
        cases.append({'label': label, 'winner': winner['name'] if winner else None,
                      'landed_cost': winner['landed_cost'] if winner else None,
                      'quantity': r['scenario']['quantity'], 'eligible_count': r['eligible_count'],
                      'changed': r['winner_id'] != base['winner_id']})
    return cases


def decision_brief(result):
    winner = next((r for r in result['results'] if r['id'] == result['winner_id']), None)
    if not winner:
        return 'No supplier meets all constraints. Review the exclusion reasons, negotiate delivery or capacity, or revise your requirements. Do not issue a purchase order from this comparison.'
    s = result['scenario']
    lines = [f'Recommended for review: {winner["name"]} ({winner["id"]}).',
             f'Weighted score {winner["score"]:.2f}/100; {result["eligible_count"]} eligible quotes.',
             f'Landed cost THB {winner["landed_cost"]:,.2f}; cash outlay THB {winner["cash_outlay"]:,.2f}.',
             f'Order {winner["ordered_qty"]:,} units for demand of {s["quantity"]:,}; lead time {winner["lead_days"]} days against a {s["deadline_days"]}-day deadline.',
             f'Quality {winner["quality_pct"]:g}%; OTIF {winner["otif_pct"]:g}%.']
    if result['cheapest_id'] != winner['id']:
        cheap = next(r for r in result['results'] if r['id'] == result['cheapest_id'])
        lines.append(f'Trade-off: THB {winner["landed_cost"]-cheap["landed_cost"]:,.2f} above the cheapest eligible offer from {cheap["name"]}; the chosen weights favor its combined delivery and performance scores.')
    if result['baseline_delta'] is not None:
        delta = result['baseline_delta']
        lines.append(f'Compared with the selected baseline: THB {abs(delta):,.2f} {"lower" if delta >= 0 else "higher"} scenario cost. This is a modeled difference, not realized savings.')
    lines.extend(['Watch: '+f for f in winner['flags']])
    lines.append('Before approval: verify technical equivalence, quote validity, included charges, tax treatment and confirmed delivery with the supplier.')
    return '\n'.join(lines)
