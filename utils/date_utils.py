from datetime import datetime, date, timedelta
from typing import Optional, Union
import re

def parse_date(date_str: Union[str, date, datetime]) -> Optional[date]:
    """Parse a date string to a date object"""
    if isinstance(date_str, date):
        return date_str
    if isinstance(date_str, datetime):
        return date_str.date()
    
    if not date_str or str(date_str).strip() in ['', '–', 'None', 'nan']:
        return None
    
    # Common date formats
    date_formats = [
        '%Y-%m-%d',  # 2026-02-06
        '%d/%m/%Y',  # 06/02/2026
        '%m/%d/%Y',  # 02/06/2026
        '%d-%m-%Y',  # 06-02-2026
        '%d %b %Y',  # 06 Feb 2026
        '%d %B %Y',  # 06 February 2026
    ]
    
    date_str_clean = str(date_str).strip()
    
    for date_format in date_formats:
        try:
            return datetime.strptime(date_str_clean, date_format).date()
        except ValueError:
            continue
    
    # Try regex for other formats
    match = re.search(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})', date_str_clean)
    if match:
        year, month, day = match.groups()
        try:
            return date(int(year), int(month), int(day))
        except ValueError:
            pass
    
    return None

def is_date_in_range(check_date: date, start_date: date, end_date: date) -> bool:
    """Check if a date is within a range (inclusive)"""
    return start_date <= check_date <= end_date

def dates_overlap(start1: date, end1: date, start2: date, end2: date) -> bool:
    """Check if two date ranges overlap"""
    return start1 <= end2 and start2 <= end1

def days_between(date1: date, date2: date) -> int:
    """Calculate days between two dates (absolute value)"""
    return abs((date2 - date1).days)

def add_days_to_date(base_date: date, days: int) -> date:
    """Add days to a date"""
    return base_date + timedelta(days=days)

def format_date_for_display(date_obj: Optional[date]) -> str:
    """Format date for display"""
    if not date_obj:
        return "Not set"
    return date_obj.strftime('%d %b %Y')

def is_future_date(date_obj: date) -> bool:
    """Check if date is in the future"""
    return date_obj > datetime.now().date()

def is_past_date(date_obj: date) -> bool:
    """Check if date is in the past"""
    return date_obj < datetime.now().date()

def get_date_range(start_date: date, end_date: date) -> list:
    """Get list of dates in a range"""
    date_list = []
    current_date = start_date
    while current_date <= end_date:
        date_list.append(current_date)
        current_date += timedelta(days=1)
    return date_list

def calculate_working_days(start_date: date, end_date: date, exclude_weekends: bool = True) -> int:
    """Calculate working days between two dates"""
    if start_date > end_date:
        start_date, end_date = end_date, start_date
    
    total_days = (end_date - start_date).days + 1
    if not exclude_weekends:
        return total_days
    
    # Count weekends
    weekend_days = 0
    current_date = start_date
    for _ in range(total_days):
        if current_date.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
            weekend_days += 1
        current_date += timedelta(days=1)
    
    return total_days - weekend_days

def is_valid_date_range(start_date: date, end_date: date) -> bool:
    """Validate that start date is before end date"""
    return start_date <= end_date

def get_next_weekday(date_obj: date, weekday: int) -> date:
    """Get next specific weekday from given date (0=Monday, 6=Sunday)"""
    days_ahead = weekday - date_obj.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return date_obj + timedelta(days=days_ahead)

def date_to_iso(date_obj: date) -> str:
    """Convert date to ISO format string"""
    return date_obj.isoformat()

def iso_to_date(iso_string: str) -> Optional[date]:
    """Convert ISO string to date"""
    try:
        return datetime.fromisoformat(iso_string).date()
    except ValueError:
        return None