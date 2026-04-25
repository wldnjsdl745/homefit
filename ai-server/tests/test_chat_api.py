from fastapi.testclient import TestClient

from app.main import create_app


def test_healthz_returns_ok() -> None:
    client = TestClient(create_app())

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_flow_with_mock_backend() -> None:
    with TestClient(create_app()) as client:
        welcome = client.post("/chat", json={"session_id": None, "raw": {}})
        assert welcome.status_code == 200
        welcome_body = welcome.json()
        assert welcome_body["state"] == "asking"
        assert welcome_body["bot_messages"] == [
            {"type": "bot.text", "content": "먼저 자본금이 어느 정도인지 알려주세요."}
        ]

        deal_question = client.post(
            "/chat",
            json={"session_id": welcome_body["session_id"], "raw": {"budget_max": 200_000_000}},
        )
        assert deal_question.status_code == 200
        assert deal_question.json()["bot_messages"] == [
            {"type": "bot.text", "content": "전세/월세 중 어떤 걸 원하시는지 알려주세요."}
        ]

        preference_question = client.post(
            "/chat",
            json={"session_id": welcome_body["session_id"], "raw": {"deal_type": "jeonse"}},
        )
        assert preference_question.status_code == 200
        assert preference_question.json()["state"] == "asking"
        assert preference_question.json()["bot_messages"] == [
            {"type": "bot.text", "content": "추가로 희망하시는 조건이 있나요?"}
        ]

        result = client.post(
            "/chat",
            json={
                "session_id": welcome_body["session_id"],
                "raw": {"preference_text": "역 가까운 곳"},
                "raw_message": "역 가까운 곳",
            },
        )
        assert result.status_code == 200
        assert result.json()["state"] == "result"
        assert result.json()["bot_messages"][-1] == {
            "type": "bot.text",
            "content": "전세 2억 예산에 맞는 지역은 분당·성남·경기도입니다.",
        }


def test_chat_accepts_budget_deal_type_and_preference_in_one_request() -> None:
    with TestClient(create_app()) as client:
        response = client.post(
            "/chat",
            json={
                "session_id": None,
                "raw": {
                    "budget_max": 200_000_000,
                    "deal_type": "jeonse",
                    "preference_text": "역 가까운 곳",
                },
                "raw_message": "전세 2억, 역 가까운 곳",
            },
        )

        assert response.status_code == 200
        assert response.json()["state"] == "result"
        assert response.json()["bot_messages"][-1] == {
            "type": "bot.text",
            "content": "전세 2억 예산에 맞는 지역은 분당·성남·경기도입니다.",
        }


def test_invalid_raw_returns_reprompt_message() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/chat",
        json={"session_id": None, "raw": {"budget_max": -1}},
    )

    assert response.status_code == 200
    assert response.json()["state"] == "asking"
    assert response.json()["bot_messages"] == [
        {"type": "bot.text", "content": "다시 알려주세요."}
    ]


def test_unsupported_raw_message_returns_apology() -> None:
    with TestClient(create_app()) as client:
        response = client.post(
            "/chat",
            json={"session_id": None, "raw": {}, "raw_message": "반려동물 가능해요?"},
        )

        assert response.status_code == 200
        assert response.json()["state"] == "asking"
        assert response.json()["bot_messages"] == [
            {
                "type": "bot.text",
                "content": (
                    "죄송해요, 아직 해당 조건은 이해하지 못해요. "
                    "예산과 전세/월세를 알려주세요."
                ),
            }
        ]
