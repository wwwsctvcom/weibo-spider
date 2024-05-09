import time
from typing import Optional
from datetime import datetime



def int_to_strftime(a):
    b = time.localtime(a)  # 转为日期字符串
    c = time.strftime("%Y-%m-%d %H:%M:%S", b)  # 格式化字符串
    return c


def months_ago_date(months: Optional[int]):
    from datetime import datetime
    from dateutil.relativedelta import relativedelta

    current_time = datetime.now()

    one_month_ago = current_time - relativedelta(months=months)

    return one_month_ago.strftime("%Y-%m-%d")


def date_compare(date1: str, date2: str) -> int:
    """
    comparing which date is before and after, date format need to be: 1970-01-01;
    """
    d1 = datetime.strptime(date1, "%Y-%m-%d")
    d2 = datetime.strptime(date2, "%Y-%m-%d")
    if d1 > d2:
        return 1
    elif d1 == d2:
        return 0
    else:
        return -1


def get_report_time_sec() -> str:
    """
    return: 1970-01-01_00-00-00
    """
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
