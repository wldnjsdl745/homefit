import { useCallback, useEffect, useMemo, useReducer, useRef } from "react";
import { ChatGatewayFactory, type ChatGateway } from "../api/chat";
import { IdFactory } from "../lib/idFactory";
import { UserInputParser } from "../lib/userInputParser";
import type { BotMessage, ChatMessage, ChatRequest, ChatResponse, Conditions } from "../types/chat";

type ChatStatus = "idle" | "waiting" | "error";

type ChatState = {
  sessionId: string | null;
  messages: ChatMessage[];
  status: ChatStatus;
  lastRaw: Conditions | null;
  lastRawMessage: string | null;
  conditions: Conditions;
};

type ChatAction =
  | { type: "request"; raw: Conditions | null; rawMessage?: string | null }
  | { type: "user_message"; message: ChatMessage }
  | { type: "response_meta"; response: ChatResponse }
  | { type: "bot_message"; message: ChatMessage; done: boolean }
  | { type: "error"; message: ChatMessage }
  | { type: "reset" };

const initialState: ChatState = {
  sessionId: null,
  messages: [],
  status: "idle",
  lastRaw: null,
  lastRawMessage: null,
  conditions: {},
};

function chatReducer(state: ChatState, action: ChatAction): ChatState {
  switch (action.type) {
    case "request":
      return {
        ...state,
        status: "waiting",
        lastRaw: action.raw,
        lastRawMessage: action.rawMessage ?? null,
        conditions: action.raw ? { ...state.conditions, ...action.raw } : state.conditions,
      };
    case "user_message":
      return { ...state, messages: [...state.messages, action.message] };
    case "response_meta":
      return {
        ...state,
        sessionId: action.response.session_id,
      };
    case "bot_message":
      return {
        ...state,
        messages: [...state.messages, action.message],
        status: action.done ? "idle" : "waiting",
      };
    case "error":
      return {
        ...state,
        messages: [...state.messages, action.message],
        status: "error",
      };
    case "reset":
      return initialState;
    default:
      return state;
  }
}

export class ChatMessageFactory {
  constructor(private readonly idFactory = new IdFactory()) {}

  botMessages(messages: BotMessage[]): ChatMessage[] {
    return messages.map((body) => ({
      id: this.idFactory.next("bot"),
      ts: Date.now(),
      role: "bot" as const,
      body,
    }));
  }

  botMessage(body: BotMessage): ChatMessage {
    return {
      id: this.idFactory.next("bot"),
      ts: Date.now(),
      role: "bot",
      body,
    };
  }

  userMessage(raw: Conditions, label: string, rawMessage?: string, chipId?: string): ChatMessage {
    return {
      id: this.idFactory.next("user"),
      ts: Date.now(),
      role: "user",
      raw,
      rawMessage,
      label,
      chipId,
    };
  }

  errorMessage(): ChatMessage {
    return {
      id: this.idFactory.next("bot"),
      ts: Date.now(),
      role: "bot",
      body: {
        type: "bot.text",
        content: "잠시 문제가 있어요. 다시 추천을 받아볼까요?",
      },
    };
  }
}

class BotMessageSequencer {
  constructor(private readonly delayMs = 420) {}

  async play(messages: BotMessage[], append: (message: BotMessage, done: boolean) => void) {
    for (let index = 0; index < messages.length; index += 1) {
      if (index > 0) {
        await this.delay();
      }

      append(messages[index], index === messages.length - 1);
    }
  }

  private delay(): Promise<void> {
    return new Promise((resolve) => window.setTimeout(resolve, this.delayMs));
  }
}

type UseChatOptions = {
  gateway?: ChatGateway;
  inputParser?: UserInputParser;
  messageFactory?: ChatMessageFactory;
  sequencer?: BotMessageSequencer;
};

export function useChat(options: UseChatOptions = {}) {
  const gateway = useMemo(() => options.gateway ?? ChatGatewayFactory.create(), [options.gateway]);
  const inputParser = useMemo(
    () => options.inputParser ?? new UserInputParser(),
    [options.inputParser],
  );
  const messageFactory = useMemo(
    () => options.messageFactory ?? new ChatMessageFactory(),
    [options.messageFactory],
  );
  const sequencer = useMemo(
    () => options.sequencer ?? new BotMessageSequencer(),
    [options.sequencer],
  );
  const [state, dispatch] = useReducer(chatReducer, initialState);
  const hasBootstrappedRef = useRef(false);

  const sendRequest = useCallback(
    async (
      request: Pick<ChatRequest, "raw" | "raw_message">,
      userLabel?: string,
      chipId?: string,
    ) => {
      if (state.status === "waiting") {
        return;
      }

      dispatch({ type: "request", raw: request.raw, rawMessage: request.raw_message });

      if (userLabel) {
        dispatch({
          type: "user_message",
          message: messageFactory.userMessage(
            request.raw,
            userLabel,
            request.raw_message ?? undefined,
            chipId,
          ),
        });
      }

      try {
        const response = await gateway.send({
          session_id: state.sessionId,
          raw: request.raw,
          raw_message: request.raw_message,
        });
        dispatch({ type: "response_meta", response });
        await sequencer.play(response.bot_messages, (botMessage, done) => {
          dispatch({
            type: "bot_message",
            message: messageFactory.botMessage(botMessage),
            done,
          });
        });
      } catch {
        dispatch({ type: "error", message: messageFactory.errorMessage() });
      }
    },
    [gateway, messageFactory, sequencer, state.sessionId, state.status],
  );

  const start = useCallback(() => sendRequest({ raw: {} }), [sendRequest]);

  const restart = useCallback(() => {
    hasBootstrappedRef.current = false;
    dispatch({ type: "reset" });
  }, []);

  const retry = useCallback(async () => {
    await sendRequest({
      raw: state.lastRaw ?? {},
      raw_message: state.lastRawMessage,
    });
  }, [sendRequest, state.lastRaw, state.lastRawMessage]);

  const submitText = useCallback(
    async (input: string) => {
      const parsed = inputParser.parse(state.conditions, input);
      await sendRequest(parsed, input.trim());
    },
    [inputParser, sendRequest, state.conditions],
  );

  useEffect(() => {
    if (!hasBootstrappedRef.current && state.messages.length === 0 && state.status === "idle") {
      hasBootstrappedRef.current = true;
      void start();
    }
  }, [start, state.messages.length, state.status]);

  return {
    messages: state.messages,
    isWaiting: state.status === "waiting",
    hasError: state.status === "error",
    submitText,
    restart,
    retry,
  };
}
