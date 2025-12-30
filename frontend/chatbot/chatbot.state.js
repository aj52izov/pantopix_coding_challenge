// chatbot.state.js

export let state = {
    chat_id: null,
    asked_info: null,
    data_var: null,
    chatStarted: false,
    privacyAccepted: false,
    final_message: null,
    chatMessages: [],
    botIsTyping: true,
    waitStart: null,
    fallbackTimer: null
};

export function saveChatbotSession() {
    sessionStorage.setItem('chatbotState', JSON.stringify(state));
}

export function loadChatbotSession() {
    const saved = JSON.parse(sessionStorage.getItem('chatbotState') || '{}');
    Object.assign(state, saved);
    if (!('botIsTyping' in saved)) {
        state.botIsTyping = state.chatMessages.length === 0;
    }
}