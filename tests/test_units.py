from app.engine import evaluate
from app.modules.protocol.rules import normalize
from app.modules.archive.rules import freeze
from app.errors import BusinessError
from copy import deepcopy
import pytest

@pytest.fixture
def units():
    return evaluate({'dataset':'units'})

def test_receipt_confirms_unitless(units):
    row=next(r for r in units['records'] if r['id']=='00002-V1')
    assert row['unit']=='' and row['unit_confirmed']=='g/L'
    assert row['unit_basis']=='RECEIPT_CONFIRMED' and row['unit_evidence']=='RCPT-2026-1115-S01'
    assert row['value']=='1.2' and row['value_mg_dl']=='120.0'

def test_declared_unit_self_confirms(units):
    row=next(r for r in units['records'] if r['id']=='00007-V1')
    assert row['unit_basis']=='RECORD_DECLARED' and row['unit_confirmed']=='g/L' and row['unit_evidence']==''

def test_unconfirmed_visit_stays_blocked(units):
    q=next(r for r in units['quarantine'] if r['id']=='00016-V1')
    assert q['code']=='UNIT_UNCONFIRMED' and q['raw']['value']=='1.2' and q['raw']['unit']==''
    assert any(d['subject']=='00016' and d['visit']=='V1' and d['code']=='MISSING_PRIMARY' for d in units['deviations'])
    assert units['balance']['status']=='待处理' and units['balance']['unit_pending']==6

def test_low_value_not_inflated(units):
    # TRAP-31：回执为 mg/dL 的中心，低值 0.9 保持 0.9，不按数值大小放大
    row=next(r for r in units['records'] if r['id']=='00009-V1')
    assert row['value_mg_dl']=='0.9' and row['unit_basis']=='RECEIPT_CONFIRMED'

def test_no_magnitude_guessing(units):
    # TRAP-31：单位只随证据走，数值大小不改变裁决
    context=deepcopy(units['context'])
    base={'id':'T','subject':'00002','visit':'V1','at':'2026-10-08T08:00:00+08:00','enrolled':'2026-10-01T00:00:00+08:00','kind':'PRIMARY','parent':'','protocol':'auto','revision':'1','unit':''}
    assert normalize(dict(base,value='118'),context)['value_mg_dl']=='11800'
    context['receipts']['S01']={'unit':'mg/dL','id':'RCPT-X','at':'2026-11-17T00:00:00+08:00'}
    assert normalize(dict(base,value='1.2'),context)['value_mg_dl']=='1.2'

def test_unconfirmed_without_receipt(units):
    context=deepcopy(units['context'])
    row={'id':'T','subject':'00015','visit':'V1','at':'2026-10-08T08:00:00+08:00','enrolled':'2026-10-01T00:00:00+08:00','kind':'PRIMARY','parent':'','protocol':'auto','revision':'1','unit':'','value':'1.2'}
    with pytest.raises(BusinessError) as e:normalize(row,context)
    assert e.value.code=='UNIT_UNCONFIRMED'

def test_retest_and_freeze_share_official_result(units):
    row=next(r for r in units['selected_results'] if r['primary_id']=='00001-V1')
    assert row['id']=='00001-R1' and row['value']=='118' and row['unit']=='mg/dL' and row['unit_basis']=='RECORD_DECLARED'
    shared=next(r for r in units['selected_results'] if r['id']=='00002-V1')
    assert shared['value']=='1.2' and shared['unit']=='' and shared['unit_confirmed']=='g/L'
    assert shared['unit_basis']=='RECEIPT_CONFIRMED' and shared['value_mg_dl']=='120.0'
    assert units['archive']['results']==len(units['selected_results'])

def test_rerun_keeps_official_results():
    a=evaluate({'dataset':'units'});b=evaluate({'dataset':'units'})
    assert a['manifest']['run_id']==b['manifest']['run_id']
    assert a['selected_results']==b['selected_results'] and a['archive']['seal']==b['archive']['seal']

def test_site_conclusions(units):
    rows={r['site']:r for r in units['site_rows']}
    assert rows['S01']['status']=='可出结论' and rows['S01']['confirmed']==14
    assert rows['S02']['status']=='可出结论' and rows['S02']['confirmed']==14
    assert rows['S03']['status']=='继续阻断' and rows['S03']['pending']==6
    assert len(units['pending_visits'])==6 and {p['site'] for p in units['pending_visits']}=={'S03'}

def test_seal_covers_unit_basis(units):
    s=deepcopy(units);s['selected_results'][0]['unit_basis']='GUESSED'
    assert freeze(s)['seal']!=units['archive']['seal']
