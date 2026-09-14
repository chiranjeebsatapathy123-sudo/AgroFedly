document.addEventListener("DOMContentLoaded", () => {
    const widget = document.getElementById("copilot-widget");
    if (!widget) return;

    const toggleBtn = document.getElementById("copilot-toggle-btn");
    const header = document.querySelector(".copilot-header");
    const inputField = document.getElementById("copilot-input");
    const sendBtn = document.getElementById("copilot-send-btn");
    const voiceBtn = document.getElementById("copilot-voice-btn");
    const messagesContainer = document.getElementById("copilot-messages");

    let isRecording = false;
    let recognition = null;

    // Initialize Web Speech API
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = true;
        
        recognition.onstart = function() {
            isRecording = true;
            voiceBtn.classList.add("recording");
            inputField.placeholder = "Listening...";
        };
        
        recognition.onresult = function(event) {
            let interimTranscript = '';
            let finalTranscript = '';
            
            for (let i = event.resultIndex; i < event.results.length; ++i) {
                if (event.results[i].isFinal) {
                    finalTranscript += event.results[i][0].transcript;
                } else {
                    interimTranscript += event.results[i][0].transcript;
                }
            }
            
            inputField.value = finalTranscript || interimTranscript;
            
            if (finalTranscript) {
                sendMessage(finalTranscript);
            }
        };
        
        recognition.onerror = function(event) {
            console.error("Speech recognition error", event.error);
            stopRecording();
        };
        
        recognition.onend = function() {
            stopRecording();
        };
    } else {
        voiceBtn.style.display = 'none';
        console.warn("Speech Recognition API not supported in this browser.");
    }

    function startRecording() {
        if (recognition && !isRecording) {
            inputField.value = '';
            recognition.start();
        }
    }

    function stopRecording() {
        if (recognition && isRecording) {
            recognition.stop();
            isRecording = false;
            voiceBtn.classList.remove("recording");
            inputField.placeholder = "Type or speak...";
        }
    }

    // Toggle widget
    const toggleWidget = (e) => {
        // If clicking on header when collapsed, open it
        if (widget.classList.contains("collapsed")) {
            widget.classList.remove("collapsed");
            inputField.focus();
        } else if (e.target === toggleBtn) {
            widget.classList.add("collapsed");
        }
    };

    header.addEventListener("click", toggleWidget);

    // Voice button
    voiceBtn.addEventListener("mousedown", startRecording);
    voiceBtn.addEventListener("mouseup", stopRecording);
    voiceBtn.addEventListener("touchstart", (e) => { e.preventDefault(); startRecording(); });
    voiceBtn.addEventListener("touchend", (e) => { e.preventDefault(); stopRecording(); });

    // Send button
    sendBtn.addEventListener("click", () => {
        if (inputField.value.trim()) {
            sendMessage(inputField.value.trim());
        }
    });

    // Enter key
    inputField.addEventListener("keypress", (e) => {
        if (e.key === "Enter" && inputField.value.trim()) {
            sendMessage(inputField.value.trim());
        }
    });

    function appendMessage(text, sender) {
        const msgDiv = document.createElement("div");
        msgDiv.className = `copilot-msg ${sender}-msg`;
        msgDiv.innerText = text;
        messagesContainer.appendChild(msgDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    function speakText(text) {
        if ('speechSynthesis' in window) {
            window.speechSynthesis.cancel();
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.rate = 1.0;
            utterance.pitch = 1.0;
            window.speechSynthesis.speak(utterance);
        }
    }

    async function sendMessage(text) {
        appendMessage(text, "user");
        inputField.value = "";
        
        // --- PHASE 2: Voice-First Intent Parsing for Farmers ---
        const lowerText = text.toLowerCase();
        if (lowerText.includes("list") || lowerText.includes("rent") || lowerText.includes("add")) {
            if (lowerText.includes("tractor") || lowerText.includes("equipment") || lowerText.includes("machine")) {
                appendMessage("Navigating you to the Equipment Listing page...", "ai");
                speakText("Navigating you to the Equipment Listing page.");
                setTimeout(() => {
                    window.location.href = "/agriculture/equipment/add/";
                }, 1500);
                return;
            }
        }
        
        // Show typing indicator
        const typingDiv = document.createElement("div");
        typingDiv.className = "copilot-typing";
        typingDiv.innerText = "AI is typing...";
        messagesContainer.appendChild(typingDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;

        try {
            const response = await fetch("/api/copilot/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": getCookie("csrftoken")
                },
                body: JSON.stringify({ message: text })
            });
            
            typingDiv.remove();
            
            if (response.ok) {
                const data = await response.json();
                if (data.response) {
                    appendMessage(data.response, "ai");
                    speakText(data.response);
                }
            } else {
                appendMessage("Error communicating with server.", "ai");
            }
        } catch (err) {
            typingDiv.remove();
            appendMessage("Network error. Please try again.", "ai");
        }
    }

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
});
