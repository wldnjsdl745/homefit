from fastapi.testclient import TestClient

from app.main import create_app


def test_healthz_returns_ok() -> None:
    client = TestClient(create_app())

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_flow_with_mock_backend() -> None:
    """칩 기반 2질문 흐름 (preference 단계 제거됨, 단일 LLM 정책).

    welcome → 자본금 칩 → 거래 유형 칩 → 결과.
    칩으로 conditions가 다 채워지므로 LLM은 호출되지 않는다.
    """
    with TestClient(create_app()) as client:
        welcome = client.post("/chat", json={"session_id": None, "raw": {}})
        assert welcome.status_code == 200
        welcome_body = welcome.json()
        assert welcome_body["state"] == "asking"
        assert welcome_body["bot_messages"] == [
            {"type": "bot.text", "content": "먼저 자본금이 어느 정도인지 알려주세요."}
        ]

        sid = welcome_body["session_id"]

        deal_question = client.post(
            "/chat",
            json={"session_id": sid, "raw": {"budget_max": 200_000_000}},
        )
        assert deal_question.status_code == 200
        assert deal_question.json()["bot_messages"] == [
            {"type": "bot.text", "content": "전세/월세 중 어떤 걸 원하시는지 알려주세요."}
        ]

        result = client.post(
            "/chat",
            json={"session_id": sid, "raw": {"deal_type": "jeonse"}},
        )
        assert result.status_code == 200
        assert result.json()["state"] == "result"
        assert result.json()["bot_messages"][-1] == {
            "type": "bot.text",
            "content": "전세 2억 예산에 맞는 지역은 분당·성남·경기도입니다.",
        }


def test_chat_reaches_result_in_two_turns() -> None:
    """단일 LLM 정책: 한 요청에 다 줘도 turn 기반이라 최소 2턴 필요.

    turn 1 (자본금 칩) → 거래 유형 질문.
    turn 2 (거래 유형 칩) → 결과.
    """
    with TestClient(create_app()) as client:
        turn1 = client.post(
            "/chat",
            json={"session_id": None, "raw": {"budget_max": 200_000_000}},
        )
        assert turn1.status_code == 200
        assert turn1.json()["state"] == "asking"
        sid = turn1.json()["session_id"]

        turn2 = client.post(
            "/chat",
            json={"session_id": sid, "raw": {"deal_type": "jeonse"}},
        )
        assert turn2.status_code == 200
        assert turn2.json()["state"] == "result"
        assert turn2.json()["bot_messages"][-1] == {
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


def test_raw_message_advances_dialog() -> None:
    """단일 LLM 정책: raw_message는 내용 무관하게 누적 + 턴 전진.

    LLM은 턴별 호출하지 않으므로 (완료 시 1회), 첫 raw_message 응답은
    내용 인식 여부와 무관하게 다음 질문(거래 유형)으로 진행한다.
    "unsupported 사과" 단계는 단일 LLM 리팩터로 제거됨.
    """
    with TestClient(create_app()) as client:
        response = client.post(
            "/chat",
            json={"session_id": None, "raw": {}, "raw_message": "2억 정도 있어요"},
        )

        assert response.status_code == 200
        assert response.json()["state"] == "asking"
        assert response.json()["bot_messages"] == [
            {"type": "bot.text", "content": "전세/월세 중 어떤 걸 원하시는지 알려주세요."}
        ]
