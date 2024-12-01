from typing import Type
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session, aliased

from app.auth import AuthHandler
from app.dtos import *
from app.models import User, Chat, UserChat, Role, Message, MessageType

auth_handler = AuthHandler()


def map_to_user_dto(user: User | Type[User]) -> UserDto:
    return UserDto(id=user.id,
                   username=user.username,
                   role=user.role,
                   blocked=user.blocked)


def create_user(db: Session, dto: RegisterUserDto):
    hashed_password = auth_handler.get_password_hash(dto.password)
    user = User(username=dto.username,
                password=hashed_password,
                role=Role.USER)
    db.add(user)
    db.commit()
    db.refresh(user)
    return map_to_user_dto(user)


def get_user_by_id(db: Session, user_id: UUID) -> UserDto:
    return map_to_user_dto(db.query(User)
                           .filter(User.id == user_id)
                           .first())


def get_user_by_username(db: Session, username: str) -> User:
    return (db.query(User)
            .filter(User.username == username)
            .first())


def get_user_dto_by_username(db: Session, username: str) -> UserDto:
    return map_to_user_dto(get_user_by_username(db, username))


def map_to_message_dto(message: Message | Type[Message] | None) -> MessageDto:
    return MessageDto(id=message.id,
                      user_id=message.user_id,
                      chat_id=message.chat_id,
                      message_type=message.message_type,
                      value=message.value,
                      datetime=message.datetime,
                      read=message.read)


def send_message(db: Session, dto: SendMessageDto):
    message = Message(chat_id=dto.chat_id,
                      user_id=dto.user_id,
                      message_type=dto.message_type,
                      value=dto.value)
    db.add(message)
    db.commit()
    db.refresh(message)
    return map_to_message_dto(message)


def edit_message(db: Session, dto: EditMessageDto):
    message = (db.query(Message)
               .filter(Message.id == dto.id)).first()
    message.message_type = dto.message_type
    message.value = dto.value
    db.add(message)
    db.commit()
    db.refresh(message)
    return map_to_message_dto(message)


def read_message(db: Session, message_id: UUID) -> MessageDto:
    message = (db.query(Message)
               .filter(Message.id == message_id)).first()
    message.read = True
    db.add(message)
    db.commit()
    db.refresh(message)
    return map_to_message_dto(message)


def get_message_by_id(db: Session, message_id: UUID) -> MessageDto | None:
    return map_to_message_dto((db.query(Message)
                               .filter(Message.id == message_id)).first())


def delete_message(db, message_id):
    message: Message = db.query(Message).filter(Message.id == message_id).first()
    db.delete(message)
    db.commit()
    return message.chat_id


def map_chat_and_user_ids_to_chat_dto(db: Session, chat: Chat | Type[Chat], user_ids: list[UUID],
                                      message: MessageDto = None) -> ChatDto:
    users: list[User] = (db.query(User)
                         .filter(User.id.in_(user_ids))
                         .all())
    user_dtos: list[UserDto] = []
    for user in users:
        user_dtos.append(map_to_user_dto(user))
    if message is None:
        message = map_to_message_dto(send_message(db, SendMessageDto(chat_id=chat.id,
                                                                     user_id=None,
                                                                     message_type=MessageType.TEXT,
                                                                     value="Chat is created")))
    else:
        message = map_to_message_dto(db.query(Message)
                                     .filter(Message.chat_id == chat.id)
                                     .order_by(Message.datetime.desc())
                                     .first())
    return ChatDto(id=chat.id,
                   chat_name=chat.chat_name,
                   users=user_dtos,
                   last_message=message)


def create_chat(db: Session, dto: CreateChatDto) -> ChatDto:
    chat = Chat(chat_name=dto.chat_name)
    db.add(chat)
    db.commit()
    db.refresh(chat)
    first_user_chat = UserChat(chat_id=chat.id,
                               user_id=dto.users[0])
    second_user_chat = UserChat(chat_id=chat.id,
                                user_id=dto.users[1])
    db.add(first_user_chat)
    db.add(second_user_chat)
    db.commit()
    db.refresh(first_user_chat)
    db.refresh(second_user_chat)
    return map_chat_and_user_ids_to_chat_dto(db, chat, dto.users)


def get_chat_by_id(db: Session, chat_id: UUID) -> ChatDto | None:
    user_chats = db.query(UserChat).filter(UserChat.chat_id == chat_id).all()
    user_ids = []
    for user_chat in user_chats:
        user_ids.append(user_chat.user_id)
    return map_chat_and_user_ids_to_chat_dto(db,
                                             ((db.query(Chat)
                                               .filter(Chat.id == chat_id)).first()),
                                             user_ids)


