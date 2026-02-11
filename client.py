import os
import re
import datetime
import time
import logging
from collections import defaultdict
from typing import List

import requests
from bs4 import BeautifulSoup
from heare.config import SettingsDefinition, Setting

import cal
from storage import Storage
import tokens

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) " \
             "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0" \
             " Safari/537.36"


log_storage = Storage('./log')
obj_storage = Storage('./storage')


def http_log(response: requests.Response, *args, **kwargs) -> None:
    token = tokens.generate_token('http')
    request = response.request
    log_storage.put(token, {
        'time': datetime.datetime.now().timestamp(),
        'duration': response.elapsed.total_seconds(),
        'request': {
            'method': request.method,
            'headers': dict(request.headers),
            'url': request.url,
            'body': str(request.body)
        },
        'response': {
            'status': response.status_code,
            'headers': dict(response.headers),
            'body': response.text
        }
    })


def make_session() -> requests.Session:
    s = requests.Session()
    s.hooks['response'].append(http_log)
    return s


def store_booked_class(instance, resp: dict):
    token = tokens.generate_token('book')
    body = resp.copy()
    body['event_id'] = instance['event_id']
    body['scheduled_id'] = instance['schedule_id']
    obj_storage.put(token, body)


def successful_registration_response(resp: dict) -> bool:
    return resp.get('status') == 1 \
        or 'already' in resp.get('message', '')


def _extract_late_fall_slug(class_name):
    """Extract a synthetic slug for Late Fall classes.
    
    Examples:
        "Late Fall Chad Wooten LB Workout" -> "LF-Chad"
        "Late Fall Kyle Wooten LB Workout" -> "LF-Kyle"
        "Late Fall 4.0-4.5 LB Workout" -> "LF-4.0-4.5"
    """
    # Check for coach name pattern: "Late Fall <FirstName> <LastName> LB Workout"
    coach_match = re.search(r'Late Fall (\w+) \w+ LB Workout', class_name)
    if coach_match:
        return f"LF-{coach_match.group(1)}"
    
    # Check for skill level pattern: "Late Fall <level> LB Workout"
    level_match = re.search(r'Late Fall ([\d.]+-[\d.]+) LB Workout', class_name)
    if level_match:
        return f"LF-{level_match.group(1)}"
    
    return None


def get_class_info_from_block(block):
    event_id = block.find(class_='more learn_more_button')['data-event-id']
    desc = block.find(class_='row_link').text
    # Split on ' | ' or '| ' to handle inconsistent formatting on the site
    parts = re.split(r'\s?\|\s?', desc)
    if len(parts) != 3:
        return None
    
    slug = None
    
    # Match class slugs like "LB01", "BMC12", "CT05", "LB12.5"
    # optionally preceded by a year like "2025 " or "2026 "
    slug_search = re.search(r'(?:\d{4}\s)?([A-Z]{2,3}\s?\d+(?:\.\d+)?)', parts[0])
    if slug_search:
        slug = slug_search.group(1).replace(' ', '')  # Normalize by removing spaces
    
    # Handle Late Fall classes with synthetic slugs
    if not slug and 'Late Fall' in parts[0]:
        slug = _extract_late_fall_slug(parts[0])
    
    if not slug:
        return None
    
    return {
        'event_id': event_id,
        'slug': slug,
        'description': parts[1],
        'schedule': parts[2],
        'seasonal_slug': parts[0]
    }


def _extract_timestamp_from_title(title):
    import pytz
    pacific = pytz.timezone('America/Los_Angeles')
    parts = title.split("|")
    tstr = parts[-1]
    # First remove time range suffix (e.g., "-11:45am")
    rx = re.compile("-[0-9]+:[0-9]{2}[ap]m")
    tstr = rx.sub('', tstr).strip()
    # Remove any additional text between the time and "on" (e.g., "90 MINUTE EDITION!")
    # This regex matches: (time with am/pm) + (any text) + (literal " on")
    # and replaces it with just: (time with am/pm) + " on"
    rx_edition = re.compile(r'([0-9]{1,2}:[0-9]{2}[ap]m)\s+.*?\s+on')
    tstr = rx_edition.sub(r'\1 on', tstr)
    # Parse the date without timezone first
    naive_dt = datetime.datetime.strptime(tstr, '%A %I:%M%p on %m/%d/%Y')
    # Localize it to Pacific time
    local_dt = pacific.localize(naive_dt)
    return int(local_dt.timestamp())


