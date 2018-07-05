import ConfigParser
from datetime import datetime, timedelta
import os
import calendar
import phorest
import gcal
import gcal_sync


def _load_config():
    cp = ConfigParser.RawConfigParser()
    with open('config.ini') as fp:
        cp.readfp(fp)

    return {
        'auth': cp.get('general', 'auth'),
        'business': cp.get('general', 'business'),
        'branch': cp.get('general', 'branch'),
        'staff_name': cp.get('general', 'staff_name'),
        'calendar_id': cp.get('general', 'calendar_id'),
    }


def _get_first_monday_before_today():
    result = datetime.today()
    while result.weekday() != calendar.MONDAY:
        result += timedelta(days=-1)
    return result


if __name__ == '__main__':
    debug = bool(os.environ.get('DEBUG'))

    cfg = _load_config()

    next_monday = _get_first_monday_before_today()

    for _ in range(5):
        next_monday += timedelta(days=7)
        next_sunday = next_monday + timedelta(days=6)

        if debug:
            print next_monday.date(), '-', next_sunday.date()

        try:
            appts = phorest.get_appointments_by_date(
                cfg['auth'], cfg['business'], cfg['branch'], cfg['staff_name'],
                next_monday, next_sunday)
        except Exception as e:
            print 'Error', next_monday.date(), '-', next_sunday.date()
            print '    ', str(e)
            continue

        events = gcal.service_events()
        for dt in sorted(appts.keys()):
            existing_events = gcal_sync.get_events_for_day(
                events, cfg['calendar_id'], dt)

            for appt in appts[dt]:
                start_time = appt['start'].strftime('%H:%M')
                end_time = appt['end'].strftime('%H:%M')
                summary = '{}, {}'.format(appt['client'], appt['service'])

                key = u'{}|{}|{}'.format(start_time, end_time, summary)
                if key in existing_events:
                    if debug:
                        print 'existing', key
                    del existing_events[key]
                    continue

                description = '\n'.join(
                    appt[k] for k in ('price', 'email', 'phone')
                    if appt[k]
                )

                if debug:
                    print 'adding', key

                event = gcal.add_event(
                    events, cfg['calendar_id'], summary, description,
                    appt['start'], appt['end'])

            if existing_events.keys():
                if debug:
                    print existing_events.keys()

                for eventid in existing_events.values():
                    gcal.delete_event(events, cfg['calendar_id'], eventid)
