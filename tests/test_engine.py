import copy
import unittest
from decimal import Decimal
from app import sample
from procurement.engine import analyze, parse_csv, sensitivity, ValidationError, money, decision_brief
from procurement.reports import csv_report, html_report

class EngineTests(unittest.TestCase):
    def setUp(self):
        self.data=sample(); self.q=self.data['quotes']; self.s=self.data['scenario'];self.s['as_of']='2026-10-01'

    def test_known_local_cost(self):
        r=analyze(self.q,self.s);q=next(q for q in r['results'] if q['id']=='Q001')
        self.assertEqual(q['goods_thb'],164000)
        self.assertEqual(q['landed_cost'],166150)
        self.assertEqual(q['vat_thb'],11606)
        self.assertEqual(q['cash_outlay'],177756)

    def test_known_import_cost_and_taxes(self):
        q=next(q for q in analyze(self.q,self.s)['results'] if q['id']=='Q002')
        # Independent worksheet: goods 131250 + freight 7350 + insurance 700.
        # Duty = 139300 * .05 = 6965; VAT = 146265 * .07 = 10238.55.
        self.assertEqual(q['duty_thb'],6965)
        self.assertEqual(q['vat_thb'],10238.55)
        self.assertEqual(q['landed_cost'],147665)
        self.assertEqual(q['cash_outlay'],157903.55)

    def test_nonrecoverable_vat(self):
        a=analyze(self.q,self.s);b=analyze(self.q,{**self.s,'vat_recoverable':False})
        for x in a['results']:
            y=next(y for y in b['results'] if y['id']==x['id'])
            self.assertEqual(y['landed_cost'],x['cash_outlay'])

    def test_moq_and_pack_roundup(self):
        self.q[0].update(moq=1100,pack_size=300)
        q=next(q for q in analyze(self.q,self.s)['results'] if q['id']=='Q001')
        self.assertEqual(q['ordered_qty'],1200);self.assertEqual(q['excess_qty'],200)
        self.assertEqual(q['goods_thb'],196800)

    def test_capacity_after_pack_rounding(self):
        self.q[0].update(pack_size=600,capacity=1000)
        q=next(q for q in analyze(self.q,self.s)['results'] if q['id']=='Q001')
        self.assertFalse(q['eligible']);self.assertIn('Order exceeds supplier capacity',q['reasons'])

    def test_no_award_even_for_cheapest(self):
        r=analyze(self.q,{**self.s,'deadline_days':1})
        self.assertIsNone(r['winner_id']);self.assertEqual(r['eligible_count'],0)
        self.assertTrue(all(q['score'] is None for q in r['results']))
        self.assertIn('No supplier',decision_brief(r))

    def test_expiry_date_boundary(self):
        self.q[0]['valid_until']=self.s['as_of']
        self.assertTrue(next(q for q in analyze(self.q,self.s)['results'] if q['id']=='Q001')['eligible'])
        self.q[0]['valid_until']='2026-09-30'
        self.assertFalse(next(q for q in analyze(self.q,self.s)['results'] if q['id']=='Q001')['eligible'])

    def test_multiple_skus_not_mixed(self):
        r=analyze(self.q,{**self.s,'sku':'FLT-H100','baseline_id':'Q007'})
        self.assertEqual(len(r['results']),4)
        self.assertTrue(all(q['sku']=='FLT-H100' for q in r['results']))

    def test_score_worksheet(self):
        r=analyze(self.q,self.s);q=next(q for q in r['results'] if q['id']=='Q001')
        eligible=[x for x in r['results'] if x['eligible']]
        expected=Decimal(str(min(x['landed_cost'] for x in eligible)))/Decimal('166150')*45+Decimal('20')+Decimal('99.2')*Decimal('.20')+Decimal('98')*Decimal('.15')
        self.assertEqual(q['score'],money(expected))

    def test_cost_only_winner(self):
        s={**self.s,'weights':{'cost':100,'lead':0,'quality':0,'reliability':0}}
        r=analyze(self.q,s);self.assertEqual(r['winner_id'],r['cheapest_id'])

    def test_deterministic_tie_break(self):
        q=copy.deepcopy(self.q[0]);q['id']='AAA';q['name']='Tie supplier'
        r=analyze([self.q[0],q],self.s)
        self.assertEqual(r['winner_id'],'AAA')

    def test_baseline_delta_sign(self):
        r=analyze(self.q,{**self.s,'baseline_id':'Q002'})
        winner=next(x for x in r['results'] if x['id']==r['winner_id'])
        self.assertAlmostEqual(r['baseline_delta'],147665-winner['landed_cost'],places=2)

    def test_sensitivity_does_not_mutate(self):
        before=copy.deepcopy(self.data);cases=sensitivity(self.q,self.s)
        self.assertEqual(len(cases),6);self.assertEqual(before,self.data)

    def test_invalid_numbers_and_weights(self):
        for value in [float('nan'),float('inf'),-1,0,True,1.5]:
            with self.subTest(value=value),self.assertRaises(ValidationError):
                analyze(self.q,{**self.s,'quantity':value})
        with self.assertRaises(ValidationError):
            analyze(self.q,{**self.s,'weights':{'cost':40,'lead':20,'quality':20,'reliability':15}})
        with self.assertRaises(ValidationError):
            analyze(self.q,{**self.s,'fx':{'THB':1}})

    def test_csv_validation(self):
        from pathlib import Path
        data=Path('data/sample_quotes.csv').read_text()
        self.assertEqual(len(parse_csv('\ufeff'+data)),10)
        for bad in ['a,b\n1,2',data.replace('Q002','Q001'),data.replace(',164,',',NaN,'),data.replace(',THB,',',XYZ,')]:
            with self.subTest(bad=bad[:30]),self.assertRaises(ValidationError):parse_csv(bad)

    def test_exports_escape_untrusted_text(self):
        self.q[0]['name']='=HYPERLINK("evil")<script>alert(1)</script>'
        r=analyze(self.q,self.s)
        csv=csv_report(r);html=html_report(r)
        self.assertIn("'=HYPERLINK",csv)
        self.assertNotIn('<script>',html);self.assertIn('&lt;script&gt;',html)


class EdgeCaseTests(unittest.TestCase):
    def test_fractional_unit_price(self):
        d=sample();d['quotes'][0]['unit_price']=.25
        q=next(q for q in analyze(d['quotes'],d['scenario'])['results'] if q['id']=='Q001')
        self.assertEqual(q['goods_thb'],250)

    def test_noncanonical_quote_date_is_rejected(self):
        d=sample();d['quotes'][0]['valid_until']='20301231'
        with self.assertRaises(ValidationError):analyze(d['quotes'],d['scenario'])

    def test_sensitivity_normalizes_numeric_strings(self):
        d=sample();d['scenario']['quantity']='1000';d['scenario']['deadline_days']='21'
        self.assertEqual(len(sensitivity(d['quotes'],d['scenario'])),6)

if __name__=='__main__':unittest.main()
