const API_BASE_URL = import.meta.env.VITE_API_URL || "https://sahakar-sahayak-4.onrender.com";

export const chatService = {
  sendMessage: async (messageText, language = "en", conversationId = null) => {
    try {
      console.log("[API] POST /query");

      const response = await fetch(`${API_BASE_URL}/query`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          query: messageText,
          language: language,
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(
          `Backend error ${response.status}: ${errorText}`
        );
      }

      const data = await response.json();

      console.log("[API] Backend response:", data);

      return {
        answer: data.answer || "",
        steps: [],
        notes: [],
        provisions: [],
        documents: [],
        sources: (data.sources || []).map((source, index) => ({
          id: `${source.document}-${source.page}-${index}`,
          documentName: source.document,
          provision: source.page
            ? `Page ${source.page}`
            : "",
        })),
        suggestedQuestions: [],
        confidence: data.confidence,
        intent: data.intent,
        language: data.language,
      };
    } catch (error) {
      console.error("[API] Failed to send message:", error);
      throw error;
    }
  },
};