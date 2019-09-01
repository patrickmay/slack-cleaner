#!/usr/bin/env python3

import sys
import requests
import json
import time

# This is a collection of functions that allow Slack messages to be
# deleted in bulk.

CHANNEL_API = "https://slack.com/api/conversations.list"
CHANNEL_LIMIT = 999
CHANNEL_TYPES = "private_channel,mpim,im"
HISTORY_API = "https://slack.com/api/conversations.history"
DELETE_API = "https://slack.com/api/chat.delete"

def slack_channels(token):
    """
    Return a list of all Slack channels available to the user identified
    by TOKEN.
    """
    channels = list()
    # Mark:  add cursor-based pagination
    payload = {'token': token,'limit': CHANNEL_LIMIT,'types': CHANNEL_TYPES}
    r = requests.get(CHANNEL_API,params=payload)

    for channel in r.json()['channels']:
        channels.append({'id': channel['id'],'name': channel.get('name',None)})

    return channels

def slack_message_metadata(token,channel_id,cursor=None):
    """ Return the user IDs and timestamps for all messages on the channel. """
    metadata = list()
    payload = {'token': token,'channel': channel_id,'cursor': cursor}
    r = requests.get(HISTORY_API,params=payload)
    response = r.json()
    
    for message in response['messages']:
        metadata.append({'user': message['user'],'timestamp': message['ts']})

    if ('response_metadata' in response
        and 'next_cursor' in response['response_metadata']
        and len(response['response_metadata']['next_cursor']) > 0):
        next_cursor = response['response_metadata']['next_cursor']
        metadata.extend(slack_message_metadata(token,channel_id,next_cursor))
    
    return metadata

def slack_timestamps(token,channel_id,user_id):
    """
    Return the timestamps of all messages with USER_ID from the channel
    with CHANNEL_ID.
    """
    timestamps = list()
    metadata = slack_message_metadata(token,channel_id)

    for metadatum in metadata:
        if metadatum['user'] == user_id:
            timestamps.append(metadatum['timestamp'])
            
    print("Found {} messages, {} for specified user."
          .format(len(metadata),len(timestamps)))

    return timestamps

def slack_delete(token,channel_id,user_id):
    """ Remove all messages with USER_ID from the channel with CHANNEL_ID. """
    timestamps = slack_timestamps(token,channel_id,user_id)
    payload = {'token': token,'channel': channel_id,'ts': None}
    success = 0
    failure = 0
    
    for timestamp in timestamps:
        payload['ts'] = timestamp
        r = requests.get(DELETE_API,params=payload)
        result = r.json()
        if 'ok' in result and result['ok']:
            success += 1
        else:
            failure += 1
            print(result.get('error','Bad response.'))
        time.sleep(3)

    return success, failure


if __name__ == "__main__":
    if len(sys.argv) == 2:
        channels = slack_channels(sys.argv[1])
        for channel in channels:
            print("id:  {}, name:  {}".format(channel['id'],channel['name']))
    elif len(sys.argv) == 4:
        success, failure = slack_delete(sys.argv[1],sys.argv[2],sys.argv[3])
        print("Deleted {} successfully and failed to delete {}."
              .format(success,failure))
    else:
        print("Usage:  {} <token> [<channel-id> <user-id>]".format(sys.argv[0]))
