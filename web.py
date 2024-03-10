import os.path
import sys
import logging

from bottle import run, get, post, abort, request, redirect
from pybars import Compiler
import json

from storage import Storage
from tokens import swap_prefix

compiler = Compiler()
storage = Storage('storage')

def update_table_contents(schedule):
    for row in schedule:
        parts = [p.strip() for p in row['description'].split("|")]
        row['class_desc'] = parts[1]
        row['class_date'] = parts[2]


def update_schedule_from_plan(schedule, plan):
    for class_ in schedule:
        slug = class_['slug']
        if slug in plan:
            class_['checked'] = 'checked'
            if plan[slug].get('scheduled'):
                class_['description'] += ' ✅'
        else:
            class_['checked'] = ''


@get('/schedule')
@get('/schedule/<schedule_id>')
def serve_schedule(schedule_id=None):
    if not schedule_id:
        schedule_id, schedule = storage.latest('sched')
    else:
        schedule = storage.get(schedule_id)
    if not schedule:
        return abort(404)

    plan_id = swap_prefix(schedule_id, "plan")
    plan = storage.get(plan_id) or {}

    return render_response(plan, schedule, schedule_id)


@post('/plan/<schedule_id>')
def create_plan(schedule_id):

    schedule = storage.get(schedule_id)
    if not schedule:
        return abort(404)

    plan_id = swap_prefix(schedule_id, "plan")
    plan = {}

    for class_ in schedule:
        slug = class_['slug']
        checked = str(request.forms.get(slug, 'off')) == 'on'
        if checked:
            plan[slug] = class_

    storage.put(plan_id, plan)

    return redirect(f"{request.urlparts[0]}://{request.get_header('host')}/schedule/{schedule_id}")


def render_response(plan, schedule, schedule_id):
    source = open('template.html', 'r').read()
    template = compiler.compile(source)
    update_schedule_from_plan(schedule, plan)
    update_table_contents(schedule)
    return template({'schedule': schedule, 'schedule_id': schedule_id})


def main(args=sys.argv):
    port = int(args[1])
    run(host='0.0.0.0', port=port)


if __name__ == "__main__":
    main(sys.argv)