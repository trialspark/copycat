"""Get messages by user from export files sent by Soc."""

import datetime
import json
import os

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

messages = []
for root, dirs, files in os.walk(
    "./soc", topdown=False  # put unzipped file from soc in a directory called "soc"
):
    for name in files:
        if name != ".DS_Store":
            with open(os.path.join(root, name)) as f:
                print(f"Processing {root}, {name}")
                file_messages = json.load(f)
                messages.extend(file_messages)
print(len(messages))

users_messages = {}
for user in all_users:
    users_messages[user] = []
    for message in messages:
        if (
            message.get("user") == user
            and message["type"] == "message"
            and not message.get("subtype")
            and message["text"] != ""
        ):
            message_text = message["text"]
            message_text = (
                message_text.replace("trialspark", "TS")
                .replace("trial spark", "TS")
                .replace("Trialspark", "TS")
                .replace("TrialSpark", "TS")
            )
            users_messages[user].append(message_text)
    user_message_count = len(users_messages[user])
    print(f"{user} has {user_message_count} messages")

datetime_postfix = int(datetime.datetime.utcnow().timestamp())
soc_messages_filename = f"soc_messages_{datetime_postfix}.json"
with open(soc_messages_filename, "w") as fp:
    json.dump(users_messages, fp)
