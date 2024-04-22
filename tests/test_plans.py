import shutil
import copy
import tempfile
from unittest import TestCase

import tokens
from web import mark_bookings

from storage import Storage

TEST_PLAN = {
    "LB03": {
        "event_id": "850377",
        "slug": "LB03",
        "description": "LB03 | Live Ball 3.5-4.0 Drop-in | Monday 7:30pm-8:45pm on 04/22/2024",
        "schedule": "Monday 7:30pm-8:45pm",
        "schedule_id": "1408968",
        "timestamp": 1713839400
    },
    "LB06": {
        "event_id": "850362",
        "slug": "LB06",
        "description": "LB06 | Live Ball 4.0+ Drop-in | Tuesday 6:15pm-7:30pm on 04/23/2024",
        "schedule": "Tuesday 6:15pm-7:30pm",
        "schedule_id": "1408991",
        "timestamp": 1713921300,
        "scheduled": True
    },
    "LB16": {
        "event_id": "850368",
        "slug": "LB16",
        "description": "LB16 | Live Ball 3.5+ Drop-in | Friday 12:00pm-1:15pm on 04/26/2024",
        "schedule": "Friday 12:00pm-1:15pm",
        "schedule_id": "1409047",
        "timestamp": 1714158000
    },
    "LB19": {
        "event_id": "850373",
        "slug": "LB19",
        "description": "LB19 | Live Ball 4.0+ Drop-in | Saturday 9:30am-10:45am on 04/27/2024",
        "schedule": "Saturday 9:30am-10:45am",
        "schedule_id": "1409063",
        "timestamp": 1714235400
    }
}
TEST_BOOKING = {
    "status": 1,
    "message": "You have successfully registered for LB03 "
               "| Live Ball 3.5-4.0 Drop-in "
               "| Monday 7:30pm-8:45pm on April 22, 2024 from 07:30pm - 08:45pm",
    "countRegistered": 1,
    "registeredCount": 1,
    "registeredUsers": "",
    "waitListedUsers": "",
    "isWaitListEnabled": False,
    "maxPerson": 12,
    "event_id": "850377",
    "scheduled_id": "1408968"
}


class TestPlans(TestCase):
    def setUp(self):
        self.storage_directory = tempfile.mkdtemp()
        self.storage = Storage(self.storage_directory)

    def tearDown(self):
        shutil.rmtree(self.storage_directory)

    def test_mark_booking(self):
        plan = copy.deepcopy(TEST_PLAN)
        plan_id = tokens.generate_token('plan')
        self.storage.put(plan_id, plan)
        _id = tokens.generate_token('book')
        self.storage.put(_id, TEST_BOOKING)
        mark_bookings(plan, self.storage)
        self.storage.put(plan_id, plan)
        from_storage = self.storage.get(plan_id)
        self.assertTrue(from_storage['LB03']['scheduled'])
