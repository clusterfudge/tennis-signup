import datetime
import os.path
import sys
import time

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import json
import logging
import storage
import tokens
from tokens import generate_token

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar", "https://www.googleapis.com/auth/calendar.events"]
GCAL_GREEN='2'
GCAL_YELLOW='5'


def create_calendar_service(db: storage.Storage, host='localhost'):
    creds = None
    # TODO: Integrate with storage API instead of sprinkling json files
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    _, token = db.latest('token')
    if token:
        creds = Credentials.from_authorized_user_info(token, SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if 'GOOGLE_APP_CREDENTIALS' in os.environ:
                flow = InstalledAppFlow.from_client_config(
                    json.loads(os.environ.get('GOOGLE_APP_CREDENTIALS')),
                    SCOPES
                )
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    "credentials.json", SCOPES
                )
            creds = flow.run_local_server(
                host=host,
                port=0,
                open_browser=False,
                authorization_prompt_message="Open Browser: {url}"
            )
            # Save the credentials for the next run
            db.put(generate_token('token'), json.loads(creds.to_json()))

    return build("calendar", "v3", credentials=creds)


def _format_event_timestamp(ts: float) -> str:
    from datetime import datetime
    import pytz

    pacific = pytz.timezone('America/Los_Angeles')
    # Convert timestamp to aware datetime
    t = datetime.fromtimestamp(ts, tz=pacific)
    # Format with ISO 8601 format including timezone
    return t.isoformat()


def get_event_for_class(db: storage.Storage, class_instance: dict, calendar_id: str):
    """
    Get event that was created these scripts.
    :param db:
    :param class_instance:
    :param calendar_id:
    :return:
    """
    token, event = db.latest('cal_event', {'schedule_id': class_instance['schedule_id']})
    return token, event


def create_event_for_class(db: storage.Storage, class_instance: dict, calendar_id: str):
    token, existing_event = get_event_for_class(db, class_instance, calendar_id)
    icon = '✅' if class_instance.get('scheduled') else '⏳'
    color = GCAL_GREEN if class_instance.get('scheduled') else GCAL_YELLOW
    body = {
        'colorId': color,
        'summary': f"{icon} Sean @ Tennis",
        'location': '7135 Sportsfield Dr NE, Seattle, WA 98115, USA',
        'start': {'dateTime': _format_event_timestamp(class_instance['timestamp']), 'timeZone': 'America/Los_Angeles'},
        'end': {'dateTime': _format_event_timestamp(class_instance['timestamp'] + (75.0 * 60.0)), 'timeZone': 'America/Los_Angeles'},
        'description': class_instance['description'],
        'reminders': {'useDefault': True}
    }
    op = None
    op_args = {'calendarId': calendar_id, 'body': body}
    client = create_calendar_service(db)
    if existing_event:
        op = client.events().update
        op_args['eventId'] = existing_event['id']
    else:
        op = client.events().insert

    try:
        result = op(**op_args).execute()
        if not token:
            token = tokens.generate_token('cal_event')
        cp = result.copy()
        cp['schedule_id'] = class_instance['schedule_id']
        db.put(token, cp)
        return result
    except Exception as _:
        logging.exception("Error updating calendar")
        return None


def sync_plan_to_calendar(db: storage.Storage, plan: dict, calendar_id: str):
    synced = []
    for slug, inst in plan.items():
        token, existing = db.latest('cal_event', {'schedule_id': inst['schedule_id']})
        if not token:
            synced.append(create_event_for_class(db, inst, calendar_id))

    return synced


def remove_calendar_event(db: storage.Storage, class_instance: dict, calendar_id: str):
    token, existing_event = get_event_for_class(db, class_instance, calendar_id)
    if not existing_event:
        # no calendar event managed for this instance. 🤷
        return
    client = create_calendar_service(db)
    return client.events().delete(calendarId=calendar_id, eventId=existing_event['id']).execute()


def update_calendar_to_new_plan(
        db: storage.Storage,
        old_plan: dict, new_plan: dict,
        calendar_id: str = os.environ.get('SHARED_CALENDAR_ID')):
    if not calendar_id:
        # Don't set this in development, don't update shared calendar in development. Bad!
        return
    to_add = new_plan.keys() - old_plan.keys()
    to_remove = old_plan.keys() - new_plan.keys()
    for slug in to_add:
        create_event_for_class(db, new_plan.get(slug), calendar_id=calendar_id)

    for slug in to_remove:
        existing_instance = old_plan.get(slug)
        if not existing_instance.get('scheduled'):
            # leave things that are already booked on the calendar, and just be sad about it
            # can still be manually removed from the calendar and will not be replaced.
            remove_calendar_event(db, old_plan.get(slug), calendar_id=calendar_id)


def main(args=None):
    # init calendar credentials
    if args is None:
        args = sys.argv
    db = storage.Storage('./storage')
    create_calendar_service(db)
    if '--sync-latest' in args:
        _, plan = db.latest('plan')
        sync_plan_to_calendar(db, plan, os.environ.get('SHARED_CALENDAR_ID'))


if __name__ == "__main__":
    main()

