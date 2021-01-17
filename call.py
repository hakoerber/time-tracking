#!/usr/bin/env python3

import logging
import sys
import argparse
import subprocess as sp
import urllib.parse

import requests

logging.basicConfig(level=logging.WARNING)

class Kimai(object):
    def __init__(self, endpoint, api_token, api_user):
        self._endpoint = endpoint
        self._api_token = api_token
        self._api_user = api_user

    def _call(self, method, path, payload):

        headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-AUTH-USER": self._api_user,
                "X-AUTH-TOKEN": self._api_token,
                }

        endpoint = urllib.parse.urljoin(self._endpoint, urllib.parse.urljoin('/api/', path))

        try:
            request = requests.request(method, endpoint, headers=headers, json=payload, timeout=10.0)
        except requests.exceptions.ReadTimeout:
            print("Request timeout")
            sys.exit(1)

        request.raise_for_status()

        return request.json()

    def get_timesheets(self):
        return self._call('GET', 'timesheets', {})

    def get_active_record(self):
        return self._call('GET', 'timesheets/active', {})

    def get_activities(self):
        return self._call('GET', 'activities', {})

    def start_record(self, activity):
        activities = self.get_activities()
        existing_activity = [a for a in activities if a['name'].lower() == activity]

        if (len(existing_activity) == 0):
            print("Activity \"{}\" not found".format(activity))
            sys.exit(1)
        elif len(existing_activity) != 1:
            print("More than a single result for activity \"{}\"".format(activity))
            sys.exit(1)

        existing_activity = existing_activity[0]

        if existing_activity['project'] is None:
            print("Activity \"{}\" does not have a project set.".format(activity))
            sys.exit(1)


        return self._call(
            'POST',
            'timesheets',
            {
                "project": existing_activity['project'],
                "activity": existing_activity['id'],
            }
        )

    def stop_record(self):
        active_record = self.get_active_record()
        if len(active_record) != 1:
            print("No active recording to stop!")
            sys.exit(1)
        return self._call(
            'PATCH',
            'timesheets/{id}/stop'.format(id=active_record[0]['id']),
            {}
        )


class PasswordStore(object):
    def __init__(self):
        pass

    def _exec(self, cmd):
        return sp.run(cmd, shell=True, stdout=sp.PIPE).stdout.strip().decode('utf-8')

    def get_pw(self, path):
        return self._exec('env -u VIRTUAL_ENV -u PATH ~/bin/mypass show {}|head -1'.format(path))

    def get_element(self, path, element):
        return self._exec('env -u VIRTUAL_ENV -u PATH ~/bin/mypass get {} {}'.format(path, element))

    def get_elements(self, path, elements):
        return self._exec('env -u VIRTUAL_ENV -u PATH ~/bin/mypass get {} {}'.format(path, " ".join(elements))).split('\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    start_parser = subparsers.add_parser('start')
    start_parser.add_argument('activity')
    start_parser.set_defaults(action='start')

    stop_parser = subparsers.add_parser('stop')
    stop_parser.set_defaults(action='stop')

    args = parser.parse_args()
    mypass = PasswordStore()

    print("Getting data from PasswordStore, you might have to touch your YubiKey")
    credentials = mypass.get_elements('mycloud/kimai', ['api.password', 'api.user', 'api.endpoint'])
    kimai_api_token = credentials[0]
    kimai_api_user = credentials[1]
    kimai_api_endpoint = credentials[2]

    kimai_api = Kimai(
        endpoint=kimai_api_endpoint,
        api_user=kimai_api_user,
        api_token=kimai_api_token
    )

    if args.action == 'start':
        if len(kimai_api.get_active_record()) != 0:
            print("There is an active recording!")
            sys.exit(1)

        kimai_api.start_record(args.activity)

    elif args.action == 'stop':
        kimai_api.stop_record()
    else:
        assert(False)
