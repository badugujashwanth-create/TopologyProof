CASES=[]
def _case(i,title,risk,source): return {"case_id":f"CASE-{i:02d}","title":title,"description":title,"expected":risk,"correctness_property":"one event at most one durable record","why": "process-local correctness guard" if risk else "no process-local correctness dependency","source":source}
RISK='''from app.payments import record_payment\nseen_events = set()\ndef receive(event_id):\n    if event_id in seen_events: return\n    record_payment(event_id)\n    seen_events.add(event_id)\n'''
SAFE='''cache = {}\ndef read(key):\n    if key in cache: return cache[key]\n    value = compute(key); cache[key] = value; return value\n'''
for i in range(1,7): CASES.append(_case(i,f"Risk pattern {i}","RISK",RISK))
CASES += [_case(7,"Performance-only cache","SAFE",SAFE),_case(8,"Request-local state","SAFE",'''def receive(event_id):\n    seen = set()\n    seen.add(event_id)\n    return seen\n'''),_case(9,"Durable idempotency","SAFE",'''def receive(event_id):\n    return insert_event_if_absent(event_id)\n'''),_case(10,"Indirect renamed guard","RISK",'''completed_keys = set()\ndef receive(key):\n    if key in completed_keys: return\n    write_ledger_entry(key)\n    completed_keys.add(key)\n''')]
def all_cases(): return tuple(CASES)
