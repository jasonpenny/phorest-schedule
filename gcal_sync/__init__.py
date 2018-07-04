from datetime import datetime, timedelta
import pytz


def get_events_for_day(events, cal_id, search_date):
    start_date = datetime.combine(search_date, datetime.min.time())
    end_date = (
        start_date + timedelta(days=1) - timedelta(minutes=1)
    )
    time_min = start_date \
            .replace(tzinfo=pytz.timezone('America/New_York')).isoformat('T')
    time_max = end_date \
            .replace(tzinfo=pytz.timezone('America/New_York')).isoformat('T')

    result = {}
    pageToken = ''
    while True:
        eventlist = events.list(calendarId=cal_id,
                                pageToken=pageToken,
                                timeMin=time_min,
                                timeMax=time_max).execute()
        for ev in eventlist['items']:
            start = ev['start']['dateTime'][11:16]
            end = ev['end']['dateTime'][11:16]
            what = ev['summary']

            key = u'{}|{}|{}'.format(start, end, what)
            result[key] = ev['id']

        pageToken = eventlist.get('nextPageToken', '')
        if pageToken == '':
            break

    return result
