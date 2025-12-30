import { state } from './chatbot.state.js';
import { renderMessages, stopTypingIndicator} from './chatbot.dom.js';


let BACKEND_URL = null;
export function setBackendUrl(url) { BACKEND_URL = url; }


export async function startChat() {
    try {
        const resp = await fetch(`${BACKEND_URL}/chat/new`);
        const backend_result = await resp.json();

        state.chat_id = backend_result.id;
        state.data_var = backend_result.data;
        state.chatStarted = true;
        state.waitStart = null;

        // Show welcome/bot message if any in backend_result.message
        if (backend_result.message) {
            state.chatMessages.push({ sender: "bot", text: backend_result.message });
            state.botIsTyping = false; // <- remove spinner
            renderMessages();
        }

    } catch (e) {
        console.error("Error starting the chat:", e);
        state.chatMessages.push({ sender: "bot", text: "Es scheint, dass es gerade ein kleines Problem beim Start des Chats gibt. Ich versuche gerade, die Verbindung erneut herzustellen. Einen kleinen Moment bitte – wir sind gleich für Sie da. Vielen Dank für Ihre Geduld und Ihr Verständnis." });
        state.botIsTyping = true; // <- remove spinner
        renderMessages();
        return false;
    }
    return true;
}

export async function sendChatMessage(userEntry) {
    try {
        const resp = await fetch(`${BACKEND_URL}/chat/${state.chat_id}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                asked_info: state.asked_info,
                data: state.data_var,
                message: userEntry,
            })
        });

        const backend_result = await resp.json();
        state.final_message = backend_result.meta.final_message || false; // Check if we need to stop the chat after this message
        // Display backend message
        stopTypingIndicator()
        state.chatMessages.push({ sender: 'bot', text: backend_result.message });
        renderMessages();

        // Save session data for next steps
        state.chat_id = backend_result.id;
        state.data_var = backend_result.data;

    } catch (error) {
        console.error("Error occurred while sending the message:", error);
        state.chatMessages.push({ sender: 'bot', text: "Der Chat braucht gerade noch einen kleinen Moment, um zu starten. Ich versuche die Verbindung nochmal herzustellen – danke für Ihre Geduld, wir sind gleich für Sie da!" });
        stopTypingIndicator()
        renderMessages();
        return false;
    }
    return true;
}


