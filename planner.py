from pybars import Compiler
from client import sign_in, build_class_map, build_next_week_schedule
from requests import Session

from storage import Storage
from tokens import generate_token, swap_prefix

storage = Storage('storage')

# sign in and build next week's schedule
s = Session()
sign_in(s)
class_map = build_class_map(s)
schedule = build_next_week_schedule(s, class_map, ["LB01", "LB03", "LB05", "LB06", "LB13", "LB15", "LB16", "LB17", "LB19"])
schedule_id = generate_token('sched', 10)
storage.put(schedule_id, schedule)

# create a plan based on previous week's plan
prev_plan_id, previous_plan = storage.latest("plan")
next_plan = None
if previous_plan:
    plan_slugs = [s['slug'] for s in previous_plan.values()]
    next_plan = {
        si['slug']: si
        for si in schedule if si['slug'] in previous_plan
    }
    next_plan_id = swap_prefix(schedule_id, 'plan')
    storage.put(next_plan_id, next_plan)

compiler = Compiler()
source = open('invite_to_plan.html', 'r').read()
template = compiler.compile(source)
print(template({'schedule_id': schedule_id, 'plan': next_plan.values()}))
