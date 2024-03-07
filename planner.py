from pybars import Compiler
from client import sign_in, build_class_map, build_next_week_schedule
from requests import Session
import random
import base62
import json

s = Session()
sign_in(s)
class_map = build_class_map(s)
schedule = build_next_week_schedule(s, class_map, ["LB01", "LB03", "LB05", "LB06", "LB13", "LB15", "LB16", "LB17", "LB19"])

token = "sched_0" + base62.encodebytes(random.randbytes(32))
with open(f"{token}.json", 'w') as f:
    json.dump(schedule, f)


compiler = Compiler()
source = open('invite_to_plan.html', 'r').read()
template = compiler.compile(source)
print(template({'schedule_id': token}))