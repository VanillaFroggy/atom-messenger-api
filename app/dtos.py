import datetime

from pydantic import BaseModel, ConfigDict
from pydantic import constr, UUID4

from app.models import Role, MessageType

USERNAME_REGEX = r"^[A-Za-z0-9_]+$"
PASSWORD_REGEX = r"^[A-Za-z0-9!@#$%^&*()_+=\-`~{}|:;<>,.?/]{12,}$"


class UserDto(BaseModel):
    id: UUID4
    username: constr(pattern=USERNAME_REGEX)
    role: Role
    blocked: bool

    def to_dict(self):
        if isinstance(self, UserDto):
            return {
                "id": str(self.id),
                "username": self.username,
                "role": self.role,
                "blocked": self.blocked
            }
        else:
            type_name = self.__class__.__name__
            raise TypeError("Unexpected type {0}".format(type_name))


class RegisterUserDto(BaseModel):
    username: constr(pattern=USERNAME_REGEX)
    password: constr(pattern=PASSWORD_REGEX)


class AuthenticateUserDto(BaseModel):
    username: constr(pattern=USERNAME_REGEX)
    password: constr(pattern=PASSWORD_REGEX)


class EditUserRole(BaseModel):
    id: UUID4
    role: Role


class CreateChatDto(BaseModel):
    chat_name: constr(min_length=1)
    users: list[UUID4]


class MessageDto(BaseModel):
    id: UUID4
    chat_id: UUID4
    user_id: UUID4 | None
    value: str
    message_type: MessageType
    datetime: datetime.datetime
    read: bool

    model_config = ConfigDict(arbitrary_types_allowed=True)


class ChatDto(BaseModel):
    id: UUID4
    chat_name: constr(min_length=1)
    users: list[UserDto]
    last_message: MessageDto

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def to_dict(self):
        if isinstance(self, ChatDto):
            return {
                "id": str(self.id),
                "chat_name": self.chat_name,
                "users": self.users,
                "last_message": self.last_message.to_dict(),
            }
        else:
            type_name = self.__class__.__name__
            raise TypeError("Unexpected type {0}".format(type_name))


class SendMessageDto(BaseModel):
    chat_id: UUID4
    user_id: UUID4 | None
    message_type: MessageType
    value: str


class EditMessageDto(BaseModel):
    id: UUID4
    message_type: MessageType
    value: str
