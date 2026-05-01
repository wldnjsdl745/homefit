package com.homefit.chat.backend.chat.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.PrePersist;
import jakarta.persistence.Table;
import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;
import java.util.UUID;

@Entity
@Table(name = "chat_messages")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class ChatMessage {

    @Id
    @Column(name = "id", nullable = false, length = 36)
    private String id;

    @Column(name = "session_id", nullable = false, length = 36)
    private String sessionId;

    @Column(name = "raw", nullable = false, columnDefinition = "json")
    private String raw;

    @Column(name = "conditions", nullable = false, columnDefinition = "json")
    private String conditions;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @Builder
    private ChatMessage(String sessionId, String raw, String conditions) {
        this.sessionId = sessionId;
        this.raw = raw;
        this.conditions = conditions;
    }

    public static ChatMessage create(String sessionId, String raw, String conditions) {
        return new ChatMessage(sessionId, raw, conditions);
    }

    @PrePersist
    void prePersist() {
        if (id == null) {
            id = UUID.randomUUID().toString();
        }

        if (sessionId == null) {
            sessionId = UUID.randomUUID().toString();
        }
    }
}
