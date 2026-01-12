import json
from datetime import datetime
from dateutil import rrule
from dateutil.relativedelta import relativedelta


def _today():
    return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)


def _yesterday():
    return _today() - relativedelta(days=1)
  

def _this_month():
    return _today().replace(day=1)
  

def _yesterday_month():
    return _yesterday().replace(day=1)
  

def _this_year():
    return _this_month().replace(month=1)
  

def _yesterday_year():
    return _yesterday_month().replace(month=1)
  

class ConfigParser:
    def __init__(self, config=None, date_fmt='%Y-%m-%d', month_fmt='%Y-%m', year_fmt='%Y', list_sep=','):
        self.config = config or {}
        self.date_fmt = date_fmt
        self.month_fmt = month_fmt
        self.year_fmt = year_fmt
        self.list_sep = list_sep
        
    def get(self, key, default=None):
        return self.config.get(key, default)
      
    def list(self, key, default=None):
        return self._cast(str.split, key, default, self.list_sep)
      
    def json(self, key, default=None):
        return self._cast(json.loads, key, default)
      
    def int(self, key, default=None):
        return self._cast(int, key, default)
        
    def bool(self, key, default=None):
        return self._cast(bool, key, default)
      
    def _cast(self, func, key, default=None, *args, **kwargs):
        if key in self.config:
            return func(self.config[key], *args, **kwargs)
        return default
        
    def date(self, key, default=None):
        if default == 'today':
            default = _today()
        elif default == 'yesterday':
            default = _yesterday()
        return self._parse_datetime(key, self.date_fmt, default)
      
    def month(self, key, default=None):
        if default == 'this_month':
            default = _this_month()
        elif default == 'yesterday_month':
            default = _yesterday_month()
        return self._parse_datetime(key, self.month_fmt, default)

    def year(self, key, default=None):
        if default == 'this_year':
            default = _this_year()
        elif default == 'yesterday_year':
            default = _yesterday_year()
        return self._parse_datetime(key, self.year_fmt, default)
      
    def _parse_datetime(self, key, fmt, default=None):
        return self._cast(datetime.strptime, key, default, fmt)
      
    def dates(self, key_start, key_end, default_start=None, default_end=None, default=None):
        return self._range('date', rrule.DAILY, key_start, key_end, default_start, default_end, default)
      
    def months(self, key_start, key_end, default_start=None, default_end=None, default=None):
        return self._range('month', rrule.MONTHLY, key_start, key_end, default_start, default_end, default)
      
    def years(self, key_start, key_end, default_start=None, default_end=None, default=None):
        return self._range('year', rrule.YEARLY, key_start, key_end, default_start, default_end, default)
    
    def _range(self, func, rule, key_start, key_end, default_start, default_end, default):
        func = getattr(self, func)
        start = func(key_start, default=default_start)
        end = func(key_end, default=default_end)
        if start is None or end is None:
            return default
        if start > end:
            start, end, reverse = end, start, True
        else:
            reverse = False
        result = list(rrule.rrule(rule, dtstart=start, until=end))
        if reverse:
            result = result[::-1]
        return result
