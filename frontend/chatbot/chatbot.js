import { renderMessages, startTypingIndicator, stopTypingIndicator, setFrontendUrl, setupPrivacyOverlay } from './chatbot.dom.js';
import { state, loadChatbotSession, saveChatbotSession } from './chatbot.state.js';
import { startChat, sendChatMessage, setBackendUrl } from './chatbot.api.js';
// Chat sending logic

const form = document.getElementById('chatbot-form');
const input = document.getElementById('chatbot-input');

loadChatbotSession();

window.startNewChatIfNeeded = async function (frontendUrl, backendUrl) {
    setFrontendUrl(frontendUrl);
    setBackendUrl(backendUrl);
    if (state.chatStarted) return; // Do not start a new chat if already started
    renderMessages(); // Initial render to show loading state
    // add async functions to re-run if error occurs
    let success = await startChat();
    // Try 3 times to startChat, if the 3rd time still could not connect, ask user to refresh page
    if (!success) {
        success = await startChat();
        if (!success) {
            success = await startChat();
            if (!success) {
                state.chatMessages.push({ sender: "bot", text: "Entschuldigung, ich konnte leider keine Verbindung aufbauen. Bitte laden Sie die Seite neu und versuchen Sie es noch einmal." });
                renderMessages();
            }
        }
    }
    saveChatbotSession(); // Save state after starting chat
}

// Handle submit
form.addEventListener('submit', async function (e) {
    e.preventDefault();
    const userEntry = input.value.trim();
    if (!userEntry) return;
    state.chatMessages.push({ sender: 'user', text: userEntry });
    renderMessages();
    startTypingIndicator()
    input.value = '';
    if (!state.chat_id) {
        stopTypingIndicator()
        state.chatMessages.push({ sender: "bot", text: "Chatverbindung nicht hergestellt." });
        //state.botIsTyping = false; // <- remove spinner
        //renderMessages();
        return;
    }
    let success = await sendChatMessage(userEntry);
    if (!success) {
        success = await sendChatMessage(userEntry);
        if (!success) {
            success = await sendChatMessage(userEntry);
            if (!success) {
                state.chatMessages.push({ sender: 'bot', text: "Es hat mit der Verbindung leider nicht ganz geklappt. Ein kurzes Neuladen der Seite hilft meistens – bitte versuchen Sie es einmal." });
                renderMessages();
            }
        }
    }
    saveChatbotSession(); // Save state after sending message
});

// Allow pressing Enter to send
input.addEventListener('keydown', e => {
    if ((e.key === 'Enter' || e.keyCode === 13) && input.value.trim() && !state.botIsTyping) {
        e.preventDefault();
        form.requestSubmit();
    }
});

// Hide button logic
document.querySelector('.chatbot-hide').onclick = function () {
    document.getElementById('chatbot-widget').style.display = 'none';
};

if (document.getElementById('chatbot-privacy-overlay')) {
    setupPrivacyOverlay();
}
