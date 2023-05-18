from typing import TypedDict, Literal, Union


class OpenAIMessage(TypedDict):
    role: Union[Literal['user'], Literal['system'], Literal['assistant']]
    content: str
