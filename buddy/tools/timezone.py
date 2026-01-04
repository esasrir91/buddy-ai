import json
from typing import Any, Dict, List, Optional
from datetime import datetime
import pytz

from buddy.tools import Toolkit
from buddy.utils.log import log_debug, logger

try:
    import requests
except ImportError:
    raise ImportError("`requests` not installed. Please install using `pip install requests`")


class TimezoneTools(Toolkit):
    def __init__(self, **kwargs):
        """Initialize Timezone Tools."""
        
        tools: List[Any] = [
            self.convert_timezone,
            self.get_timezone_info,
            self.list_timezones,
            self.get_current_time,
            self.calculate_time_difference,
        ]

        super().__init__(name="timezone", tools=tools, **kwargs)

    def convert_timezone(
        self,
        datetime_str: str,
        from_timezone: str,
        to_timezone: str,
        format: str = "%Y-%m-%d %H:%M:%S"
    ) -> str:
        """Convert datetime between timezones.

        Args:
            datetime_str (str): DateTime string to convert
            from_timezone (str): Source timezone (e.g., 'UTC', 'US/Eastern')
            to_timezone (str): Target timezone
            format (str): DateTime format

        Returns:
            str: Converted datetime or error message
        """
        try:
            # Parse the datetime string
            dt = datetime.strptime(datetime_str, format)
            
            # Localize to source timezone
            from_tz = pytz.timezone(from_timezone)
            localized_dt = from_tz.localize(dt)
            
            # Convert to target timezone
            to_tz = pytz.timezone(to_timezone)
            converted_dt = localized_dt.astimezone(to_tz)
            
            return json.dumps({
                "original": {
                    "datetime": datetime_str,
                    "timezone": from_timezone
                },
                "converted": {
                    "datetime": converted_dt.strftime(format),
                    "timezone": to_timezone,
                    "iso_format": converted_dt.isoformat(),
                    "timestamp": converted_dt.timestamp()
                }
            })
        except Exception as e:
            return json.dumps({"error": f"Failed to convert timezone: {str(e)}"})

    def get_timezone_info(self, timezone_name: str) -> str:
        """Get information about a timezone.

        Args:
            timezone_name (str): Timezone name (e.g., 'US/Eastern')

        Returns:
            str: Timezone information or error message
        """
        try:
            tz = pytz.timezone(timezone_name)
            current_time = datetime.now(tz)
            
            # Get UTC offset
            utc_offset = current_time.strftime('%z')            
            # Check if DST is in effect
            is_dst = bool(current_time.dst())
            
            return json.dumps({
                "timezone": timezone_name,
                "current_time": current_time.isoformat(),
                "utc_offset": utc_offset,
                "is_dst": is_dst,
                "abbreviation": current_time.strftime('%Z'),
                "timestamp": current_time.timestamp()
            })
        except Exception as e:
            return json.dumps({"error": f"Failed to get timezone info: {str(e)}"})

    def list_timezones(self, filter_text: Optional[str] = None) -> str:
        """List available timezones.

        Args:
            filter_text (Optional[str]): Filter timezones containing this text

        Returns:
            str: List of timezones or error message
        """
        try:
            all_timezones = list(pytz.all_timezones)
            
            if filter_text:
                filtered_timezones = [
                    tz for tz in all_timezones 
                    if filter_text.lower() in tz.lower()
                ]
                timezones = sorted(filtered_timezones)
            else:
                timezones = sorted(all_timezones)[:50]  # Limit to first 50 for readability
            
            return json.dumps({
                "timezones": timezones,
                "total_count": len(pytz.all_timezones),
                "filtered_count": len(timezones) if filter_text else 50
            })
        except Exception as e:
            return json.dumps({"error": f"Failed to list timezones: {str(e)}"})

    def get_current_time(self, timezone_name: str = "UTC") -> str:
        """Get current time in specified timezone.

        Args:
            timezone_name (str): Timezone name

        Returns:
            str: Current time or error message
        """
        try:
            tz = pytz.timezone(timezone_name)
            current_time = datetime.now(tz)
            
            return json.dumps({
                "timezone": timezone_name,
                "current_time": current_time.isoformat(),
                "formatted": current_time.strftime("%Y-%m-%d %H:%M:%S %Z"),
                "timestamp": current_time.timestamp(),
                "utc_offset": current_time.strftime('%z')
            })
        except Exception as e:
            return json.dumps({"error": f"Failed to get current time: {str(e)}"})

    def calculate_time_difference(
        self,
        datetime1: str,
        timezone1: str,
        datetime2: str,
        timezone2: str,
        format: str = "%Y-%m-%d %H:%M:%S"
    ) -> str:
        """Calculate time difference between two datetimes.

        Args:
            datetime1 (str): First datetime string
            timezone1 (str): First timezone
            datetime2 (str): Second datetime string
            timezone2 (str): Second timezone
            format (str): DateTime format

        Returns:
            str: Time difference or error message
        """
        try:
            # Parse and localize first datetime
            dt1 = datetime.strptime(datetime1, format)
            tz1 = pytz.timezone(timezone1)
            localized_dt1 = tz1.localize(dt1)
            
            # Parse and localize second datetime
            dt2 = datetime.strptime(datetime2, format)
            tz2 = pytz.timezone(timezone2)
            localized_dt2 = tz2.localize(dt2)
            
            # Calculate difference
            time_diff = localized_dt2 - localized_dt1
            
            # Convert to human-readable format
            total_seconds = abs(time_diff.total_seconds())
            days = int(total_seconds // 86400)
            hours = int((total_seconds % 86400) // 3600)
            minutes = int((total_seconds % 3600) // 60)
            seconds = int(total_seconds % 60)
            
            return json.dumps({
                "datetime1": {
                    "datetime": datetime1,
                    "timezone": timezone1,
                    "iso": localized_dt1.isoformat()
                },
                "datetime2": {
                    "datetime": datetime2,
                    "timezone": timezone2,
                    "iso": localized_dt2.isoformat()
                },
                "difference": {
                    "total_seconds": time_diff.total_seconds(),
                    "absolute_seconds": total_seconds,
                    "days": days,
                    "hours": hours,
                    "minutes": minutes,
                    "seconds": seconds,
                    "human_readable": f"{days}d {hours}h {minutes}m {seconds}s"
                }
            })
        except Exception as e:
            return json.dumps({"error": f"Failed to calculate time difference: {str(e)}"})