import type { BotMessage } from "../types/chat";

export class MessageRenderer {
  getText(message: BotMessage): string {
    if (message.type === "bot.text") {
      return message.content;
    }

    return message.chips.map((chip) => chip.label).join(", ");
  }
}
