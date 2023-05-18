from typing import List, TypedDict

class Element(TypedDict):
    type: str
    user_id: str
    text: str

class Elements(TypedDict):
    elements: List[Element]
    type: str

class Block(TypedDict):
    block_id: str
    elements: List[Elements]
    type: str

class AppMentionEvent(TypedDict):
    blocks: List[Block]
    channel: str
    client_msg_id: str
    event_ts: str
    team: str
    text: str
    ts: str
    type: str
    user: str