def build_next_week_schedule(session: requests.Session, class_map: dict[str, dict], slugs:List[str]):
    instances = {}
    # Calculate the minimum timestamp (48 hours from now - past the booking window)
    min_timestamp = datetime.datetime.now().timestamp() + (48 * 60 * 60)
    # Calculate the cutoff timestamp for 9 days in the future
    cutoff_timestamp = datetime.datetime.now().timestamp() + (9 * 24 * 60 * 60)
    
    for slug in slugs:
        if slug not in class_map:
            continue
        for inst in class_map[slug]:
            class_ = inst.copy()
            page = session.get(f'https://tcsp.clubautomation.com/calendar/event-info?id={class_["event_id"]}')
            soup = BeautifulSoup(page.content, "html.parser")
            candidate_instances = soup.find_all(class_='register-button-closed')
            
            # Filter candidate_instances to be within 48 hours to 9 days in the future
            filtered_candidate_instances = []
            for instance in candidate_instances:
                instance_timestamp = _extract_timestamp_from_title(instance['data-title'])
                if min_timestamp <= instance_timestamp <= cutoff_timestamp:
                    filtered_candidate_instances.append(instance)
            candidate_instances = filtered_candidate_instances
            
            eligible_instances = list(filter(
                    lambda x: (x.text != 'Full' and x.text != 'Closed') or x.text == 'Not yet open',
                    candidate_instances
                ))
            
            # Also filter register-button-now instances for the same criteria
            now_instances = soup.find_all(class_='register-button-now')
            filtered_now_instances = []
            for instance in now_instances:
                instance_timestamp = _extract_timestamp_from_title(instance['data-title'])
                if min_timestamp <= instance_timestamp <= cutoff_timestamp:
                    filtered_now_instances.append(instance)
            candidate_instances = filtered_now_instances
            
            eligible_instances = candidate_instances + eligible_instances

            if not eligible_instances:
                continue
            next_instance = eligible_instances[0]
            class_['event_id'] = next_instance['data-event-id']
            class_['schedule_id'] = next_instance['data-schedule-id']
            class_['description'] = next_instance['data-title']
            class_['slug'] = slug
            class_['timestamp'] = _extract_timestamp_from_title(class_['description'])
            instances[slug] = class_
            break
    return sorted(instances.values(), key=lambda x: x['timestamp'])


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
    result = defaultdict(list)
    for block in class_elements:
        info = get_class_info_from_block(block)
        if info:
            result[info['slug']].append(info)

    return result


def sign_in(session: requests.Session, email=os.getenv("EMAIL"), password=os.getenv("PASSWORD")):
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


def register(session: requests.Session, class_: dict, user_id, get_state: bool = False):
    page = session.get(f'https://tcsp.clubautomation.com/calendar/event-info?id={class_["event_id"]}')
    page.raise_for_status()
    soup = BeautifulSoup(page.content, "html.parser")
    sign_up_button = soup.find(class_="register-button-now")  # signups are open
    if not sign_up_button:
        sign_up_button = soup.find(class_="register-button-registered")
        if sign_up_button and not get_state:
            return {"status": 1, "message": f"You are already registered for {class_['slug']}."}
    if not sign_up_button:
        sign_up_button = soup.find(class_="register-button-closed")
        if sign_up_button and not get_state:
            return {"status": -1, "message": f"Class {class_['slug']} is or not yet open."}
    if not sign_up_button:  # give up
        return {"status": -1, "message": "Could not find a signup button.", "error_code": "not-found"}

    event_id = sign_up_button["data-event-id"]
    schedule_id = sign_up_button["data-schedule-id"]
    return register_for_instance(session, event_id, schedule_id, user_id)


def register_for_instance(session, event_id, schedule_id, user_id):
    """
    Register for a class instance. First tries fast-register, then falls back
    to cart checkout flow for classes that require payment (like LB03).
    """
    body = {
        f"userIds[{user_id}]": "true",
        "eventId": event_id,
        "scheduleId": schedule_id,
        "purpose": None,
    }
    
    # Try fast-register first
    register_resp = session.post(
        'https://tcsp.clubautomation.com/calendar/fast-register-event',
        data=body
    )
    register_resp.raise_for_status()
    result = register_resp.json()
    
    # If payment required, fall back to cart checkout flow
    if result.get('status') == -1 and 'without payment' in result.get('message', ''):
        logging.info("Fast register requires payment, falling back to cart checkout flow")
        return _register_via_cart(session, event_id, schedule_id, user_id)
    
    return result


