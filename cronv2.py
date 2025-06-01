import os
import sys
from datetime import datetime, timedelta

import cal
from client import Client, ClientSettings
from storage import Storage
import mail_client
import logging
logging.basicConfig(
    format='[%(asctime)s][%(levelname)-0s] %(message)s',
    level=logging.ERROR,
    datefmt='%Y-%m-%d %H:%M:%S')
storage = Storage('storage')

plan_id, plan = storage.latest('plan')
if not plan:
    sys.exit()

now = datetime.now()
schedule_window = timedelta(days=2, minutes=2)
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
            cal.create_event_for_class(storage, clazz, os.environ.get('SHARED_CALENDAR_ID'))
        else:
            error_message = f"Failed to sign up for {clazz['slug']}: {result.get('message')}"
            logging.error(error_message)
            
            # Create detailed HTML email body
            class_time = datetime.fromtimestamp(clazz['timestamp']).strftime('%Y-%m-%d %I:%M %p')
            email_body = f"""
            <h2>Tennis Class Booking Error</h2>
            <p>An error occurred while trying to book the following tennis class:</p>
            <h3>Class Details:</h3>
            <ul>
                <li><strong>Date/Time:</strong> {class_time}</li>
                <li><strong>Class Name:</strong> {clazz.get('name', 'N/A')}</li>
                <li><strong>Instructor:</strong> {clazz.get('instructor', 'N/A')}</li>
                <li><strong>Location:</strong> {clazz.get('location', 'N/A')}</li>
                <li><strong>Duration:</strong> {clazz.get('duration', 'N/A')} minutes</li>
                <li><strong>Slug:</strong> {clazz.get('slug', 'N/A')}</li>
            </ul>
            <h3>Error Details:</h3>
            <p>{result.get('message', 'Unknown error')}</p>
            <p><em>Attempted booking at: {datetime.now().strftime('%Y-%m-%d %I:%M %p')}</em></p>
            """
            
            # Send error email
            mail_client.send_email(
                subject=f"Tennis Booking Error - {class_time}",
                body=email_body
            )
            
            if 'maximum' in result.get('message') or 'without payment' in result.get('message'):
                clazz['failed'] = True

storage.put(plan_id, plan)