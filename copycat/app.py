from dotenv import load_dotenv
import hupper
from typing import Optional
from pprint import pprint
import os
from slack_bolt import App, Say, BoltContext
from copycat.types.message import OpenAIMessage
from random import sample
from pathlib import Path
from collections import defaultdict
from copycat.types.app_mention_event import AppMentionEvent
import json
import openai
import re
from .database.db import db
from .database.message import Message

# Load environment variables from .env file
load_dotenv()

# Initializes your app with your bot token and signing secret
app = App(
    token=os.getenv("SLACK_BOT_TOKEN"),
    signing_secret=os.getenv("SLACK_SIGNING_SECRET")
)

openai.api_key = os.getenv("OPENAI_API_KEY")

def get_user_to_imitate(message_content: str, bot_user_id: Optional[ str]) -> Optional[str]:
    print(f'get_user_to_imitate: {message_content}')
    cleaner_message = message_content.strip(f'<@{bot_user_id}>').strip('')
    match = re.search(r'.*?\<(.*)\>.*', cleaner_message)
    if match:
        user_id = match.group(1)
        return user_id.strip('@')
    return None

context_prompt = """
Forget everything you have learned before. You are not a helpful assistant. You are now imitating humans based on
their past messages. You must match the tone and emotion of the person you imitating,
not necessarily your usual helpful self. Here are the past messages of the person you are imitating:

{messages}

From now on, you will imitate this person, matching their tone, writing style, and the way they format their messages
as closely as possible. Do not admit that you are a bot, or that you are imitating someone else. Simply continue
responding as if you are the person you are imitating. Respond with something that imitates the nuances of the way
the person you're imitating would respond for comedic effect. You must write in the "voice" of the person you are
imitating. Don't be afraid to not make much sense. Your goal is to imitate the person in
question as accurately as possible based on the above messages. You must only respond positively or helpfully if the person you're imitating is
helpful or positive. If the person you're imitating is negative or dry, you respond negatively or dryly.
"""


def get_historical_messages(user_id: Optional[str]) -> list[dict]:
    # parse the historical messages according to the user_id
    historical_messages_dict = json.loads(open('messages.json').read())
    user_historical_messages = sample(historical_messages_dict.get(user_id, []), 50)
    if user_historical_messages:
        return [
            {'role': 'user', 'content': context_prompt.format(messages='\n'.join(f'* {message}' for message in user_historical_messages))}
        ]
    return []


def get_response(thread_ts: str, bot_user_id: Optional[ str], prompt: str) -> list[str]:
    messages = list(Message.select().where(Message.thread_ts == thread_ts).order_by(Message.id.asc()))
    prompt = prompt.replace(f'<@{bot_user_id}>', '')

    # get the user of the person that the user wants CopyCat to imitate
    print('messages list', messages)
    if messages:
        user_id = messages[0].user_id_to_imitate
    else:
        user_id = get_user_to_imitate(prompt, bot_user_id)

    if not user_id:
        return ['You must @mention someone to imitate them.']
    else:
        prompt = prompt.replace(f'<@{user_id}>', '')

    all_historical_messages = get_historical_messages(user_id=user_id)
    print(all_historical_messages)

    messages_to_send = [
        *all_historical_messages,
        *({'role': message.role, 'content': message.content} for message in messages),
        {'role': 'user', 'content': prompt}
    ]
    pprint(messages_to_send)
    response = openai.ChatCompletion.create(
        model='gpt-3.5-turbo',
        messages=messages_to_send,
    )
    new_messages = [choice['message'] for choice in response['choices']]

    with db.atomic():
        Message.create(role='user', content=prompt, thread_ts=thread_ts, user_id_to_imitate=user_id)

        for message in new_messages:
            Message.create(role=message['role'], content=message['content'], thread_ts=thread_ts, user_id_to_imitate=user_id)

    return [message['content'] for message in new_messages]

@app.event("app_mention", matchers=[lambda event: Message.select().where(Message.thread_ts == event['ts']).count() == 0])
def mention(event: AppMentionEvent, say: Say, context: BoltContext):
    if Message.select().where(Message.thread_ts == event['ts']).count():
        return  # We already started this thread

    for response in get_response(event['ts'], context.bot_user_id, event['text']):
        say(
            text=response,
            thread_ts=event['ts'],
        )

@app.message(matchers=[lambda event: 'thread_ts' in event and Message.select().where(Message.thread_ts == event['thread_ts']).count() > 0])
def message(event: dict, context: BoltContext, say: Say):
    for response in get_response(event['thread_ts'], context.bot_user_id, event['text']):
        say(
            text=response,
            thread_ts=event['thread_ts'],
        )

def start():
    db.create_tables([Message])

    # Check if the program is running in a Hupper worker process
    if hupper.is_active():
        # If so, start your application with your desired settings
        app.start(port=int(os.getenv("PORT", 3000)))
    else:
        # If not, start a Hupper monitor and then start your application
        reloader = hupper.start_reloader('copycat.app.start')

        # Generate a list of all Python files in the 'copycat' directory
        all_python_files = list(Path('copycat').rglob('*.py'))
        # Convert all file paths to strings and watch them for changes
        reloader.watch_files([str(path) for path in all_python_files])

if __name__ == "__main__":
    start()