def _register_via_cart(session, event_id, schedule_id, user_id):
    """
    Register for a class by adding to cart and checking out with house charge.
    Used for classes that require payment (like LB03).
    """
    # Step 1: Add to cart via register-event endpoint
    body = {
        f"userIds[{user_id}]": "true",
        "eventId": event_id,
        "scheduleId": schedule_id,
    }
    
    add_resp = session.post(
        'https://tcsp.clubautomation.com/calendar/register-event',
        data=body
    )
    add_resp.raise_for_status()
    add_result = add_resp.json()
    
    if add_result.get('status') != 1:
        logging.error(f"Failed to add to cart: {add_result.get('message')}")
        add_result['cart_url'] = 'https://tcsp.clubautomation.com/member/cart'
        return add_result
    
    logging.info(f"Added to cart: {add_result.get('message')}")
    
    # Step 2: Get cart page to find cart item ID and form details
    cart_resp = session.get('https://tcsp.clubautomation.com/member/cart')
    cart_html = cart_resp.text
    
    # Extract cart item IDs from form action
    match = re.search(r'cart_items/([\d,]+)/\?ajax=1', cart_html)
    if not match:
        logging.error("Could not find cart item IDs in cart page")
        return {
            'status': -1, 
            'message': 'Added to cart but could not find cart item ID for checkout',
            'cart_url': 'https://tcsp.clubautomation.com/member/cart'
        }
    
    cart_item_ids = match.group(1)
    logging.info(f"Found cart item IDs: {cart_item_ids}")
    
    # Extract form field values
    def extract_hidden_value(html, name):
        match = re.search(rf'name="{name}"[^>]*value="([^"]*)"', html)
        return match.group(1) if match else None
    
    # Step 3: Submit checkout with house charge
    checkout_url = f'https://tcsp.clubautomation.com/member/cart/step/1/cart_items/{cart_item_ids}/?ajax=1'
    checkout_data = {
        'active_gateway': extract_hidden_value(cart_html, 'active_gateway') or 'CashFlow',
        'user_id': extract_hidden_value(cart_html, 'user_id') or str(user_id),
        'continue': extract_hidden_value(cart_html, 'continue') or '1',
        'account': 'house charge',
    }
    
    # Add billing address fields if present
    bill_street = extract_hidden_value(cart_html, 'bill_street_address')
    if bill_street:
        checkout_data['bill_street_address'] = bill_street
    bill_city = extract_hidden_value(cart_html, 'bill_city')
    if bill_city:
        checkout_data['bill_city'] = bill_city
    bill_state = extract_hidden_value(cart_html, 'bill_state')
    if bill_state:
        checkout_data['bill_state'] = bill_state
    
    logging.info(f"Submitting checkout to {checkout_url}")
    checkout_resp = session.post(checkout_url, data=checkout_data)
    checkout_resp.raise_for_status()
    
    # Check if checkout succeeded (look for "Thank you" in response)
    if 'Thank you' in checkout_resp.text or 'thank you' in checkout_resp.text.lower():
        logging.info("Cart checkout successful")
        return {
            'status': 1,
            'message': 'Successfully registered via cart checkout (house charge)',
            'countRegistered': 1
        }
    else:
        logging.error(f"Cart checkout may have failed. Response: {checkout_resp.text[:500]}")
        return {
            'status': -1,
            'message': 'Cart checkout submitted but success not confirmed. Please check cart manually.',
            'cart_url': 'https://tcsp.clubautomation.com/member/cart'
        }


class ClientSettings(SettingsDefinition):
    username = Setting(str)
    password = Setting(str)
    get_state = Setting(bool, default=False, required=False)


class Client(object):
    def __init__(self, settings: ClientSettings):
        self._username = settings.username.get()
        self._password = settings.password.get()
        self._session = make_session()
        self._session.headers.update({
            "User-Agent": USER_AGENT
        })
        self._signed_in = False

    def _sign_in(self):
        if not self._signed_in:
            sign_in(self._session, email=self._username, password=self._password)
            self._signed_in = True
            logging.debug("Successfully signed in.")

    def refresh_class_map(self):
        self._sign_in()
        return build_class_map(self._session)

    def register(self, class_slug: str, class_map: dict, attempts: int = 90, get_state=False):
        self._sign_in()
        if class_slug not in class_map:
            logging.error(f"Could not find class with slug {class_slug}")
            return
        user_info = get_user_info(self._session)
        resp = {'status': -1, 'message': 'no-attempt-made'}
        for _ in range(attempts):
            resp = register(self._session, class_map[class_slug], user_info.get('id'), get_state=get_state)
            if resp.get('error_code') != 'not-found':
                break
            logging.info("Open class instance not found, waiting for another attempt.")
            time.sleep(1)
        logging.info(resp['message'])
        return resp

    def register_for_instance(self, class_instance, attempts: int = 90):
        self._sign_in()
        user_info = get_user_info(self._session)
        resp = {'status': -1, 'message': 'no-attempt-made'}
        for _ in range(attempts):
            resp = register_for_instance(
                self._session,
                class_instance['event_id'],
                class_instance['schedule_id'],
                user_info.get('id')
            )

            if 'maximum number' in resp.get('message') or 'without payment' in resp.get('message'):
                break
            if successful_registration_response(resp):
                store_booked_class(class_instance, resp)
                cal.create_event_for_class(obj_storage, class_instance, os.environ.get('SHARED_CALENDAR_ID'))
                break
            logging.debug("Open class instance not found, waiting for another attempt.")
            time.sleep(1)

        return resp


def main(class_slug="LB01", get_state=False):
    logging.info(f"Attempting to register for {class_slug}.")
    settings = ClientSettings.load()
    client = Client(settings)
    class_map = client.refresh_class_map()
    logging.info("Refreshed class map.")
    result = client.register(class_slug, class_map, get_state=settings.get_state.get())
    if result.get('registeredUsers'):
        logging.info(result.get('registeredUsers'))


if __name__ == '__main__':
    logging.basicConfig(
        format='[%(asctime)s][%(levelname)-0s] %(message)s',
        level=logging.INFO,
        datefmt='%Y-%m-%d %H:%M:%S')
    main()
