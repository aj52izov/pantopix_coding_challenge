(function () {

    var me = document.currentScript || (function(){
        var s = document.getElementsByTagName('script');
        return s[s.length-1];
      })();
    
    // pull the URL from the data-attribute
    const frontendUrl =  me.getAttribute('chatbot_url')
    const backendUrl =  me.getAttribute('backend-url')

    // Chatbot CSS
    var style = document.createElement('link');
    style.rel = 'stylesheet';
    style.href = `${frontendUrl}/chatbot.css`;
    style.id = 'chatbot-style';
    document.head.appendChild(style);

    // Chatbot Button
    if (!document.getElementById('open-chat-btn')) {
        var btn = document.createElement('button');
        btn.id = 'open-chat-btn';
        btn.title = 'Chat with us!';

        var img = new Image();
        img.src = `${frontendUrl}/assets/chatbot.svg`;     
        img.alt = '';
        //img.width = 35;
        //img.height = 35;
        //img.style.borderRadius = "30%";
        //img.style.overflow = "hidden";
        //img.style.boxShadow = "10px 10px 20px rgba(0,0,0,0.3)";
        img.addEventListener('error', () => console.error('Icon failed to load:', img.src));

        btn.appendChild(img);
        document.body.appendChild(btn);
    }

    // Button styles (insert directly so it always loads)
    var s = document.createElement('style');
    s.innerHTML = `
#open-chat-btn {
    position: fixed;
    bottom: 30px;
    right: 30px;
    width: 60px;
    height: 60px;
    border-radius: 50%;
    background: #f05a28;
    border: none;
    font-size: 2em;
    cursor: pointer;
    z-index: 1000;
    transition: background 0.2s, transform 0.2s, box-shadow 0.2s;
    box-shadow: 0 6px 12px rgb(240, 90, 40);

}

#open-chat-btn:active {
    transform: translateY(2px);
    box-shadow: 0 10px 16px rgb(240, 90, 40);
}

#open-chat-btn:hover {
    background: #f05a28;
}
#open-chat-btn img {
    width: 1.5em; 
    height: 1.5em; 
    border-radius: 50%;
    overflow: hidden;
}
#chatbot-container {
    position: fixed;
    bottom: 100px;
    right: 30px;
    z-index: 1000;
}
    `;
    document.head.appendChild(s);

    // Chatbot Container
    if (!document.getElementById('chatbot-container')) {
        var div = document.createElement('div');
        div.id = 'chatbot-container';
        document.body.appendChild(div);
    }

    // Widget loader
    document.getElementById('open-chat-btn').addEventListener('click', function () {
        let container = document.getElementById('chatbot-container');
        let widget = document.getElementById('chatbot-widget');
        if (!widget) {
            fetch(`${frontendUrl}/chatbot.html`)
                .then(resp => resp.text())
                .then(html => {
                    container.innerHTML = html;
                    if (!document.getElementById('chatbot-chat-js')) {
                        let script = document.createElement('script');
                        script.id = 'chatbot-chat-js';
                        script.type = 'module';
                        script.src = `${frontendUrl}/chatbot.js`;
                        script.onload = function () {
                            if (typeof startNewChatIfNeeded === "function") {
                                startNewChatIfNeeded(frontendUrl, backendUrl);
                            }
                        };
                        document.body.appendChild(script);
                    } else {
                        if (typeof startNewChatIfNeeded === "function") {
                            startNewChatIfNeeded(frontendUrl, backendUrl);
                        }
                    }
                })
                .catch(e => alert("Could not load chatbot: " + e));
        } else {
            if (widget.style.display === 'none' || widget.style.display === '') {
                widget.style.display = 'block';
                if (typeof startNewChatIfNeeded === "function") {
                    startNewChatIfNeeded(frontendUrl, backendUrl);
                }
            } else {
                widget.style.display = 'none';
            }
        }
    });
})();

