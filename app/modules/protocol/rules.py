from app.coerce import instant,number
from app.errors import BusinessError
from app.reasons import reject

def choose_protocol(subject,at,context):
    assignments=context['assignments'].get(subject,[])
    matches=[a for a in assignments if instant(a['start'])<=at<instant(a['end'])]
    if len(matches)!=1:raise BusinessError('PROTOCOL_CONFLICT','受试者方案未定或生效窗重叠')
    chosen=matches[0]['version']
    if chosen not in context['plans']:raise BusinessError('UNKNOWN_PROTOCOL','方案不存在')
    return chosen

def confirm_unit(row,context):
    declared=str(row.get('unit','')).strip()
    if declared:
        factor=context['units'].get(declared)
        if factor is None:raise BusinessError('BAD_UNIT','检验单位无法换算')
        return declared,factor,'RECORD_DECLARED',''
    site=context.get('sites',{}).get(row['subject'],'')
    receipt=context.get('receipts',{}).get(site)
    if not receipt:raise BusinessError('UNIT_UNCONFIRMED',f"中心{site or '未登记'}回执未到，单位待确认")
    factor=context['units'].get(receipt.get('unit',''))
    if factor is None:raise BusinessError('BAD_UNIT','回执单位无法换算')
    return receipt['unit'],factor,'RECEIPT_CONFIRMED',receipt.get('id','')

def normalize(row,context):
    at,enrolled=instant(row['at']),instant(row['enrolled']);revision=number(row['revision'])
    if row['subject'] not in context['subjects']:raise BusinessError('UNKNOWN_SUBJECT','受试者未入组')
    if enrolled!=instant(context['subjects'][row['subject']]):raise BusinessError('ENROLLMENT_CONFLICT','入组基准不一致')
    if at<enrolled or revision<1 or revision%1:raise BusinessError('INVALID_RANGE','访视日期或版本越界')
    if row['kind'] not in {'PRIMARY','RETEST'}:raise BusinessError('BAD_KIND','记录类型无效')
    chosen=choose_protocol(row['subject'],at,context)
    if row['protocol'] not in {'auto',chosen}:raise BusinessError('PROTOCOL_MISMATCH','记录方案与受试者有效版不符')
    if row['visit'] not in context['plans'][chosen]:raise BusinessError('UNKNOWN_VISIT','访视编号不存在')
    value=number(row['value'])
    unit,factor,basis,evidence=confirm_unit(row,context)
    if value<0:raise BusinessError('INVALID_RANGE','检验值小于零')
    return {**row,'at':at.isoformat(),'enrolled':enrolled.isoformat(),'revision':int(revision),'selected_protocol':chosen,'unit_confirmed':unit,'unit_basis':basis,'unit_evidence':evidence,'value_mg_dl':str(value*number(factor))}

def apply(state):
    good=[]
    for row in state['records']:
        try:good.append(normalize(row,state['context']))
        except BusinessError as e:reject(state,row,e.code,e.message)
    state['records']=good;state['views']['protocol']={'title':'受试者方案','rows':[{'id':r['id'],'subject':r['subject'],'visit':r['visit'],'selected_protocol':r['selected_protocol'],'unit_confirmed':r['unit_confirmed'],'unit_basis':r['unit_basis'],'at':r['at']} for r in good],'metrics':{'有效记录':len(good),'方案版本':len(state['context']['plans'])}}
