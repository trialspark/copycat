from dotenv import load_dotenv
import hupper
from typing import Optional
from pprint import pprint
import os
from slack_bolt import App, Say, BoltContext
from copycat.types.message import OpenAIMessage
from pathlib import Path
from collections import defaultdict
from copycat.types.app_mention_event import AppMentionEvent
import openai
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

def get_response(thread_ts: str, bot_user_id: Optional[ str], prompt: str) -> list[str]:
    messages = list(Message.select().where(Message.thread_ts == thread_ts).order_by(Message.id.asc()))
    prompt = prompt.replace(f'<@{bot_user_id}>', 'CopyCat')

    response = openai.ChatCompletion.create(
        model='gpt-3.5-turbo',
        messages=[
            {'role': 'system', 'content': 'You are CopyCat, a bot that imitates specific humans in a conversation.'},
            *({'role': message.role, 'content': message.content} for message in messages),
            {'role': 'user', 'content': prompt}
        ],
    )
    new_messages = [choice['message'] for choice in response['choices']]

    with db.atomic():
        Message.create(role='user', content=prompt, thread_ts=thread_ts)

        for message in new_messages:
            Message.create(role=message['role'], content=message['content'], thread_ts=thread_ts)

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
