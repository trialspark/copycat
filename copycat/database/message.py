from peewee import Model, AutoField, TextField, CharField

from .db import db


class Message(Model):
    id = AutoField()
    role = CharField()
    content = TextField()
    thread_ts = CharField()

    class Meta:
        database = db
