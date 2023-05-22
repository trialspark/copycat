"""Script to get messages by channel and by user from all non-archived public Slack channels."""

import datetime
import json
import os
import time

from dotenv import load_dotenv
from slack_sdk import WebClient

load_dotenv()

# Set up your Slack API token
slack_token = os.getenv("SLACK_API_TOKEN")
client = WebClient(token=slack_token)

# Get list of channels
response = client.conversations_list(
    types="public_channel", limit=1000, exclude_archived=True
)
channels = response["channels"]
channel_count = len(channels)
print(f"Found {channel_count} active public channels.")

# Get list of members in each channel
channels_members = {}
for channel in channels:
    members_response = client.conversations_members(channel=channel["id"], limit=1000)
    members = members_response["members"]
    channels_members[channel["id"]] = members
print(channels_members)

# Get list of all users (using users in general as proxy)
for channel in channels:
    if channel["name"] == "general":
        general_channel_id = channel["id"]
        break
all_users = channels_members[general_channel_id]
print(all_users)


# Function to handle rate limit by waiting for the specified duration
def handle_rate_limit(wait_seconds):
    print(f"Rate limited. Waiting for {wait_seconds} seconds...")
    time.sleep(wait_seconds)


# Function to get last 10k user-generated messages in a given channel
def get_channel_messages(channel_id):
    cursor = None
    max_count = 10000
    messages = []
    while len(messages) < max_count:
        try:
            response = client.conversations_history(
                channel=channel_id,
                limit=min(max_count - len(messages), 1000),
                cursor=cursor,
            )
        except Exception as e:
            handle_rate_limit(int(e.response.headers["Retry-After"]))
            continue

        for message in response["messages"]:
            if (
                message["type"] == "message"
                and not message.get("subtype")
                and message["text"] != ""
            ):
                messages.append(message)
        if not response["has_more"]:
            break
        cursor = response["response_metadata"]["next_cursor"]
    return messages


channels_messages = {}
for channel in channels:
    channels_messages[channel["id"]] = []
    channel_messages = get_channel_messages(channel["id"])
    channels_messages[channel["id"]].extend(channel_messages)

print(channels_messages)

datetime_postfix = int(datetime.datetime.utcnow().timestamp())
channels_messges_filename = f"channels_messages_{datetime_postfix}.json"
with open(channels_messges_filename, "w") as fp:
    json.dump(channels_messages, fp)

users_messages = {}
for user in all_users:
    users_messages[user] = []
    for channel, messages in channels_messages.items():
        for message in messages:
            if message.get("user") == user:
                message_text = message["text"]
                message_text = (
                    message_text.replace("trialspark", "TS")
                    .replace("trial spark", "TS")
                    .replace("Trialspark", "TS")
                    .replace("TrialSpark", "TS")
                )
                users_messages[user].append(message_text)

users_messages_filename = f"users_messages_{datetime_postfix}.json"
with open(users_messages_filename, "w") as fp:
    json.dump(users_messages, fp)
