import { renderMarkdown, splitIntoSubblocks, dotWaitMsgHTML, randomFallback, showSendIcon} from './chatbot.util.js';
import { state, saveChatbotSession } from './chatbot.state.js';

let FRONTEND_URL = null;
export function setFrontendUrl(url) { FRONTEND_URL = url; }

// Simple renderer
export function renderMessages() {
    const form = document.getElementById('chatbot-form');
    const input = document.getElementById('chatbot-input');
    const messages = document.getElementById('chatbot-messages');
    document.getElementById('chatbot-widget').style.display = 'block';
    // Clear previous messages 
    messages.innerHTML = '';
    state.chatMessages.forEach(msg => {
        if (msg.sender === 'user') {
            // User message (right-align, no avatar)
            const div = document.createElement('div');
            div.className = 'chatbot-msg-user';
            div.textContent = msg.text;
            messages.appendChild(div);
        } else {
            // Bot message (with avatar)
            const blocks = splitIntoSubblocks(msg.text, 500);
            blocks.forEach(block => {
                const div = document.createElement('div');
                div.className = 'chatbot-msg-bot';
                div.innerHTML = `
                <div class="bot-avatar">
                    <img src="https://media.licdn.com/dms/image/v2/C4D0BAQH5Uea-p8mKfA/company-logo_200_200/company-logo_200_200/0/1630563514541/pantopix_gmbh__co_kg_logo?e=2147483647&v=beta&t=1a2yk8CtebJ7bkBi-Y1h1a-VOCuv7yMjjOuzEwf-EhU" />
                </div>
                <div class="bot-text">${renderMarkdown(block)}</div>
                `;
                messages.appendChild(div);
            });
        }
    });
    if (state.botIsTyping) {
        if (!state.waitStart) state.waitStart = Date.now();
        input.disabled = true;
        form.querySelector('button[type="submit"]').disabled = true;
        const div = document.createElement('div');
        div.className = 'chatbot-msg-bot';
        const waitTime = Date.now() - state.waitStart;
        let waitMsgHTML = '';
        if (waitTime > 8000) {
            waitMsgHTML = randomFallback();
        } else {
            waitMsgHTML = dotWaitMsgHTML;
        }
        div.innerHTML = `
            <div class="bot-avatar">
                <img src="https://media.licdn.com/dms/image/v2/C4D0BAQH5Uea-p8mKfA/company-logo_200_200/company-logo_200_200/0/1630563514541/pantopix_gmbh__co_kg_logo?e=2147483647&v=beta&t=1a2yk8CtebJ7bkBi-Y1h1a-VOCuv7yMjjOuzEwf-EhU"/>
            </div>
            ${waitMsgHTML}
        `;
        messages.appendChild(div);
    }
    else {
        state.waitStart = null
        input.disabled = false;
        form.querySelector('button[type="submit"]').disabled = false;
    }
    //messages.scrollTop = messages.scrollHeight;
    // grab *all* the user‐message nodes
    const userMsgs = messages.querySelectorAll('.chatbot-msg-user');
    if (userMsgs.length) {
        // pick the very last one
        const lastUser = userMsgs[userMsgs.length - 1];
        lastUser.scrollIntoView({
            behavior: 'auto', // or 'smooth'
            block: 'start'
        });
    }

    // If final message is set, make textArea not editable and the form not submitable
    if (state.final_message) {
        input.disabled = true;
        form.querySelector('button[type="submit"]').disabled = true;
        input.placeholder = "Chat beendet. Vielen Dank für Ihre Anfrage!";
        // Optionally hide the form
        //form.style.display = 'none';
    }

    showSendIcon(FRONTEND_URL);
    // Save state after rendering
    saveChatbotSession();
}


export function startTypingIndicator() {
    state.botIsTyping = true
    state.waitStart = null;
    renderMessages() // shows the spinner immediately

    state.fallbackTimer = setTimeout(() => {
        if (state.botIsTyping) {
            // replace spinner with fallback
            document.querySelector('.chatbot-msg-bot .chatbot-typing-indicator')
                .outerHTML = `<div class="text">${randomFallback()}</div>`
        }
    }, 8000)
}

export function stopTypingIndicator() {
    state.botIsTyping = false
    clearTimeout(state.fallbackTimer)
    state.waitStart = null;
    renderMessages() // show the real bot message
}

export function setupPrivacyOverlay() {
    const overlay = document.getElementById('chatbot-privacy-overlay');
    const acceptBtn = document.getElementById('accept-privacy-btn');
    const messages = document.getElementById('chatbot-messages');
    const form = document.getElementById('chatbot-form');
    // Hide chat UI until accepted
    if (!state.privacyAccepted) {
        messages.style.display = "none";
        form.style.display = "none";
        overlay.style.display = "flex";
    }

    acceptBtn.onclick = () => {
        overlay.style.display = "none";
        messages.style.display = "flex";
        form.style.display = "flex";
        state.privacyAccepted = true;
        // If backend is already ready, display welcome
        renderMessages();
    };
    // Save state
    saveChatbotSession();
}