def delete_chat(db, chat_id: UUID):
    db.delete(db.query(UserChat).filter(UserChat.chat_id == chat_id))
    db.delete(db.query(Chat).filter(Chat.id == chat_id))
    db.commit()


def get_messages_by_chat_id(db: Session, chat_id: UUID) -> list[MessageDto] | list[Type[MessageDto]]:
    messages: list[Message] = (db.query(Message)
                               .filter(Message.chat_id == chat_id)
                               .order_by(Message.datetime.asc())).all()
    message_dtos: list[MessageDto] = []
    for message in messages:
        message_dtos.append(map_to_message_dto(message))
    return message_dtos


def map_chat_and_users_dict_chat_user_dict_and_message_dict_to_chat_dto(chat: Chat, id_users: dict[UUID, User],
                                                                        chat_user_map: dict[UUID, list[UUID]],
                                                                        message_dict: dict[UUID, Message]) -> ChatDto:
    users: list[User] = [id_users[user_id] for user_id in chat_user_map[chat.id]]
    return ChatDto(id=chat.id,
                   chat_name=chat.chat_name,
                   users=list([map_to_user_dto(user) for user in users]),
                   last_message=map_to_message_dto(message_dict[chat.id]))


def get_chat_dtos_list(db: Session, user_chats: set[UserChat] | set[Type[UserChat]], user_id: UUID) -> list[ChatDto]:
    chat_ids: set[UUID] = set([user_chat.chat_id for user_chat in user_chats])
    subquery = (
        db.query(
            Message.chat_id,
            Message.id,
            func.row_number()
            .over(partition_by=Message.chat_id, order_by=Message.datetime.desc())
            .label("row_num"),
        )
        .subquery()
    )
    message_alias = aliased(Message)
    message_set: set[Message] = (
        db.query(message_alias)
        .join(subquery, subquery.c.id == message_alias.id)
        .filter(subquery.c.row_num == 1)
        .all()
    )
    message_dict: dict[UUID, Message] = dict()
    for message in message_set:
        message_dict.setdefault(message.chat_id, message)
    chat_ids.union(set([message.chat_id for message in message_set]))
    if user_id is not None:
        user_chats_for_union: set[UserChat] = set(UserChat(chat_id=chat_id, user_id=user_id) for chat_id in chat_ids)
        user_chats.union(user_chats_for_union)
    user_chats.update(set(db.query(UserChat).filter(UserChat.chat_id.in_(chat_ids)).all()))
    chat_user_dict: dict[UUID, list[UUID]] = dict()
    for user_chat in user_chats:
        chat_user_dict.setdefault(user_chat.chat_id, []).append(user_chat.user_id)
    user_ids: set[UUID] = set([user_chat.user_id for user_chat in user_chats])
    users: set[User] = set((db.query(User)
                            .filter(User.id.in_(user_ids))).all())
    users_dict: dict[UUID, User] = dict()
    for user in users:
        users_dict.setdefault(user.id, user)
    chats: list[Chat] = (db.query(Chat)
                         .filter(Chat.id.in_(chat_ids))).all()
    chat_dtos: list[ChatDto] = []
    for chat in chats:
        chat_dtos.append(
            map_chat_and_users_dict_chat_user_dict_and_message_dict_to_chat_dto(chat, users_dict, chat_user_dict,
                                                                                message_dict))
    chat_dtos.sort(key=lambda chat_dto: chat_dto.last_message.datetime, reverse=True)
    return chat_dtos


def get_chats_by_user_id(db: Session, user_id: UUID) -> list[ChatDto]:
    return get_chat_dtos_list(db,
                              set(db.query(UserChat).filter(UserChat.user_id == user_id).all()),
                              user_id)


def get_all_chats(db: Session) -> list[ChatDto]:
    return get_chat_dtos_list(db,
                              set(db.query(UserChat).all()),
                              None)


def edit_user_role(db: Session, dto: EditUserRole):
    user = (db.query(User)
            .filter(User.id == dto.id)).first()
    user.role = dto.role
    db.add(user)
    db.commit()
    db.refresh(user)


def block_user(db: Session, user_id: UUID):
    user = (db.query(User)
            .filter(User.id == user_id)).first()
    user.block = True
    db.add(user)
    db.commit()
    db.refresh(user)
