"""
Unit tests for schedule filtering in build_next_week_schedule
"""
import unittest
import datetime
from unittest.mock import Mock, patch
import pytz
from client import build_next_week_schedule


class TestScheduleFiltering(unittest.TestCase):
    """Test cases for schedule filtering in build_next_week_schedule"""

    @patch('client.requests.Session')
    def test_filters_classes_within_48_hours(self, mock_session):
        """Test that classes within 48 hours are filtered out"""
        # Create mock timestamps using Pacific time (consistent with _extract_timestamp_from_title)
        pacific = pytz.timezone('America/Los_Angeles')
        now = datetime.datetime.now(pacific)
        
        # Class 1: 24 hours from now (should be filtered out)
        future_24h = now + datetime.timedelta(hours=24)
        timestamp_24h = future_24h.strftime('%A %I:%M%p on %m/%d/%Y')
        
        # Class 2: 72 hours from now (should be included)
        future_72h = now + datetime.timedelta(hours=72)
        timestamp_72h = future_72h.strftime('%A %I:%M%p on %m/%d/%Y')
        
        # Mock the HTML response with both classes
        mock_html = f"""
        <html>
            <button class="register-button-closed" 
                    data-title="{timestamp_24h}"
                    data-event-id="event-24h"
                    data-schedule-id="schedule-24h">Not yet open</button>
            <button class="register-button-closed" 
                    data-title="{timestamp_72h}"
                    data-event-id="event-72h"
                    data-schedule-id="schedule-72h">Not yet open</button>
        </html>
        """
        
        mock_response = Mock()
        mock_response.content = mock_html.encode('utf-8')
        mock_session_instance = Mock()
        mock_session_instance.get.return_value = mock_response
        
        class_map = {
            'LB01': [{'event_id': 'test-event', 'slug': 'LB01'}]
        }
        
        result = build_next_week_schedule(mock_session_instance, class_map, ['LB01'])
        
        # The result should only include the 72h class (filtered 24h class)
        self.assertEqual(len(result), 1, "Should only return one class (72h, not 24h)")
        
        if result:
            class_instance = result[0]
            timestamp = class_instance['timestamp']
            time_diff = timestamp - now.timestamp()
            # Assert that the returned class is at least 48 hours in the future
            self.assertGreaterEqual(time_diff, 48 * 60 * 60,
                                  "Class should be at least 48 hours in the future")

    @patch('client.requests.Session')
    def test_filters_classes_beyond_9_days(self, mock_session):
        """Test that classes beyond 9 days are filtered out"""
        # Create mock timestamps using Pacific time (consistent with _extract_timestamp_from_title)
        pacific = pytz.timezone('America/Los_Angeles')
        now = datetime.datetime.now(pacific)
        
        # Class: 10 days from now (should be filtered out)
        future_10d = now + datetime.timedelta(days=10)
        timestamp_10d = future_10d.strftime('%A %I:%M%p on %m/%d/%Y')
        
        # Class: 7 days from now (should be included)
        future_7d = now + datetime.timedelta(days=7)
        timestamp_7d = future_7d.strftime('%A %I:%M%p on %m/%d/%Y')
        
        # Mock the HTML response
        mock_html = f"""
        <html>
            <button class="register-button-closed" 
                    data-title="{timestamp_10d}"
                    data-event-id="event-10d"
                    data-schedule-id="schedule-10d">Not yet open</button>
            <button class="register-button-closed" 
                    data-title="{timestamp_7d}"
                    data-event-id="event-7d"
                    data-schedule-id="schedule-7d">Not yet open</button>
        </html>
        """
        
        mock_response = Mock()
        mock_response.content = mock_html.encode('utf-8')
        mock_session_instance = Mock()
        mock_session_instance.get.return_value = mock_response
        
        class_map = {
            'LB01': [{'event_id': 'test-event', 'slug': 'LB01'}]
        }
        
        result = build_next_week_schedule(mock_session_instance, class_map, ['LB01'])
        
        # The result should only include the 7-day class (filtered 10-day class)
        self.assertEqual(len(result), 1, "Should only return one class (7d, not 10d)")
        
        if result:
            class_instance = result[0]
            timestamp = class_instance['timestamp']
            time_diff = timestamp - now.timestamp()
            # Assert that the returned class is within 9 days
            self.assertLessEqual(time_diff, 9 * 24 * 60 * 60,
                               "Class should be within 9 days")

    def test_48_hour_window_calculation(self):
        """Test that 48 hours equals 2 days exactly"""
        hours_48 = 48 * 60 * 60
        days_2 = 2 * 24 * 60 * 60
        self.assertEqual(hours_48, days_2, "48 hours should equal 2 days")


if __name__ == '__main__':
    unittest.main()
