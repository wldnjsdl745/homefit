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
                                  "raw": { "budget_max": null, "deal_type": "jeonse" },
                                  "conditions": { "budget_max": null, "deal_type": "jeonse" }
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.session_id").value(sessionId))
                .andExpect(jsonPath("$.conditions.budget_max").value(200000000))
                .andExpect(jsonPath("$.conditions.deal_type").value("jeonse"));
    }

    @Test
    void filterReturnsTopThreeSeoulApartmentRegionsWithinBudgetInManwon() throws Exception {
        long mapo = insertRegion("서울특별시", "11440", "마포구", "001", "공덕동");
        long seongdong = insertRegion("서울특별시", "11200", "성동구", "002", "옥수동");
        long gwangjin = insertRegion("서울특별시", "11215", "광진구", "003", "자양동");
        long yongsan = insertRegion("서울특별시", "11170", "용산구", "004", "한남동");

        insertTransactions(mapo, "jeonse", 10_000L, "마포래미안", 3);
        insertTransactions(seongdong, "jeonse", 15_000L, "옥수파크힐스", 2);
        insertTransactions(gwangjin, "jeonse", 18_000L, "자양현대", 1);
        insertTransactions(yongsan, "jeonse", 90_000L, "한남더힐", 5);
        insertTransactions(mapo, "monthly_rent", 5_000L, "마포래미안", 5);

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
                .andExpect(jsonPath("$.regions[0]").value("마포구"))
                .andExpect(jsonPath("$.regions[1]").value("성동구"))
                .andExpect(jsonPath("$.regions[2]").value("광진구"))
                .andExpect(jsonPath("$.apartments", hasSize(3)))
                .andExpect(jsonPath("$.apartments[0].name").value("마포래미안"));
    }

    @Test
    void filterSaleUsesSalePriceAmountWithinBudgetInManwon() throws Exception {
        long gangnam = insertRegion("서울특별시", "11680", "강남구", "001", "역삼동");
        long mapo = insertRegion("서울특별시", "11440", "마포구", "002", "공덕동");
        long yongsan = insertRegion("서울특별시", "11170", "용산구", "003", "한남동");

        insertSaleTransactions(gangnam, 15_000L, "역삼래미안", 3);
        insertSaleTransactions(mapo, 18_000L, "공덕자이", 2);
        insertSaleTransactions(yongsan, 90_000L, "한남더힐", 5);

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
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.regions", hasSize(2)))
                .andExpect(jsonPath("$.regions[0]").value("강남구"))
                .andExpect(jsonPath("$.regions[1]").value("마포구"))
                .andExpect(jsonPath("$.apartments", hasSize(2)))
                .andExpect(jsonPath("$.apartments[0].name").value("역삼래미안"));
    }

    @Test
    void filterFallsBackToLegalDongWhenBuildingNameIsMissing() throws Exception {
        long mapo = insertRegion("서울특별시", "11440", "마포구", "001", "공덕동");
        long seongdong = insertRegion("서울특별시", "11200", "성동구", "002", "옥수동");
        long yongsan = insertRegion("서울특별시", "11170", "용산구", "003", "한남동");

        insertTransactionsWithoutBuildingName(mapo, "jeonse", 10_000L, 3);
        insertTransactionsWithoutBuildingName(seongdong, "jeonse", 15_000L, 2);
        insertTransactionsWithoutBuildingName(yongsan, "jeonse", 90_000L, 5);

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
                .andExpect(jsonPath("$.regions", hasSize(2)))
                .andExpect(jsonPath("$.apartments", hasSize(2)))
                .andExpect(jsonPath("$.apartments[0].name").doesNotExist());
    }

    @Test
    void invalidDealTypeReturnsBadRequest() throws Exception {
        mockMvc.perform(post("/internal/filter")
                        .contentType(APPLICATION_JSON)
                        .content("""
                                {
                                  "conditions": {
                                    "budget_max": 200000000,
                                    "deal_type": "banse"
                                  }
                                }
                                """))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.detail").value("conditions.deal_type must be jeonse, monthly_rent, or sale."));
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

    private void insertTransactions(
            long regionId,
            String dealType,
            long depositAmount,
            String buildingName,
            int count
    ) {
        for (int i = 0; i < count; i++) {
            jdbcTemplate.update("""
                            insert into housing_transactions (
                              region_id, deal_type, deposit_amount, monthly_rent, contract_date,
                              building_name, rental_area, built_year
                            )
                            values (?, ?, ?, null, date '2026-04-25', ?, 59.40, 2015)
                            """,
                    regionId,
                    dealType,
                    depositAmount,
                    buildingName
            );
        }
    }

    private void insertSaleTransactions(long regionId, long salePriceAmount, String buildingName, int count) {
        for (int i = 0; i < count; i++) {
            jdbcTemplate.update("""
                            insert into housing_transactions (
                              region_id, deal_type, sale_price_amount, deposit_amount, monthly_rent, contract_date,
                              building_name, rental_area, built_year
                            )
                            values (?, 'sale', ?, null, null, date '2026-04-25', ?, 84.90, 2018)
                            """,
                    regionId,
                    salePriceAmount,
                    buildingName
            );
        }
    }

    private void insertTransactionsWithoutBuildingName(
            long regionId,
            String dealType,
            long depositAmount,
            int count
    ) {
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
