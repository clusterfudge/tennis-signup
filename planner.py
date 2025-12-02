import argparse
from pybars import Compiler

import tokens
from client import sign_in, build_class_map, build_next_week_schedule, make_session
from web import mark_bookings
import os
from cal import sync_plan_to_calendar
from storage import Storage
from tokens import generate_token, swap_prefix

storage = Storage('storage')


def main(send_email=True, print_schedule=False):
    # sign in and build next week's schedule
    s = make_session()
    sign_in(s)
    class_map = build_class_map(s)
    schedule = build_next_week_schedule(s, class_map, list(filter(lambda key: key.startswith("LB") or key.startswith("LF"), class_map.keys())))
    schedule_id = generate_token('sched', entropy=10)
    storage.put(schedule_id, schedule)

    if print_schedule:
        print(f"Schedule ID: {schedule_id}")
        print(f"Total classes in schedule: {len(schedule)}")
        print("\nSchedule:")
        for cls in schedule:
            print(f"  {cls['slug']}: {cls.get('seasonal_slug', '')} | {cls.get('schedule', '')}")

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

    if print_schedule:
        print(f"\nPlan ID: {next_plan_id}")
        print(f"Total classes in plan: {len(next_plan)}")
        if next_plan:
            print("\nPlan:")
            for slug, cls in next_plan.items():
                print(f"  {slug}: {cls.get('seasonal_slug', '')} | {cls.get('schedule', '')}")

    compiler = Compiler()
    source = open('invite_to_plan.html', 'r').read()
    template = compiler.compile(source)

    # Calculate weekly cost: $41.38 per class
    CLASS_COST = 41.38
    num_classes = len(next_plan)
    weekly_total = f"{num_classes * CLASS_COST:.2f}"

    plan_html = template({
        'schedule_id': schedule_id,
        'plan': next_plan.values(),
        'weekly_total': weekly_total
    })

    if send_email:
        from mail_client import send_plan_email
        send_plan_email(schedule_id, plan_html)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate tennis class schedule and plan')
    parser.add_argument('--no-email', action='store_true', help='Disable sending email')
    parser.add_argument('--print-schedule', action='store_true', help='Print schedule and plan to stdout')
    args = parser.parse_args()
    
    main(send_email=not args.no_email, print_schedule=args.print_schedule)
