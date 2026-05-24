export type DealType = "monthly_rent" | "jeonse" | "sale";

export type CommuteDestination = "gangnam" | "yeouido" | "gwanghwamun" | "hongdae" | "jamsil";

export type Conditions = {
  budget_max?: number;
  deal_type?: DealType;
  monthly_rent_max?: number;
  commute_destination?: CommuteDestination;
  commute_skipped?: boolean;
  preference_text?: string;
};

export type ChatRequest = {
  session_id?: string | null;
  raw: Conditions;
  raw_message?: string | null;
};

export type ChatState = "asking" | "result";

export type QuickReplyChip = {
  id: string;
  label: string;
};

export type BotMessage =
  | { type: "bot.text"; content: string }
  | { type: "bot.quick_replies"; chips: QuickReplyChip[] };

export type ChatResponse = {
  session_id: string;
  state: ChatState;
  bot_messages: BotMessage[];
};

export type ChatMessage =
  | {
      id: string;
      ts: number;
      role: "user";
      raw: Conditions;
      rawMessage?: string;
      label: string;
      chipId?: string;
    }
  | {
      id: string;
      ts: number;
      role: "bot";
      body: BotMessage;
    };
