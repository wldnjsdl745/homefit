from fastapi.testclient import TestClient

from app.main import create_app


def test_healthz_returns_ok() -> None:
    client = TestClient(create_app())

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_flow_with_mock_backend() -> None:
    """칩 기반 흐름: 예산 → 거래 → 희망지역 → 통근지 → 연령층 → 인프라 → 결과.

    전세는 monthly_rent_max 질문 없이 생활 선호를 확인한 뒤 결과로 간다.
    칩으로 conditions가 다 채워지므로 LLM은 호출되지 않는다.
    """
    with TestClient(create_app()) as client:
        welcome = client.post("/chat", json={"session_id": None, "raw": {}})
        assert welcome.status_code == 200
        welcome_body = welcome.json()
        assert welcome_body["state"] == "asking"
        assert welcome_body["bot_messages"][0] == {
            "type": "bot.text",
            "content": (
                "거래 가능한 예산 상한을 알려주세요. "
                "매매는 매매가, 전세와 월세는 보증금 기준이에요."
            ),
        }

        sid = welcome_body["session_id"]

        deal_question = client.post(
            "/chat",
            json={"session_id": sid, "raw": {"budget_max": 200_000_000}},
        )
        assert deal_question.status_code == 200
        assert deal_question.json()["bot_messages"][0] == {
            "type": "bot.text",
            "content": "서울 실거래 데이터 기준으로 전세, 월세, 매매 중 어떤 거래를 볼까요?",
        }

        region_question = client.post(
            "/chat",
            json={"session_id": sid, "raw": {"deal_type": "jeonse"}},
        )
        assert region_question.status_code == 200
        assert region_question.json()["state"] == "asking"
        assert "희망하는 지역" in region_question.json()["bot_messages"][0]["content"]

        commute_question = client.post(
            "/chat",
            json={"session_id": sid, "raw": {"preferred_region": "마포구"}},
        )
        assert commute_question.status_code == 200
        assert "직장이나 자주 가는 곳" in commute_question.json()["bot_messages"][0]["content"]

        age_question = client.post(
            "/chat",
            json={"session_id": sid, "raw": {"workplace": "논현"}},
        )
        assert age_question.status_code == 200
        assert "연령층" in age_question.json()["bot_messages"][0]["content"]

        infra_question = client.post(
            "/chat",
            json={"session_id": sid, "raw": {"age_group": "young_adult"}},
        )
        assert infra_question.status_code == 200
        assert "주변 인프라" in infra_question.json()["bot_messages"][0]["content"]

        result = client.post(
            "/chat",
            json={"session_id": sid, "raw": {"infrastructure_priorities": ["transit"]}},
        )
        assert result.status_code == 200
        assert result.json()["state"] == "result"
        assert result.json()["bot_messages"][0]["type"] == "bot.text"
        assert "전세" in result.json()["bot_messages"][0]["content"]
        assert "추천 아파트" in result.json()["bot_messages"][0]["content"]


def test_chat_reaches_result_after_lifestyle_turns() -> None:
    """전세/매매는 예산, 거래유형, 생활 선호 답변 후 결과.

    turn 1 (자본금 칩) → 거래 유형 질문.
    turn 2 (거래 유형 칩, 전세) → 희망 지역 질문.
    turn 3-5 → 통근지/연령층/인프라 질문.
    turn 6 → 결과.
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
        assert turn2.json()["state"] == "asking"
        assert "희망하는 지역" in turn2.json()["bot_messages"][0]["content"]

        turn3 = client.post(
            "/chat",
            json={"session_id": sid, "raw": {"preferred_region": "상관없음"}},
        )
        assert turn3.status_code == 200
        assert turn3.json()["state"] == "asking"
        assert "직장이나 자주 가는 곳" in turn3.json()["bot_messages"][0]["content"]

        turn4 = client.post(
            "/chat",
            json={"session_id": sid, "raw": {"workplace": "상관없음"}},
        )
        assert turn4.status_code == 200
        assert "연령층" in turn4.json()["bot_messages"][0]["content"]

        turn5 = client.post(
            "/chat",
            json={"session_id": sid, "raw": {"age_group": "any"}},
        )
        assert turn5.status_code == 200
        assert "주변 인프라" in turn5.json()["bot_messages"][0]["content"]

        turn6 = client.post(
            "/chat",
            json={"session_id": sid, "raw": {"infrastructure_priorities": []}},
        )
        assert turn6.status_code == 200
        assert turn6.json()["state"] == "result"
        assert turn6.json()["bot_messages"][0]["type"] == "bot.text"
        assert "전세" in turn6.json()["bot_messages"][0]["content"]


def test_monthly_rent_flow_asks_rent_budget() -> None:
    """월세 선택 시 monthly_rent_max 추가 질문 → 생활 선호 확인 → 결과.

    turn 1 (자본금 칩) → 거래 유형 질문.
    turn 2 (월세 칩) → 월세 예산 질문.
    turn 3 (monthly_rent_max) → 희망 지역 질문.
    turn 4-6 → 통근지/연령층/인프라 질문.
    turn 7 → 결과.
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
            "content": "월세는 월 납입 상한도 필요해요. 매달 얼마까지 괜찮으신가요?",
        }

        turn3 = client.post(
            "/chat",
            json={"session_id": sid, "raw": {"monthly_rent_max": 800_000}},
        )
        assert turn3.status_code == 200
        assert turn3.json()["state"] == "asking"
        assert "희망하는 지역" in turn3.json()["bot_messages"][0]["content"]

        turn4 = client.post(
            "/chat",
            json={"session_id": sid, "raw": {"preferred_region": "상관없음"}},
        )
        assert turn4.status_code == 200
        assert "직장이나 자주 가는 곳" in turn4.json()["bot_messages"][0]["content"]

        turn5 = client.post(
            "/chat",
            json={"session_id": sid, "raw": {"workplace": "상관없음"}},
        )
        assert turn5.status_code == 200
        assert "연령층" in turn5.json()["bot_messages"][0]["content"]

        turn6 = client.post(
            "/chat",
            json={"session_id": sid, "raw": {"age_group": "any"}},
        )
        assert turn6.status_code == 200
        assert "주변 인프라" in turn6.json()["bot_messages"][0]["content"]

        turn7 = client.post(
            "/chat",
            json={"session_id": sid, "raw": {"infrastructure_priorities": []}},
        )
        assert turn7.status_code == 200
        assert turn7.json()["state"] == "result"
        assert "월세" in turn7.json()["bot_messages"][0]["content"]


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
            "content": "서울 실거래 데이터 기준으로 전세, 월세, 매매 중 어떤 거래를 볼까요?",
        }
