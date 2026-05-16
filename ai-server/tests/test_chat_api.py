from fastapi.testclient import TestClient

from app.main import create_app


def test_healthz_returns_ok() -> None:
    client = TestClient(create_app())

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_flow_with_mock_backend() -> None:
    """칩 기반 흐름: welcome → 자본금 칩 → 거래 유형 칩(전세) → 결과.

    전세는 monthly_rent_max 질문 없이 바로 결과로 간다.
    칩으로 conditions가 다 채워지므로 LLM은 호출되지 않는다.
    """
    with TestClient(create_app()) as client:
        welcome = client.post("/chat", json={"session_id": None, "raw": {}})
        assert welcome.status_code == 200
        welcome_body = welcome.json()
        assert welcome_body["state"] == "asking"
        assert welcome_body["bot_messages"][0] == {
            "type": "bot.text",
            "content": "먼저 자본금이 어느 정도인지 알려주세요.",
        }

        sid = welcome_body["session_id"]

        deal_question = client.post(
            "/chat",
            json={"session_id": sid, "raw": {"budget_max": 200_000_000}},
        )
        assert deal_question.status_code == 200
        assert deal_question.json()["bot_messages"][0] == {
            "type": "bot.text",
            "content": "전세, 월세, 매매 중 어떤 걸 원하시는지 알려주세요.",
        }

        result = client.post(
            "/chat",
            json={"session_id": sid, "raw": {"deal_type": "jeonse"}},
        )
        assert result.status_code == 200
        assert result.json()["state"] == "result"
        assert result.json()["bot_messages"][0]["type"] == "bot.text"
        assert "전세" in result.json()["bot_messages"][0]["content"]
        assert "서울 지역" in result.json()["bot_messages"][0]["content"]


def test_chat_reaches_result_in_two_turns() -> None:
    """단일 LLM 정책: turn 기반이라 최소 2턴 필요 (전세/매매 기준).

    turn 1 (자본금 칩) → 거래 유형 질문.
    turn 2 (거래 유형 칩, 전세) → 결과.
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
        assert turn2.json()["bot_messages"][0]["type"] == "bot.text"
        assert "전세" in turn2.json()["bot_messages"][0]["content"]


def test_monthly_rent_flow_asks_rent_budget() -> None:
    """월세 선택 시 monthly_rent_max 추가 질문 → 3턴에 결과.

    turn 1 (자본금 칩) → 거래 유형 질문.
    turn 2 (월세 칩) → 월세 예산 질문.
    turn 3 (monthly_rent_max) → 결과.
    """
    with TestClient(create_app()) as client:
        turn1 = client.post(
            "/chat",
            json={"session_id": None, "raw": {"budget_max": 200_000_000}},
        )
        sid = turn1.json()["session_id"]

        turn2 = client.post(
            "/chat",
            json={"session_id": sid, "raw": {"deal_type": "monthly_rent"}},
        )
        assert turn2.status_code == 200
        assert turn2.json()["state"] == "asking"
        assert turn2.json()["bot_messages"][0] == {
            "type": "bot.text",
            "content": "월마다 나가는 월세 예산을 얼마로 생각하시나요?",
        }

        turn3 = client.post(
            "/chat",
            json={"session_id": sid, "raw": {"monthly_rent_max": 800_000}},
        )
        assert turn3.status_code == 200
        assert turn3.json()["state"] == "result"
        assert "월세" in turn3.json()["bot_messages"][0]["content"]


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

    첫 raw_message 응답은 내용 인식 여부와 무관하게 거래 유형 질문으로 진행.
    """
    with TestClient(create_app()) as client:
        response = client.post(
            "/chat",
            json={"session_id": None, "raw": {}, "raw_message": "2억 정도 있어요"},
        )

        assert response.status_code == 200
        assert response.json()["state"] == "asking"
        assert response.json()["bot_messages"][0] == {
            "type": "bot.text",
            "content": "전세, 월세, 매매 중 어떤 걸 원하시는지 알려주세요.",
        }
