from uuid import UUID

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Response, Cookie, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import RedirectResponse, ORJSONResponse
from sqlalchemy.orm import Session

import app.dtos as dtos
import app.models as models
import app.service as service
from app.auth import AuthHandler
from app.db import SessionLocal, engine
from app.initialize_db import initialize_db

models.Base.metadata.create_all(bind=engine)

load_dotenv("../.env")
auth_handler = AuthHandler()


def get_db():
    db = SessionLocal()
    try:
        yield db
        initialize_db(db)
    finally:
        db.close()


app = FastAPI(
    title="Atom Messenger Api"
)


class ConnectionManager:
    def __init__(self):
        self.chat_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, chat_id: str):
        await websocket.accept()
        if chat_id not in self.chat_connections:
            self.chat_connections[chat_id] = []
        self.chat_connections[chat_id].append(websocket)

    def disconnect(self, websocket: WebSocket, chat_id: str):
        if chat_id in self.chat_connections:
            self.chat_connections[chat_id].remove(websocket)
            if not self.chat_connections[chat_id]:
                del self.chat_connections[chat_id]

    async def broadcast_to_chat(self, chat_id: str, message: str):
        if chat_id in self.chat_connections:
            for connection in self.chat_connections[chat_id]:
                await connection.send_text(message)


manager = ConnectionManager()


@app.websocket("/ws/chat/{chat_id}")
async def chat_websocket(websocket: WebSocket, chat_id: str):
    await manager.connect(websocket, chat_id)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast_to_chat(chat_id, f"Chat {chat_id}: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket, chat_id)
        await manager.broadcast_to_chat(chat_id, f"Client disconnected from chat {chat_id}")


@app.get("/", response_class=RedirectResponse)
async def index(token: str | None = Cookie(None)):
    if not auth_handler.decode_token(token=token) or token is None:
        return RedirectResponse("/register/")
    return RedirectResponse("/chat/")


async def get_token(response: Response,
                    user: dtos.AuthenticateUserDto,
                    db: Session = Depends(get_db)):
    db_user = service.get_user_by_username(db, username=user.username)
    if (db_user is None) or (not auth_handler.verify_password(user.password, db_user.password)):
        raise HTTPException(status_code=400, detail='Invalid username or password')
    token = auth_handler.encode_token(user.username)
    response.set_cookie(key="token", value=token)
    return response


@app.post("/register/", response_class=ORJSONResponse)
async def register_user(user: dtos.RegisterUserDto,
                        db: Session = Depends(get_db)):
    db_user = service.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="User with this username already exist")
    service.create_user(db=db, dto=user)
    return RedirectResponse("/authenticate/")


@app.post("/authenticate/", response_class=ORJSONResponse)
async def authenticate_user(user: dtos.AuthenticateUserDto,
                            db: Session = Depends(get_db)):
    db_user = service.get_user_by_username(db, username=user.username)
    if (db_user is None) or (not auth_handler.verify_password(user.password, db_user.password)) or db_user.blocked:
        raise HTTPException(status_code=400, detail="Wrong username or password or you are banned")
    response = ORJSONResponse(str(db_user.id))
    await get_token(response=response, user=user, db=db)
    return response


@app.get("/getChatList/{user_id}", response_class=ORJSONResponse)
async def get_chat_list(user_id: UUID,
                        token: str | None = Cookie(None),
                        db: Session = Depends(get_db)):
    if not auth_handler.decode_token(token=token) or token is None:
        return RedirectResponse("/authenticate/")
    chat_list = service.get_chats_by_user_id(db=db, user_id=user_id)
    result = list()
    for chat in chat_list:
        result.append(chat.model_dump())
    return ORJSONResponse(result)


@app.post("/getChatById/{chat_id}", response_class=ORJSONResponse)
async def get_chat_by_id(chat_id: UUID,
                         token: str | None = Cookie(None),
                         db: Session = Depends(get_db)):
    if not auth_handler.decode_token(token=token) or token is None:
        return RedirectResponse("/authenticate/")
    return ORJSONResponse(service.get_chat_by_id(db=db, chat_id=chat_id))


@app.post("/createChat", response_class=ORJSONResponse)
async def create_chat(request: dtos.CreateChatDto,
                      token: str | None = Cookie(None),
                      db: Session = Depends(get_db)):
    if not auth_handler.decode_token(token=token) or token is None:
        return RedirectResponse("/authenticate/")
    return ORJSONResponse(service.create_chat(db=db, dto=request).model_dump())


@app.delete("/deleteChat/{chat_id}", response_class=ORJSONResponse)
async def delete_chat(chat_id: UUID,
                      token: str | None = Cookie(None),
                      db: Session = Depends(get_db)):
    if not auth_handler.decode_token(token=token) or token is None:
        return RedirectResponse("/authenticate/")
    service.delete_chat(db=db, chat_id=chat_id)
    await manager.broadcast_to_chat(str(chat_id), f"DELETE CHAT WITH ID: {chat_id}")
    return ORJSONResponse("")


