package com.homefit.internal.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.homefit.chat.entity.ChatMessage;
import com.homefit.chat.repository.ChatMessageRepository;
import com.homefit.internal.dto.UpsertConditionsRequest;
import com.homefit.internal.dto.UpsertConditionsResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class ConditionHistoryService {

    private static final TypeReference<LinkedHashMap<String, Object>> MAP_TYPE = new TypeReference<>() {
    };

    private final ChatMessageRepository chatMessageRepository;
    private final InternalConditionValidator validator;
    private final ObjectMapper objectMapper;

    @Transactional
    public UpsertConditionsResponse upsert(UpsertConditionsRequest request) {
        String sessionId = resolveSessionId(request.sessionId());
        Map<String, Object> mergedConditions = loadLatestConditions(sessionId);
        mergedConditions.putAll(request.conditions());
        validator.validatePartial(mergedConditions);

        ChatMessage chatMessage = ChatMessage.create(
                sessionId,
                writeJson(request.raw()),
                writeJson(mergedConditions)
        );
        chatMessageRepository.save(chatMessage);

        return new UpsertConditionsResponse(sessionId, mergedConditions);
    }

    private String resolveSessionId(String sessionId) {
        if (sessionId == null || sessionId.isBlank()) {
            return UUID.randomUUID().toString();
        }

        try {
            return UUID.fromString(sessionId).toString();
        } catch (IllegalArgumentException exception) {
            throw new InvalidInternalApiRequestException("session_id must be a UUID.");
        }
    }

    private Map<String, Object> loadLatestConditions(String sessionId) {
        return chatMessageRepository.findTopBySessionIdOrderByCreatedAtDesc(sessionId)
                .map(ChatMessage::getConditions)
                .map(this::readJson)
                .orElseGet(LinkedHashMap::new);
    }

    private LinkedHashMap<String, Object> readJson(String json) {
        try {
            JsonNode node = objectMapper.readTree(json);
            if (node.isTextual()) {
                node = objectMapper.readTree(node.asText());
            }
            return objectMapper.convertValue(node, MAP_TYPE);
        } catch (JsonProcessingException exception) {
            throw new InvalidInternalApiRequestException("Stored conditions JSON is invalid.");
        }
    }

    private String writeJson(Map<String, Object> value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (JsonProcessingException exception) {
            throw new InvalidInternalApiRequestException("Request JSON is invalid.");
        }
    }
}
