package com.homefit;

import com.homefit.chat.repository.ChatMessageRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.web.servlet.MockMvc;

import static org.hamcrest.Matchers.hasSize;
import static org.hamcrest.Matchers.matchesPattern;
import static org.springframework.http.MediaType.APPLICATION_JSON;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
class InternalApiTests {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ChatMessageRepository chatMessageRepository;

    @Autowired
    private JdbcTemplate jdbcTemplate;

    @BeforeEach
    void setUp() {
        chatMessageRepository.deleteAll();
        jdbcTemplate.update("delete from housing_transactions");
        jdbcTemplate.update("delete from regions");
    }

    @Test
    void upsertConditionsCreatesSessionAndStoresMessage() throws Exception {
        mockMvc.perform(post("/internal/upsert-conditions")
                        .contentType(APPLICATION_JSON)
                        .content("""
                                {
                                  "session_id": null,
                                  "raw": { "budget_max": 200000000 },
                                  "conditions": { "budget_max": 200000000 }
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.session_id", matchesPattern(
                        "^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
                )))
                .andExpect(jsonPath("$.conditions.budget_max").value(200000000));

        org.assertj.core.api.Assertions.assertThat(chatMessageRepository.count()).isEqualTo(1);
    }

    @Test
    void upsertConditionsMergesWithLatestSessionConditions() throws Exception {
        String sessionId = "f44dfd4a-3d58-4f69-9c93-6b669e7d5e9f";

        mockMvc.perform(post("/internal/upsert-conditions")
                        .contentType(APPLICATION_JSON)
                        .content("""
                                {
                                  "session_id": "f44dfd4a-3d58-4f69-9c93-6b669e7d5e9f",
                                  "raw": { "budget_max": 200000000 },
                                  "conditions": { "budget_max": 200000000 }
                                }
                                """))
                .andExpect(status().isOk());

        mockMvc.perform(post("/internal/upsert-conditions")
                        .contentType(APPLICATION_JSON)
                        .content("""
                                {
                                  "session_id": "f44dfd4a-3d58-4f69-9c93-6b669e7d5e9f",
                                  "raw": { "deal_type": "jeonse" },
                                  "conditions": { "deal_type": "jeonse" }
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.session_id").value(sessionId))
                .andExpect(jsonPath("$.conditions.budget_max").value(200000000))
                .andExpect(jsonPath("$.conditions.deal_type").value("jeonse"));
    }

    @Test
    void filterReturnsTopThreeRegionsByTransactionCount() throws Exception {
        long bundang = insertRegion("경기도", "41135", "분당", "001", "정자동");
        long seongnam = insertRegion("경기도", "41131", "성남", "002", "태평동");
        long suwon = insertRegion("경기도", "41111", "수원", "003", "매탄동");
        long yongsan = insertRegion("서울특별시", "11170", "용산", "004", "한남동");

        insertTransactions(bundang, "jeonse", 100_000_000L, 3);
        insertTransactions(seongnam, "jeonse", 150_000_000L, 2);
        insertTransactions(suwon, "jeonse", 180_000_000L, 1);
        insertTransactions(yongsan, "jeonse", 900_000_000L, 5);
        insertTransactions(bundang, "monthly_rent", 50_000_000L, 5);

        mockMvc.perform(post("/internal/filter")
                        .contentType(APPLICATION_JSON)
                        .content("""
                                {
                                  "conditions": {
                                    "budget_max": 200000000,
                                    "deal_type": "jeonse"
                                  }
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.regions", hasSize(3)))
                .andExpect(jsonPath("$.regions[0]").value("분당"))
                .andExpect(jsonPath("$.regions[1]").value("성남"))
                .andExpect(jsonPath("$.regions[2]").value("수원"));
    }

    @Test
    void invalidDealTypeReturnsBadRequest() throws Exception {
        mockMvc.perform(post("/internal/filter")
                        .contentType(APPLICATION_JSON)
                        .content("""
                                {
                                  "conditions": {
                                    "budget_max": 200000000,
                                    "deal_type": "sale"
                                  }
                                }
                                """))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.detail").value("conditions.deal_type must be jeonse or monthly_rent."));
    }

    @Test
    void healthzIsPublic() throws Exception {
        mockMvc.perform(get("/healthz"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("UP"));
    }

    private long insertRegion(
            String sido,
            String sigunguCode,
            String sigungu,
            String legalDongCode,
            String legalDongName
    ) {
        jdbcTemplate.update("""
                        insert into regions (
                          sido, sigungu_code, sigungu, legal_dong_code, legal_dong_name
                        )
                        values (?, ?, ?, ?, ?)
                        """,
                sido,
                sigunguCode,
                sigungu,
                legalDongCode,
                legalDongName
        );
        return jdbcTemplate.queryForObject("select max(id) from regions", Long.class);
    }

    private void insertTransactions(long regionId, String dealType, long depositAmount, int count) {
        for (int i = 0; i < count; i++) {
            jdbcTemplate.update("""
                            insert into housing_transactions (
                              region_id, deal_type, deposit_amount, monthly_rent, contract_date
                            )
                            values (?, ?, ?, null, date '2026-04-25')
                            """,
                    regionId,
                    dealType,
                    depositAmount
            );
        }
    }
}