@app.get("/getMessageList/{chat_id}", response_class=ORJSONResponse)
async def get_message_list(chat_id: UUID,
                           token: str | None = Cookie(None),
                           db: Session = Depends(get_db)):
    if not auth_handler.decode_token(token=token) or token is None:
        return RedirectResponse("/authenticate/")
    message_list = service.get_messages_by_chat_id(db=db, chat_id=chat_id)
    result = list()
    for message in message_list:
        result.append(message.model_dump())
    return ORJSONResponse(result)


@app.get("/getMessageById/{message_id}", response_class=ORJSONResponse)
async def get_message_by_id(message_id: UUID,
                            token: str | None = Cookie(None),
                            db: Session = Depends(get_db)):
    if not auth_handler.decode_token(token=token) or token is None:
        return RedirectResponse("/authenticate/")
    return ORJSONResponse(service.get_message_by_id(db=db, message_id=message_id).model_dump())


@app.post("/sendMessage", response_class=ORJSONResponse)
async def send_message(request: dtos.SendMessageDto,
                       token: str | None = Cookie(None),
                       db: Session = Depends(get_db)):
    if not auth_handler.decode_token(token=token) or token is None:
        return RedirectResponse("/authenticate/")
    message_dto: dtos.MessageDto = service.send_message(db=db, dto=request)
    await manager.broadcast_to_chat(str(request.chat_id), message_dto.model_dump())
    return ORJSONResponse("")


@app.put("/editMessage", response_class=ORJSONResponse)
async def edit_message(request: dtos.EditMessageDto,
                       token: str | None = Cookie(None),
                       db: Session = Depends(get_db)):
    if not auth_handler.decode_token(token=token) or token is None:
        return RedirectResponse("/authenticate/")
    message_dto: dtos.MessageDto = service.edit_message(db=db, dto=request)
    await manager.broadcast_to_chat(str(request.chat_id), message_dto.model_dump())
    return ORJSONResponse("")


@app.put("/readMessage/{message_id}", response_class=ORJSONResponse)
async def read_message(message_id: UUID,
                       token: str | None = Cookie(None),
                       db: Session = Depends(get_db)):
    if not auth_handler.decode_token(token=token) or token is None:
        return RedirectResponse("/authenticate/")
    message_dto: dtos.MessageDto = service.read_message(db=db, message_id=message_id)
    await manager.broadcast_to_chat(str(message_dto.chat_id), message_dto.model_dump())
    return ORJSONResponse("")


@app.delete("/deleteMessage/{message_id}", response_class=ORJSONResponse)
async def delete_message(message_id: UUID,
                         token: str | None = Cookie(None),
                         db: Session = Depends(get_db)):
    if not auth_handler.decode_token(token=token) or token is None:
        return RedirectResponse("/authenticate/")
    chat_id = service.delete_message(db=db, message_id=message_id)
    await manager.broadcast_to_chat(str(chat_id), f"DELETE MESSAGE WITH ID: {message_id}")
    return ORJSONResponse("")


@app.get("/getUserById/{user_id}", response_class=ORJSONResponse)
async def get_user_by_id(user_id: UUID,
                         token: str | None = Cookie(None),
                         db: Session = Depends(get_db)):
    if not auth_handler.decode_token(token=token) or token is None:
        return RedirectResponse("/authenticate/")
    return ORJSONResponse(service.get_user_by_id(db=db, user_id=user_id).model_dump())


# Admin endpoints
@app.get("/getAllChats", response_class=ORJSONResponse)
async def get_chat_list(token: str | None = Cookie(None),
                        db: Session = Depends(get_db)):
    if not auth_handler.decode_token(token=token) or token is None:
        return RedirectResponse("/authenticate/")
    chat_list = service.get_all_chats(db=db)
    result = list()
    for chat in chat_list:
        result.append(chat.model_dump())
    return ORJSONResponse(result)


@app.put("/editUserRole", response_class=ORJSONResponse)
async def edit_user_role(request: dtos.EditUserRole,
                         token: str | None = Cookie(None),
                         db: Session = Depends(get_db)):
    if not auth_handler.decode_token(token=token) or token is None:
        return RedirectResponse("/authenticate/")
    service.edit_user_role(db=db, dto=request)
    return ORJSONResponse("")


@app.put("/blockUser/{user_id}", response_class=ORJSONResponse)
async def block_user(user_id: UUID,
                     token: str | None = Cookie(None),
                     db: Session = Depends(get_db)):
    if not auth_handler.decode_token(token=token) or token is None:
        return RedirectResponse("/authenticate/")
    service.block_user(db=db, user_id=user_id)
    return ORJSONResponse("")


if __name__ == "__main__":
    uvicorn.run("main:app", log_level="info")
