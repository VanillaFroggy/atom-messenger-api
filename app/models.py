import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Column, ForeignKey, DateTime, String, UUID, Boolean
from sqlalchemy.orm import declarative_base

Base = declarative_base()

USERNAME_REGEX = r"^[A-Za-z0-9]+$"
PASSWORD_REGEX = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^\w\s]).{12,}$"


class Role(str, Enum):
    ADMIN = "ADMIN",
    USER = "USER"


class User(Base):
    __tablename__ = 'users'

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    username = Column(String, index=True)
    password = Column(String)
    role = Column(String)
    blocked = Column(Boolean, default=False)


class Chat(Base):
    __tablename__ = 'chats'

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    chat_name = Column(String, index=True)


class UserChat(Base):
    __tablename__ = 'user_chats'

    chat_id = Column(UUID, ForeignKey('chats.id'), primary_key=True)
    user_id = Column(UUID, ForeignKey('users.id'), primary_key=True)


class MessageType(str, Enum):
    TEXT = "TEXT"
    # IMAGE = "IMAGE"
    # VIDEO = "VIDEO"
    # AUDIO = "AUDIO"
    # FILE = "FILE"


class Message(Base):
    __tablename__ = 'messages'

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    chat_id = Column(UUID, ForeignKey('chats.id'))
    user_id = Column(UUID, ForeignKey('users.id'))
    value = Column(String)
    message_type: MessageType = Column(String)
    datetime: datetime = Column(DateTime, default=datetime.now(timezone.utc))
    read = Column(Boolean, default=False)

    # publisher: Mapped["User"] = relationship("User", foreign_keys=[user_id])

    def to_dict(self):
        if isinstance(self, Message):
            return {
                "id": str(self.id),
                "chat_id": str(self.chat_id),
                "user_id": str(self.user_id),
                "message_type": str(self.message_type),
                "datetime": str(self.datetime),
                "read": self.read,
                "value": self.value,
            }
        else:
            type_name = self.__class__.__name__
            raise TypeError("Unexpected type {0}".format(type_name))
