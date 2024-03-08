import os.path
import sys
import logging

from bottle import run, get, post, abort, request
from pybars import Compiler
import json

compiler = Compiler()


def swap_prefix(token: str, new_prefix: str):
    suffix = token[token.rfind('_') + 1:]
    return new_prefix + '_' + suffix


def update_schedule_from_plan(schedule, plan):
    for class_ in schedule:
        if class_['slug'] in plan:
            class_['checked'] = 'checked'
        else:
            class_['checked'] = ''

@get('/schedule/<schedule_id>')
def serve_schedule(schedule_id):
    schedule_filename = f"{schedule_id}.json"
    if not os.path.exists(schedule_filename):
        return abort(404)

    plan_id = swap_prefix(schedule_id, "plan")
    plan_filename = f"{plan_id}.json"
    if os.path.exists(plan_filename):
        with open(plan_filename, 'r') as f:
            plan = json.load(f)
    else:
        plan = {}

    source = open('template.html', 'r').read()
    template = compiler.compile(source)

    with open(schedule_filename, 'r') as f:
        schedule = json.load(f)
        update_schedule_from_plan(schedule, plan)
        return template({'schedule': schedule, 'schedule_id': schedule_id})


@post('/plan/<schedule_id>')
def create_plan(schedule_id):
    schedule_filename = f"{schedule_id}.json"
    if not os.path.exists(schedule_filename):
        return abort(404)

    plan_id = swap_prefix(schedule_id, "plan")
    plan_filename = f"{plan_id}.json"
    with open(schedule_filename, 'r') as f:
        schedule = json.load(f)

    plan = {}

    for class_ in schedule:
        slug = class_['slug']
        checked = str(request.forms.get(slug, 'off')) == 'on'
        if checked:
            plan[slug] = class_

    with open(plan_filename, 'w') as f:
        json.dump(plan, f)

    source = open('template.html', 'r').read()
    template = compiler.compile(source)

    with open(schedule_filename, 'r') as f:
        schedule = json.load(f)
        update_schedule_from_plan(schedule, plan)
        return template({'schedule': schedule, 'schedule_id': schedule_id})


def main(args=sys.argv):
    port = int(args[1])
    run(host='0.0.0.0', port=port)


if __name__ == "__main__":
    main(sys.argv)