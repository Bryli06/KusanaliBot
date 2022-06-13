from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
import re
import dateparser #install dateparser

class InvalidTime(Exception):
    def __init__(self, error):
        self.error = error

        super(InvalidTime, self).__init__(f"Error parsing time: {error}")

    def __reduce__(self):
        return (InvalidTime, self.error)

class TimeConverter:
    def __init__(self, convert): #human readable string like tomorrow, 3h, april 20th 1889
        self.start = datetime.now(timezone.utc)
        self.final: datetime = None
        self.convert(convert)

    def convert(self, convert):
        regex = (r'(?:(?P<years>[0-9])(?:years?|y))?'
              r'(?:(?P<months>[0-9]{1,2})(?:months?|mo))?'
              r'(?:(?P<weeks>[0-9]{1,4})(?:weeks?|w))?'
              r'(?:(?P<days>[0-9]{1,5})(?:days?|d))?'
              r'(?:(?P<hours>[0-9]{1,5})(?:hours?|h))?'
              r'(?:(?P<minutes>[0-9]{1,5})(?:min(?:ute)?s?|m))?'
              r'(?:(?P<seconds>[0-9]{1,5})(?:sec(?:ond)?s?|s))?')
        match = re.compile(regex, re.IGNORECASE).match(convert)

        if match and match.group(0): #parse data if is in short time format
            kargs={}
            for k, v in match.groupdict(default='0').items():
                kargs[k] = int(v)

            self.final = self.start + relativedelta(**kargs)

            if self.final < self.start:
                raise InvalidTime("The time is in the past")

            return

        if convert.endswith(" from now"):
            convert = convert[:-9].strip()
        self.final = dateparser.parse(convert, settings = {"TIMEZONE" : "UTC"})
        if self.final:
            self.final = self.final.replace(tzinfo=timezone.utc)
            if self.final < self.start:
                raise InvalidTime("The time is in the past")

            return

        raise InvalidTime(f"Could not parse time {convert}")



