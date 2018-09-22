import requests
import xmltodict
import pytz
from collections import defaultdict
from datetime import datetime, timedelta


def get_appointments_by_date(auth, business, branch, staff_name, dtstart, dtend):
    url = (
        'https://prod-us.phorest.com/memento/rest/business/{}/branch/{}/appointment?max=2147483647'
        '&start_time={}T04:00:00.000Z'
        '&end_time={}T04:00:00.000Z&has_notes=true'
        .format(
            business,
            branch,
            dtstart.strftime('%Y-%m-%d'),
            dtend.strftime('%Y-%m-%d')
        )
    )
    r = requests.get(url, headers={'Authorization': auth})
    doc = xmltodict.parse(r.content)

    staffId, clients, services = _get_staff_clients_and_services(doc, staff_name)

    UTC = pytz.timezone('UTC')
    NY = pytz.timezone('America/New_York')

    added = set()
    result = defaultdict(list)
    for appt in doc['appointmentList']['appointment']:
        if staffId != appt.get('staffRef'):
            continue

        client = clients[appt['clientCardRef']]
        service = services[appt['branchServiceRef']]

        apptstart = (
            datetime.strptime(appt['startTime'][:16], '%Y-%m-%dT%H:%M')
            .replace(tzinfo=UTC)
            .astimezone(NY)
        )
        apptend = (
            datetime.strptime(appt['endTime'][:16], '%Y-%m-%dT%H:%M')
            .replace(tzinfo=UTC)
            .astimezone(NY)
        ) + timedelta(minutes=service['gapTime'])

        appointment = {
            'type': 'appointment',
            'start': apptstart,
            'end': apptend,
            'client': client['name'],
            'phone': _get_phone(client),
            'email': client['email'],
            'service': service['name'],
            'price': _get_price(appt, service),
        }
        appt_tpl = (
            appointment['start'],
            appointment['end'],
            appointment['client'],
            appointment['service'],
        )
        if appt_tpl in added:
            continue
        added.add(appt_tpl)
        result[apptstart.date()].append(appointment)

    return result


def get_breaks(auth, business, branch, staff_name, dtstart, dtend):
    url = (
        'https://prod-us.phorest.com/memento/rest/business/{}/branch/{}/staffBreak?max=2147483647&'
        'start_time=%3E{}T04:00:00.000Z&start_time=%3C{}T04:00:00.000Z'
        .format(
            business,
            branch,
            dtstart.strftime('%Y-%m-%d'),
            dtend.strftime('%Y-%m-%d')
        )
    )

    r = requests.get(url, headers={'Authorization': auth})
    doc = xmltodict.parse(r.content)

    staffId = None
    supports = doc['staffBreakList']['support']
    if not isinstance(supports, list):
        supports = [supports]
    for support in supports:
        typ = support.get('@xsi:type')

        if not staffId and typ == 'StaffSupport':
            if staff_name == support['firstName'] + ' ' + support['lastName']:
                staffId = support['identity']['@id']
                break

    if not staffId:
        return

    UTC = pytz.timezone('UTC')
    NY = pytz.timezone('America/New_York')

    result = defaultdict(list)
    for brk in doc['staffBreakList']['staffBreak']:
        if staffId != brk.get('staffRef'):
            continue

        brkstart = (
            datetime.strptime(brk['startTime'][:16], '%Y-%m-%dT%H:%M')
            .replace(tzinfo=UTC)
            .astimezone(NY)
        )
        brkend = (
            datetime.strptime(brk['endTime'][:16], '%Y-%m-%dT%H:%M')
            .replace(tzinfo=UTC)
            .astimezone(NY)
        )

        staffbreak = {
            'type': 'break',
            'start': brkstart,
            'end': brkend,
            'label': brk['label'],
        }
        result[brkstart.date()].append(staffbreak)

    return result


def _get_staff_clients_and_services(doc, staff_name):
    staff_id, clients, services = None, {}, {}

    for support in doc['appointmentList']['support']:
        typ = support.get('@xsi:type')
        if typ == 'ClientCardSupport':
            clients[support['identity']['@id']] = {
                'name': support['firstName'] + ' ' + support['lastName'],
                'phone': support.get('mobile', ''),
                'email': support.get('email', ''),
            }

        elif typ == 'ServiceSupport':
            price = ''
            if support.get('price') and support['price'][0] != '0':
                price = support['price']

            services[support['identity']['@id']] = {
                'name': support['name'],
                'price': price,
                'gapTime': int(support.get('gapTime', 0))
            }

        elif not staff_id and typ == 'StaffSupport':
            if staff_name == support['firstName'] + ' ' + support['lastName']:
                staff_id = support['identity']['@id']

    if not staff_id:
        raise Exception('Staff not found: {}'.format(staff_name))

    return staff_id, clients, services


def _get_phone(client):
    if len(client['phone']) == 11:
        return (
            client['phone'][0] + '.' +
            client['phone'][1:4] + '.' +
            client['phone'][4:7] + '.' +
            client['phone'][7:]
        )

    return client['phone']


def _get_price(appt, service):
    if appt.get('price') and appt['price'][0] != '0':
        return '$' + appt['price']

    if service['price']:
        return '$' + service['price']

    return ''
