
export function escapeHTML(text) {
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

export function cleanLink(url) {
    if (typeof url !== 'string') return '';
    let s = url.trim();

    // 2) "/." oder "/.." oder mehrfach davon am Ende → auf genau "/" reduzieren
    s = s.replace(/(?:\/\.\.?)+$/u, '/');

    // 3) Alle übrigen unerwünschten End-Zeichen (Klammern, Anführungen, Satzzeichen, Dashes) wegsäubern
    s = s.replace(/(?:[)"'\]}>›»]+|[.,;:!?…]+|[—–-]+)+$/u, '');

    // 4) Nochmals abschließende Leerzeichen (inkl. NBSP) entfernen und zurückgeben
    return s.replace(/[\s\u00A0]+$/u, '');
}

export function renderMarkdown(text) {
    let t = text.replace(/\[([^\]]+)\]\(mailto:([^)]+)\)/gi, "$2");
    t = t.replace(/(\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b)(.{0,4})\1/g, "$1");
    let html = escapeHTML(t);

    html = html.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/gi, '<a href="$2" target="_blank">$1</a>');
    html = html.replace(/(\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b)/g, '<a href="mailto:$1">$1</a>');
    html = html.replace(/\*\*(.*?)\*\*/g, "<b>$1</b>");
    html = html.replace(/__(.*?)__/g, "<b>$1</b>");
    html = html.replace(/(\s|\A)\*(?!\*)([^\*]+)\*/g, "$1<i>$2</i>");
    html = html.replace(/(\s|\A)_(?!_)([^_]+)_/g, "$1<i>$2</i>");
    html = html.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank">$1</a>');
    html = html.replace(/^\* (.*)$/gm, "&bull; $1");
    html = html.replace(/(^|\s)(www\.[^\s<]+)/g, function (match, space, url) {
        url = cleanLink(url)
        return space + '<a href="http://' + url + '" target="_blank" rel="noopener noreferrer">' + url + '  </a>';
    });
    html = html.replace(/(^|\s)((https?:\/\/)[^\s<]+)/g, function (match, space, url) {
        url = cleanLink(url)
        return space + '<a href="' + url + '" target="_blank" rel="noopener noreferrer">' + url + '  </a>';
    });
    html = html.replace(/\n/g, "<br>");
    return html;
}


/**
* Splits text into subblocks
*  - always splits on "\n\n", when next char is A–Z
*  - if text is longer than maxLen and no natural splits, it will chunk at
*    the nearest newline/space before maxLen
*/
export function splitIntoSubblocks(text, maxLen = 1000) {
    // 1) first try to split on double-newline + upper-case
    let parts = text.split(/\n{2}(?=[A-Z])/);

    // 2) if still one big blob and it’s too long, chunk it
    if (parts.length === 1 && text.length > maxLen) {
        parts = [];
        let cursor = 0;
        while (cursor < text.length) {
            let next = Math.min(text.length, cursor + maxLen);
            // try to break at last newline or space before next
            const snippet = text.slice(cursor, next);
            const sep = Math.max(snippet.lastIndexOf('\n'), snippet.lastIndexOf(". "));
            if (sep > -1) {
                parts.push(text.slice(cursor, cursor + sep));
                cursor += sep + 1;
            } else {
                // no separator found, hard split
                parts.push(snippet);
                cursor = next;
            }
        }
    }

    // remove any empty
    return parts.filter(p => p.trim().length);
};


const msgList = [
    "Almost done—thank you for your patience.",
    "One moment please—I'm looking for the answer.",
    "Please wait a moment, I'll be right back.",
    "One moment, I'll be right back.",
    "One moment, I'll check that for you quickly,",
    "I'll be right back, thank you for your patience!",
    "I'll check that for you quickly,",
    "I'll just check, one moment please,",
    "Just a moment, I'll find the answer for you.",
    "One second—I'll try to find out.",
    "Almost done—thank you for your patience.",
    "I'll check that—please wait a moment.",
    "One second please—I'm still looking.",
    "One moment please...",
    "Just a moment please...",
    "Please wait a moment...",
    "I'm still checking...",
    "I'll be right back...",
    "Just a moment..."
];

export function randomFallback() {
    return `${msgList[Math.floor(Math.random() * msgList.length)]}
            ${dotWaitMsgHTML}
        `
}

// Insert SendIcon into response space
export function showSendIcon(frontendUrl) {
    const btn = document.querySelector('.chatbot-send');
    const Wait = `${frontendUrl}/assets/bot_wait.svg`;
    const Send = `${frontendUrl}/assets/bot_send.svg`;
    if (!btn) return;

    let icon = btn.querySelector('.icon');
    if (!icon) {
        icon = new Image();
        icon.className = 'icon';
        icon.alt = '';
        btn.appendChild(icon);
    }

    if (btn && !btn.dataset.iconInjected) {
        icon.src = Wait;
        btn.dataset.iconInjected = '1';

        btn.addEventListener('mouseenter', () => {
            icon.src = Send;
        });

        btn.addEventListener('mouseleave', () => {
            icon.src = Wait;
        });
    }

}

export const dotWaitMsgHTML = `
            <div class="bot-text chatbot-typing-indicator">
                <span class="typing-dot"></span>
                <span class="typing-dot"></span>
                <span class="typing-dot"></span>
            </div>
            ` ;