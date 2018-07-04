import ConfigParser
from datetime import datetime, timedelta
import calendar
import phorest


def _load_config():
    cp = ConfigParser.RawConfigParser()
    with open('config.ini') as fp:
        cp.readfp(fp)

    return {
        'auth': cp.get('general', 'auth'),
        'business': cp.get('general', 'business'),
        'branch': cp.get('general', 'branch'),
        'staff_name': cp.get('general', 'staff_name'),
    }


def _get_first_monday_before_today():
    result = datetime.today()
    while result.weekday() != calendar.MONDAY:
        result += timedelta(days=-1)
    return result


if __name__ == '__main__':
    cfg = _load_config()

    next_monday = _get_first_monday_before_today()

    for w in range(1):
        next_monday += timedelta(days=7 * w)
        next_sunday = next_monday + timedelta(days=6)

        print next_monday.date(), '-', next_sunday.date()

        appts = phorest.get_appointments_by_date(
            cfg['auth'], cfg['business'], cfg['branch'], cfg['staff_name'],
            next_monday, next_sunday)

        for dt in sorted(appts.keys()):
            print dt
            for appt in appts[dt]:
                import pprint
                pprint.pprint(appt)
            # TODO :    sync events to calendar for day

            print '-' * 60
