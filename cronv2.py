import sys
from datetime import datetime, timedelta

from client import Client, ClientSettings
from storage import Storage
import logging
logging.basicConfig(level=logging.ERROR)

storage = Storage('storage')

plan_id, plan = storage.latest('plan')
if not plan:
    sys.exit()

now = datetime.now()
schedule_window = timedelta(days=2, minutes=1)
settings = ClientSettings.load()

for slug, clazz in plan.items():
    if clazz.get('scheduled') or clazz.get('failed'):
        continue

    class_start = datetime.fromtimestamp(clazz['timestamp'])
    if class_start < now:
        continue
    if (class_start - now) <= schedule_window:
        client = Client(settings)
        result = client.register_for_instance(clazz)
        if result.get('status') == 1 or 'already registered' in result.get('message'):
            clazz['scheduled'] = True
        else:
            logging.error(f"Failed to sign up for {clazz['slug']}: {result.get('message')}")
            if 'maximum' in result.get('message'):
                clazz['failed'] = True


storage.put(plan_id, plan)


