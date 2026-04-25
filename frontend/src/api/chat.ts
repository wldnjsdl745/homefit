import { ApiClient } from "./client";
import { MockChatServer } from "../mocks/MockChatServer";
import type { ChatRequest, ChatResponse } from "../types/chat";

export interface ChatGateway {
  send(request: ChatRequest): Promise<ChatResponse>;
}

export class RemoteChatGateway implements ChatGateway {
  constructor(private readonly client: ApiClient) {}

  send(request: ChatRequest): Promise<ChatResponse> {
    return this.client.post<ChatRequest, ChatResponse>("/chat", request);
  }
}

export class MockChatGateway implements ChatGateway {
  constructor(private readonly server = new MockChatServer()) {}

  send(request: ChatRequest): Promise<ChatResponse> {
    return this.server.handle(request);
  }
}

export class ChatGatewayFactory {
  static create(): ChatGateway {
    const useMock = import.meta.env.VITE_USE_MOCK_CHAT !== "false";

    if (useMock) {
      return new MockChatGateway();
    }

    const baseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
    return new RemoteChatGateway(new ApiClient(baseUrl));
  }
}
