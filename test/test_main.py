def test_register_user(client):
    data = {"username": "test_user", "password": "_Test@1234$!&)"}
    response = client.post("/register/", json=data)
    if response.status_code == 200:
        assert response.status_code == 200
        assert "token" in response.cookies
    else:
        assert response.status_code == 400


def test_register_second_user(client):
    data = {"username": "test_user_1", "password": "1_Test@1234$!&)"}
    response = client.post("/register/", json=data)
    if response.status_code == 200:
        assert response.status_code == 200
        assert "token" in response.cookies
    else:
        assert response.status_code == 400


def test_authenticate_user(client):
    data = {"username": "test_user", "password": "_Test@1234$!&)"}
    response = client.post("/authenticate/", json=data)
    assert response.status_code == 200
    assert "token" in response.cookies


def test_authenticate_second_user(client):
    data = {"username": "test_user_1", "password": "1_Test@1234$!&)"}
    response = client.post("/authenticate/", json=data)
    assert response.status_code == 200
    assert "token" in response.cookies


def test_create_chat(client):
    auth_response = client.post("/authenticate/", json={"username": "test_user", "password": "_Test@1234$!&)"})
    auth_response_1 = client.post("/authenticate/", json={"username": "test_user_1", "password": "1_Test@1234$!&)"})
    token = auth_response.cookies.get("token")

    data = {"chat_name": "Test Chat", "users": [str(auth_response.json()), str(auth_response_1.json())]}
    response = client.post("/createChat", json=data, cookies={"token": token})
    print(response.json())
    assert response.status_code == 200
    assert response.json()["chat_name"] == "Test Chat"


def test_get_chat_list(client):
    auth_response = client.post("/authenticate/", json={"username": "test_user", "password": "_Test@1234$!&)"})
    token = auth_response.cookies.get("token")

    response = client.get(f"/getChatList/{str(auth_response.json())}", cookies={"token": token})
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_send_message(client):
    auth_response = client.post("/authenticate/", json={"username": "test_user", "password": "_Test@1234$!&)"})
    token = auth_response.cookies.get("token")

    chat_list_response = client.get(f"/getChatList/{str(auth_response.json())}", cookies={"token": token})
    data = {"chat_id": str(chat_list_response.json()[0]["id"]), "user_id": str(auth_response.json()),
            "message_type": "TEXT", "value": "Hello, world!"}
    response = client.post("/sendMessage", json=data, cookies={"token": token})
    assert response.status_code == 200
    # assert response.json()["value"] == "Hello, world!"


def test_get_message_list(client):
    auth_response = client.post("/authenticate/", json={"username": "test_user", "password": "_Test@1234$!&)"})
    token = auth_response.cookies.get("token")

    chat_list_response = client.get(f"/getChatList/{str(auth_response.json())}", cookies={"token": token})
    response = client.get(f"/getMessageList/{str(chat_list_response.json()[0]['id'])}", cookies={"token": token})
    assert response.status_code == 200
    assert isinstance(response.json(), list)
