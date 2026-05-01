package com.homefit.chat.backend.chat.repository;

import com.homefit.chat.backend.chat.entity.ChatMessage;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface ChatMessageRepository extends JpaRepository<ChatMessage, String> {

    Optional<ChatMessage> findTopBySessionIdOrderByCreatedAtDesc(String sessionId);
}
