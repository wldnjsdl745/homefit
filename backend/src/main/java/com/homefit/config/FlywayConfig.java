package com.homefit.config;

import org.flywaydb.core.Flyway;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.autoconfigure.flyway.FlywayMigrationStrategy;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;

@Configuration
public class FlywayConfig {

    private static final Logger log = LoggerFactory.getLogger(FlywayConfig.class);

    @Bean
    public FlywayMigrationStrategy existingSchemaBaselineStrategy() {
        return flyway -> {
            if (hasExistingV3SchemaWithoutHistory(flyway)) {
                log.info("Existing Homefit schema detected without Flyway history. Baseline as version {}.",
                        flyway.getConfiguration().getBaselineVersion());
                flyway.baseline();
            }

            flyway.migrate();
        };
    }

    private boolean hasExistingV3SchemaWithoutHistory(Flyway flyway) {
        try (Connection connection = flyway.getConfiguration().getDataSource().getConnection()) {
            String schema = connection.getCatalog();
            if (schema == null || schema.isBlank()) {
                schema = connection.getSchema();
            }
            String historyTable = flyway.getConfiguration().getTable();

            if (tableExists(connection, schema, historyTable)) {
                return false;
            }

            return tableExists(connection, schema, "regions")
                    && tableExists(connection, schema, "housing_transactions")
                    && tableExists(connection, schema, "chat_messages")
                    && columnExists(connection, schema, "housing_transactions", "sale_price_amount");
        } catch (SQLException exception) {
            throw new IllegalStateException("Failed to inspect schema before Flyway migration.", exception);
        }
    }

    private boolean tableExists(Connection connection, String schema, String tableName) throws SQLException {
        String sql = """
                select count(*)
                from information_schema.tables
                where table_schema = ?
                  and table_name = ?
                """;
        try (PreparedStatement statement = connection.prepareStatement(sql)) {
            statement.setString(1, schema);
            statement.setString(2, tableName);
            try (ResultSet resultSet = statement.executeQuery()) {
                resultSet.next();
                return resultSet.getInt(1) > 0;
            }
        }
    }

    private boolean columnExists(
            Connection connection,
            String schema,
            String tableName,
            String columnName
    ) throws SQLException {
        String sql = """
                select count(*)
                from information_schema.columns
                where table_schema = ?
                  and table_name = ?
                  and column_name = ?
                """;
        try (PreparedStatement statement = connection.prepareStatement(sql)) {
            statement.setString(1, schema);
            statement.setString(2, tableName);
            statement.setString(3, columnName);
            try (ResultSet resultSet = statement.executeQuery()) {
                resultSet.next();
                return resultSet.getInt(1) > 0;
            }
        }
    }
}
