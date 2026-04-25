import { useCallback, useEffect, useMemo, useReducer, useRef } from "react";
import { ChatGatewayFactory, type ChatGateway } from "../api/chat";
import { IdFactory } from "../lib/idFactory";
import { UserInputParser } from "../lib/userInputParser";
import type { BotMessage, ChatMessage, ChatResponse, Conditions } from "../types/chat";

type ChatStatus = "idle" | "waiting" | "error";

type ChatState = {
  sessionId: string | null;
  messages: ChatMessage[];
  status: ChatStatus;
  lastRaw: Conditions | null;
  conditions: Conditions;
};

type ChatAction =
  | { type: "request"; raw: Conditions | null }
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
  conditions: {},
};

function chatReducer(state: ChatState, action: ChatAction): ChatState {
  switch (action.type) {
    case "request":
      return {
        ...state,
        status: "waiting",
        lastRaw: action.raw,
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

  userMessage(raw: Conditions, label: string, chipId?: string): ChatMessage {
    return {
      id: this.idFactory.next("user"),
      ts: Date.now(),
      role: "user",
      raw,
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

  const sendRaw = useCallback(
    async (raw: Conditions, userLabel?: string, chipId?: string) => {
      if (state.status === "waiting") {
        return;
      }

      dispatch({ type: "request", raw });

      if (userLabel) {
        dispatch({
          type: "user_message",
          message: messageFactory.userMessage(raw, userLabel, chipId),
        });
      }

      try {
        const response = await gateway.send({ session_id: state.sessionId, raw });
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

  const start = useCallback(() => sendRaw({}), [sendRaw]);

  const restart = useCallback(() => {
    hasBootstrappedRef.current = false;
    dispatch({ type: "reset" });
  }, []);

  const retry = useCallback(async () => {
    await sendRaw(state.lastRaw ?? {});
  }, [sendRaw, state.lastRaw]);

  const submitText = useCallback(
    async (input: string) => {
      try {
        const raw = inputParser.parse(state.conditions, input);
        await sendRaw(raw, input.trim());
      } catch {
        dispatch({
          type: "error",
          message: messageFactory.botMessage({
            type: "bot.text",
            content: state.conditions.budget_max
              ? "전세 또는 월세로 입력해주세요."
              : "숫자만 입력해주세요.",
          }),
        });
      }
    },
    [inputParser, messageFactory, sendRaw, state.conditions],
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
