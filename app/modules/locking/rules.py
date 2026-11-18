def decide(state):
    c=state['counts'];explained=len(state['records'])+len(state['quarantine'])+c['blank']+c['duplicate']+c['repeated_header'];blocked=len(state['deviations'])+len(state['retest_issues'])+len(state['quarantine'])
    return {'input':c['input'],'accepted':len(state['records']),'quarantined':len(state['quarantine']),'row_balanced':c['input']==explained,'completed':len(state['completed']),'expected':len(state['context']['subjects'])*len(state['context']['required_visits']),'deviations':len(state['deviations']),'retest_issues':len(state['retest_issues']),'unit_pending':sum(1 for q in state['quarantine'] if q.get('code')=='UNIT_UNCONFIRMED'),'blocked':blocked,'status':'可锁库' if not blocked and c['input']==explained else '待处理'}
def site_conclusions(state):
    sites=state['context'].get('sites',{});pending=state['pending_visits'];rows=[]
    for site in sorted(set(sites.values())):
        members={s for s in state['context']['subjects'] if sites.get(s)==site}
        blocked=sum(1 for d in state['deviations'] if d.get('subject') in members)+sum(1 for p in pending if p['subject'] in members)
        rows.append({'site':site,'expected':len(members)*len(state['context']['required_visits']),'confirmed':sum(1 for c in state['completed'] if c['subject'] in members),'pending':sum(1 for p in pending if p['subject'] in members),'status':'继续阻断' if blocked else '可出结论'})
    return rows
def apply(state):
    state['balance']=decide(state)
    sites=state['context'].get('sites',{})
    state['pending_visits']=[{'subject':q['raw'].get('subject',''),'visit':q['raw'].get('visit',''),'id':q['id'],'site':sites.get(q['raw'].get('subject',''),'未登记'),'code':q['code'],'detail':q['detail']} for q in state['quarantine'] if q.get('code')=='UNIT_UNCONFIRMED']
    state['site_rows']=site_conclusions(state)
    state['views']['locking']={'title':'锁库闸门','rows':[state['balance']],'site_rows':state['site_rows'],'official':state['selected_results'],'pending':state['pending_visits'],'metrics':{'应访视':state['balance']['expected'],'已完成':state['balance']['completed'],'阻断项':state['balance']['blocked'],'待补证据':len(state['pending_visits'])}}
