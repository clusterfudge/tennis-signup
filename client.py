import os
import time
import logging
import requests
from bs4 import BeautifulSoup
from heare.config import SettingsDefinition, Setting

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0" \
             " Safari/537.36"

logging.basicConfig(
    format='[%(asctime)s][%(levelname)-0s] %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')

def get_class_info_from_block(block):
    event_id = block.find(class_='more learn_more_button')['data-event-id']
    desc = block.find(class_='row_link').text
    parts = desc.split(' | ')
    if len(parts) != 3:
        return None
    return {
        'event_id': event_id,
        'slug': parts[0],
        'description': parts[1],
        'schedule': parts[2]
    }


def build_class_map(session: requests.Session):
    all_classes = session.get(
        'https://tcsp.clubautomation.com/calendar/classes-by-class',
        headers={
            'X-Requested-With': 'XMLHttpRequest'
        }
    )
    all_classes.raise_for_status()
    soup = BeautifulSoup(all_classes.content, 'html.parser')
    class_elements = soup.find_all(class_='block')
    result = {}
    for block in class_elements:
        info = get_class_info_from_block(block)
        if info:
            result[info['slug']] = info

    return result


def sign_in(session: requests.Session, email=os.getenv("EMAIL"), password=os.getenv("PASS")):
    page = session.get('https://tcsp.clubautomation.com')
    soup = BeautifulSoup(page.content, "html.parser")
    login_token = soup.find(id="login_token")["value"]
    logged_in = session.post(
        url='https://tcsp.clubautomation.com/login/login',
        data={
             "email": email,
             "password": password,
             "login_token": login_token
         },
        headers={
            'Accept': '*/*',
            'Origin': 'https://tcsp.clubautomation.com',
            'Referrer': 'https://tcsp.clubautomation.com/',
            'X-Requested-With': 'XMLHttpRequest'
        }
    )

    logged_in.raise_for_status()
    # Page invokes login handler via ajax, then refreshes to get credentialed cookies and
    # redirects to member page
    login_redirect = session.get('https://tcsp.clubautomation.com/', allow_redirects=False)
    login_redirect.raise_for_status()


def get_user_info(session: requests.Session):
    user_info = session.get('https://tcsp.clubautomation.com/user/get-member-info').json()
    if user_info.get('success'):
        return user_info.get('info')
    else:
        return user_info


def register(session: requests.Session, class_: dict, user_id):
    page = session.get(f'https://tcsp.clubautomation.com/calendar/event-info?id={class_["event_id"]}')
    page.raise_for_status()
    soup = BeautifulSoup(page.content, "html.parser")
    sign_up_button = soup.find(class_="register-button-now")  # signups are open
    if not sign_up_button:
        sign_up_button = soup.find(class_="register-button-registered")
        if sign_up_button:
            return {"status": 1, "message": f"You are already registered for {class_['slug']}."}
    if not sign_up_button:
        sign_up_button = soup.find(class_="register-button-closed")
        if sign_up_button:
            return {"message": f"Class {class_['slug']} is full."}
    if not sign_up_button:  # give up
        return {"status": -1, "message": "Could not find a signup button.", "error_code": "not-found"}

    event_id = sign_up_button["data-event-id"]
    schedule_id = sign_up_button["data-schedule-id"]
    register_resp = session.post(
        'https://tcsp.clubautomation.com/calendar/fast-register-event',
        data={
            f"userIds[{user_id}]": "true",
            "eventId": event_id,
            "scheduleId": schedule_id
        }
    )
    register_resp.raise_for_status()
    return register_resp.json()


class ClientSettings(SettingsDefinition):
    username = Setting(str)
    password = Setting(str)


class Client(object):
    def __init__(self, settings: ClientSettings):
        self._username = settings.username.get()
        self._password = settings.password.get()
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": USER_AGENT
        })
        self._signed_in = False

    def _sign_in(self):
        if not self._signed_in:
            sign_in(self._session, email=self._username, password=self._password)
            self._signed_in = True
            logging.info("Successfully signed in.")

    def refresh_class_map(self):
        self._sign_in()
        return build_class_map(self._session)

    def register(self, class_slug: str, class_map: dict, attempts: int = 90):
        self._sign_in()
        if class_slug not in class_map:
            logging.error(f"Could not find class with slug {class_slug}")
            return
        user_info = get_user_info(self._session)
        resp = {'message': 'no-attempt-made'}
        for _ in range(attempts):
            resp = register(self._session, class_map[class_slug], user_info.get('id'))
            if resp.get('error_code') != 'not-found':
                break
            logging.info("Open class instance not found, waiting for another attempt.")
            time.sleep(1)
        logging.info(resp['message'])
        return resp


def main(class_slug="LB01"):
    logging.info(f"Attempting to register for {class_slug}.")
    settings = ClientSettings.load()
    client = Client(settings)
    class_map = client.refresh_class_map()
    logging.info("Refreshed class map.")
    client.register(class_slug, class_map)


if __name__ == '__main__':
    main()
