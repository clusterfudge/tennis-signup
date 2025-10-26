"""
Unit tests for timestamp parsing in client.py
"""
import unittest
import datetime
import pytz
from client import _extract_timestamp_from_title


class TestTimestampParsing(unittest.TestCase):
    """Test cases for _extract_timestamp_from_title function"""

    def test_standard_format(self):
        """Test parsing of standard format without extra text"""
        title = 'Thursday 10:45am on 10/30/2025'
        timestamp = _extract_timestamp_from_title(title)
        dt = datetime.datetime.fromtimestamp(timestamp, tz=pytz.timezone('America/Los_Angeles'))
        self.assertEqual(dt.strftime('%A'), 'Thursday')
        self.assertEqual(dt.strftime('%I:%M%p'), '10:45AM')
        self.assertEqual(dt.strftime('%m/%d/%Y'), '10/30/2025')

    def test_with_edition_text(self):
        """Test parsing with edition text (original bug report)"""
        title = 'Thursday 10:45am 90 MINUTE EDITION! on 10/30/2025'
        timestamp = _extract_timestamp_from_title(title)
        dt = datetime.datetime.fromtimestamp(timestamp, tz=pytz.timezone('America/Los_Angeles'))
        self.assertEqual(dt.strftime('%A'), 'Thursday')
        self.assertEqual(dt.strftime('%I:%M%p'), '10:45AM')
        self.assertEqual(dt.strftime('%m/%d/%Y'), '10/30/2025')

    def test_with_time_range(self):
        """Test parsing with time range suffix"""
        title = 'Thursday 10:45am-11:45am on 10/30/2025'
        timestamp = _extract_timestamp_from_title(title)
        dt = datetime.datetime.fromtimestamp(timestamp, tz=pytz.timezone('America/Los_Angeles'))
        self.assertEqual(dt.strftime('%A'), 'Thursday')
        self.assertEqual(dt.strftime('%I:%M%p'), '10:45AM')
        self.assertEqual(dt.strftime('%m/%d/%Y'), '10/30/2025')

    def test_with_time_range_and_edition(self):
        """Test parsing with both time range and edition text"""
        title = 'Thursday 10:45am-11:45am 90 MINUTE EDITION! on 10/30/2025'
        timestamp = _extract_timestamp_from_title(title)
        dt = datetime.datetime.fromtimestamp(timestamp, tz=pytz.timezone('America/Los_Angeles'))
        self.assertEqual(dt.strftime('%A'), 'Thursday')
        self.assertEqual(dt.strftime('%I:%M%p'), '10:45AM')
        self.assertEqual(dt.strftime('%m/%d/%Y'), '10/30/2025')

    def test_with_special_class_text(self):
        """Test parsing with different special text"""
        title = 'Monday 9:00am SPECIAL CLASS on 11/01/2025'
        timestamp = _extract_timestamp_from_title(title)
        dt = datetime.datetime.fromtimestamp(timestamp, tz=pytz.timezone('America/Los_Angeles'))
        self.assertEqual(dt.strftime('%I:%M%p'), '09:00AM')
        self.assertEqual(dt.strftime('%m/%d/%Y'), '11/01/2025')

    def test_with_pipe_separator(self):
        """Test parsing with pipe separator in title"""
        title = 'LB01 | Thursday 10:45am 90 MINUTE EDITION! on 10/30/2025'
        timestamp = _extract_timestamp_from_title(title)
        dt = datetime.datetime.fromtimestamp(timestamp, tz=pytz.timezone('America/Los_Angeles'))
        self.assertEqual(dt.strftime('%A'), 'Thursday')
        self.assertEqual(dt.strftime('%I:%M%p'), '10:45AM')
        self.assertEqual(dt.strftime('%m/%d/%Y'), '10/30/2025')

    def test_consistency_across_formats(self):
        """Test that all formats with same day/time produce same timestamp"""
        titles = [
            'Thursday 10:45am on 10/30/2025',
            'Thursday 10:45am 90 MINUTE EDITION! on 10/30/2025',
            'Thursday 10:45am-11:45am on 10/30/2025',
            'Thursday 10:45am-11:45am 90 MINUTE EDITION! on 10/30/2025',
        ]
        timestamps = [_extract_timestamp_from_title(title) for title in titles]
        # All timestamps should be equal
        self.assertEqual(len(set(timestamps)), 1)


if __name__ == '__main__':
    unittest.main()
