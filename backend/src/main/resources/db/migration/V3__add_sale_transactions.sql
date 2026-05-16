ALTER TABLE housing_transactions
    ADD COLUMN sale_price_amount BIGINT NULL;

ALTER TABLE housing_transactions
    DROP CONSTRAINT chk_housing_transactions_deal_type;

ALTER TABLE housing_transactions
    ADD CONSTRAINT chk_housing_transactions_deal_type
        CHECK (deal_type IN ('jeonse', 'monthly_rent', 'sale'));

CREATE INDEX idx_housing_transactions_deal_type_sale_price_amount
    ON housing_transactions (deal_type, sale_price_amount);
