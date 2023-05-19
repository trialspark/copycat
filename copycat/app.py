from dotenv import load_dotenv
import hupper
from typing import Optional
from pprint import pprint
import os
from slack_bolt import App, Say, BoltContext
from copycat.types.message import OpenAIMessage
from random import choices
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
    token=os.getenv("SLACK_BOT_TOKEN"), signing_secret=os.getenv("SLACK_SIGNING_SECRET")
)

openai.api_key = os.getenv("OPENAI_API_KEY")


def get_user_to_imitate(
    message_content: str, bot_user_id: Optional[str]
) -> Optional[str]:
    print(f"get_user_to_imitate: {message_content}")
    cleaner_message = message_content.strip(f"<@{bot_user_id}>").strip("")
    match = re.search(r".*?\<(.*)\>.*", cleaner_message)
    if match:
        user_id = match.group(1)
        return user_id.strip("@")
    return None


context_prompt = """
Your goal is to create a persona based on a set of sample chat messages, and then generate new messages using that persona.
Here are the sample messages you should use to create the persona and generate messages: {messages}.
Send back a message that sounds as similar as possible to the sample messages without copying them exactly. Imagine you are
this person and that you are sending a random message that you might send at any given time.

Your response should all meet the following criteria:
1. It should use the same text formatting as in the sample messages (for example, if the messages do not use capitalization, your response should not either; if the messages use emojis or abbreviations your response should use those emojis and abbreviations too).
2. It should mention a topic from the sample messages.
3. It should not exactly copy any sentences or phrases from the sample messages.
4. It should be written from the perspective of the persona you created based on the sample messages. Do not say that you are an assistant. Do not say that you are a bot. Do not offer to help. Do not speak to the person who wrote the sample messages.
5. You are not a helpful assistant. Do not add helpful questions or phrases to your response. Your response should use the same tone as the sample messages.
6. Limit your response to a single message of 1-5 sentences.
"""


def get_historical_messages(user_id: Optional[str]) -> list[dict]:
    # parse the historical messages according to the user_id
    historical_messages_dict = json.loads(open("messages.json").read())
    user_historical_messages = choices(historical_messages_dict.get(user_id, []), k=50)
    if user_historical_messages:
        return [
            {
                "role": "user",
                "content": context_prompt.format(
                    messages="\n".join(
                        f"* {message}" for message in user_historical_messages
                    )
                ),
            }
        ]
    return []


def get_response(thread_ts: str, bot_user_id: Optional[str], prompt: str) -> list[str]:
    messages = list(
        Message.select()
        .where(Message.thread_ts == thread_ts)
        .order_by(Message.id.asc())
    )
    prompt = prompt.replace(f"<@{bot_user_id}>", "")

    # get the user of the person that the user wants CopyCat to imitate
    print("messages list", messages)
    if messages:
        user_id = messages[0].user_id_to_imitate
    else:
        user_id = get_user_to_imitate(prompt, bot_user_id)

    if not user_id:
        return ["You must @mention someone to imitate them."]
    else:
        prompt = prompt.replace(f"<@{user_id}>", "")

    all_historical_messages = get_historical_messages(user_id=user_id)
    print(all_historical_messages)

    messages_to_send = [
        # for now, the entire prompt to GPT is encapsulated in the historical message, which is currently
        # the most reliable approach to getting CopyCat to imitate a specific user
        *all_historical_messages,
        # uncomment the line below to use the historical messages from the thread
        # *({"role": message.role, "content": message.content} for message in messages),
        # uncomment the line below to ask GPT to respond to a specific prompt
        # {"role": "user", "content": prompt},
    ]
    pprint(messages_to_send)
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages_to_send,
    )
    new_messages = [choice["message"] for choice in response["choices"]]

    with db.atomic():
        Message.create(
            role="user", content=prompt, thread_ts=thread_ts, user_id_to_imitate=user_id
        )

        for message in new_messages:
            Message.create(
                role=message["role"],
                content=message["content"],
                thread_ts=thread_ts,
                user_id_to_imitate=user_id,
            )

    return [message["content"] for message in new_messages]


@app.event(
    "app_mention",
    matchers=[
        lambda event: Message.select().where(Message.thread_ts == event["ts"]).count()
        == 0
    ],
)
def mention(event: AppMentionEvent, say: Say, context: BoltContext):
    if Message.select().where(Message.thread_ts == event["ts"]).count():
        return  # We already started this thread

    for response in get_response(event["ts"], context.bot_user_id, event["text"]):
        say(
            text=response,
            thread_ts=event["ts"],
        )


@app.message(
    matchers=[
        lambda event: "thread_ts" in event
        and Message.select().where(Message.thread_ts == event["thread_ts"]).count() > 0
    ]
)
def message(event: dict, context: BoltContext, say: Say):
    for response in get_response(
        event["thread_ts"], context.bot_user_id, event["text"]
    ):
        say(
            text=response,
            thread_ts=event["thread_ts"],
        )


def start():
    db.create_tables([Message])

    # Check if the program is running in a Hupper worker process
    if hupper.is_active():
        # If so, start your application with your desired settings
        app.start(port=int(os.getenv("PORT", 3000)))
    else:
        # If not, start a Hupper monitor and then start your application
        reloader = hupper.start_reloader("copycat.app.start")

        # Generate a list of all Python files in the 'copycat' directory
        all_python_files = list(Path("copycat").rglob("*.py"))
        # Convert all file paths to strings and watch them for changes
        reloader.watch_files([str(path) for path in all_python_files])


if __name__ == "__main__":
    start()
