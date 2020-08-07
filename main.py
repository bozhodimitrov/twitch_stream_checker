from copy import deepcopy
from contextlib import suppress
from time import sleep
from json import JSONDecodeError
from json import dumps as json_dumps
from json import loads as json_loads
from fuzzywuzzy.process import extractOne
from argparse import ArgumentParser
from pprint import pprint
from sys import exit
import http.client
from auth import HEADERS


# Front-end keyword: sha256Hash PersistedQueryLink
# https://github.com/apollographql/apollo-link-persisted-queries/blob/master/src/index.ts

# Back-end handling:
# https://github.com/graph-gophers/graphql-go/blob/master/graphql.go

# https://ogs.gg/twitch-stolen-content/

'''
Impersonating the account of the OG Sports player.
Fake giveaway and scamming twitch users.
This account also uses a lot of twitch bots to spam the chat.
'''

GQL_URL = 'gql.twitch.tv'
VERIFIED = {
    'bigdaddy',
    'saksadotaa',
    'midone',
    'topsonous',
    'sumayyl',
    '7ckngmad',
    'jeraxai',
    # 'ogesports',
    'gorgc',
    'zfreek',
    'MadaraDota2',
}

IMPERSONATION_BODY = [{
    "operationName": "ReportUserModal_ReportUser",
    "variables": {
        "input": {
            "description": "video > video more options > impersonation > Impersonating someone else\n\ndescription: Impersonating the account of the OG Sports player.\nFake giveaway and scamming twitch users.\nThis account also uses a lot of twitch bots to spam the chat.", # noqa E501
            "reason": "impersonation",
            "content": "USER_REPORT",
            "contentID": "",
            "extra": "",
            "wizardPath": [
                "video",
                "video more options",
                "impersonation",
                "Impersonating someone else",
            ]
        }
    },
    "extensions": {
        "persistedQuery": {
            "version": 1,
            "sha256Hash": "dd2b8f6a76ee54aff685c91537fd75814ffdc732a74d3ae4b8f2474deabf26fc", # noqa E501
        }
    }
}]

BODY = [
    {
        "operationName": "DirectoryPage_Game",
        "variables": {
            "name": "dota 2",
            "options": {
                "includeRestricted": ["SUB_ONLY_LIVE"],
                "sort":"VIEWER_COUNT",
                "recommendationsContext": {"platform": "web"},
                "requestID": "JIRA-VXP-2397",
                "tags": [],
            },
            "sortTypeIsRecency": False,
            "limit": 100,
        },
        "extensions":{
            "persistedQuery": {
                "version": 1,
                "sha256Hash": "f2ac02ded21558ad8b747a0b63c0bb02b0533b6df8080259be10d82af63d50b3", # noqa E501
            }
        }
    }
]


def gql_request(conn, body, debug=False):
    conn.request('POST', '/gql', body=json_dumps(body), headers=HEADERS)
    response = conn.getresponse()
    if response.status != 200:
        print(f'Invalid response: {response.status}')
        return

    try:
        result = json_loads(response.read())
    except JSONDecodeError:
        result = ''

    if not len(result):
        print(f'Invalid result: {result}')
        return

    if debug:
        pprint(result)
        return

    return result


def send_report(conn, impersonation_body, broadcaster_id):
    impersonation_body[0]['variables']['input']['targetID'] = broadcaster_id
    gql_request(conn, impersonation_body)
    print('Report sent.')


def streams(result):
    try:
        streams = result[0].get('data').get('game').get('streams')
        has_next_page = streams.get('pageInfo').get('hasNextPage')
        edges = streams.get('edges')
    except AttributeError:
        return

    for edge in edges:
        try:
            cursor = edge.get('cursor')
            title = edge.get('node').get('title')
            views_count = edge.get('node').get('viewersCount')
            broadcaster = edge.get('node').get('broadcaster')
            broadcaster_id = broadcaster.get('id')
            login = broadcaster.get('login')
            is_partner = broadcaster.get('roles').get('isPartner')
        except AttributeError:
            continue

        if views_count <= 30:
            return

        if (
            is_partner or
            not (match := extractOne(login, VERIFIED, score_cutoff=69))
        ):
            continue

        verified_account, confidence = match
        yield (
            has_next_page,
            verified_account,
            confidence,
            login,
            title,
            views_count,
            broadcaster_id,
            cursor,
        )


def check_streams(detected_accounts, report=False, debug=False):
    body = deepcopy(BODY)
    impersonation_body = deepcopy(IMPERSONATION_BODY)
    conn = http.client.HTTPSConnection(GQL_URL)

    cursor = ''
    has_next_page = True
    while has_next_page:
        result = gql_request(conn, body, debug)
        if result is None:
            break

        for (
            has_next_page,
            verified_account,
            confidence,
            login,
            title,
            views_count,
            broadcaster_id,
            cursor,
        ) in streams(result):
            if cursor:
                body[0]['variables']['cursor'] = cursor

            if login in detected_accounts:
                continue

            print(
                f'\u001b[36m{verified_account}\u001b[0m {confidence}% '
                f'\u001b[31m{login} '
                f'\u001b[35m{views_count} '
                f'\u001b[0m{title.replace(chr(10), " ")}'
            )

            detected_accounts.add(login)
            if report and confidence >= 90:
                send_report(conn, impersonation_body, broadcaster_id)


def main(debug=False):
    parser = ArgumentParser(description='Twitch Stream Checker')
    parser.add_argument(
        '-r', '--report', action='store_true', help='send report',
    )
    args = parser.parse_args()
    detected_accounts = set()

    while True:
        check_streams(detected_accounts, args.report, debug)
        sleep(60)


if __name__ == '__main__':
    with suppress(KeyboardInterrupt):
        exit(main())
