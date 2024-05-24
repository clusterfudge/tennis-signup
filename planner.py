from pybars import Compiler

import tokens
from client import sign_in, build_class_map, build_next_week_schedule, make_session
from web import mark_bookings
import os
from cal import sync_plan_to_calendar
from storage import Storage
from tokens import generate_token, swap_prefix

storage = Storage('storage')

# sign in and build next week's schedule
s = make_session()
sign_in(s)
class_map = build_class_map(s)
schedule = build_next_week_schedule(s, class_map, ["LB01", "LB03", "LB05", "LB06", "LB13", "LB15", "LB16", "LB17", "LB19"])
schedule_id = generate_token('sched', entropy=10)
storage.put(schedule_id, schedule)

# create a plan based on previous week's plan
prev_plan_id, previous_plan = storage.latest("plan")
next_plan = None
if previous_plan is not None:
    plan_slugs = [s['slug'] for s in previous_plan.values()]
    booked = set([el['schedule_id'] for el in previous_plan.values()])
    next_plan = {
        si['slug']: si
        for si in schedule if si['slug'] in previous_plan
    }
    next_plan_id = swap_prefix(schedule_id, 'plan')
else:
    next_plan_id, next_plan = tokens.generate_token('plan'), {}

mark_bookings(next_plan)
sync_plan_to_calendar(storage, next_plan, os.environ.get('SHARED_CALENDAR_ID'))
storage.put(next_plan_id, next_plan)

compiler = Compiler()
source = open('invite_to_plan.html', 'r').read()
template = compiler.compile(source)
print(template({'schedule_id': schedule_id, 'plan': next_plan.values()}))
