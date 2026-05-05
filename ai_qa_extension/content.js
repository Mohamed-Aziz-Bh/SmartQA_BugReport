// Smart QA – Content Script (v3.0.0)
console.log("%c🔍 SmartQA Sensor: Monitoring actif", "color: #0ea5e9; font-weight: bold;");

/**
 * 1. CAPTURE DES ERREURS JAVASCRIPT (Runtime)
 */
window.addEventListener('error', (event) => {
    const errorData = {
        type: "JS_ERROR",
        message: event.message,
        source: event.filename,
        line: event.lineno,
        col: event.colno,
        stack: event.error ? event.error.stack : "No stack trace",
        timestamp: new Date().toISOString()
    };
    sendToBackground("BROWSER_CONSOLE_LOG", errorData);
});

/**
 * 2. CAPTURE DES PROMESSES NON GÉRÉES (Async Errors)
 */
window.addEventListener('unhandledrejection', (event) => {
    const errorData = {
        type: "PROMISE_ERROR",
        reason: event.reason ? event.reason.toString() : "Unknown Rejection",
        timestamp: new Date().toISOString()
    };
    sendToBackground("BROWSER_CONSOLE_LOG", errorData);
});

/**
 * 3. INTERCEPTION DES REQUÊTES RÉSEAU (Fetch/XHR échoués)
 * Note: Pour un PFE, capturer les 4xx/5xx est crucial pour l'IA
 */
const originalFetch = window.fetch;
window.fetch = async (...args) => {
    try {
        const response = await originalFetch(...args);
        if (!response.ok) {
            sendToBackground("NETWORK_ERROR", {
                url: args[0],
                status: response.status,
                statusText: response.statusText,
                method: args[1]?.method || 'GET'
            });
        }
        return response;
    } catch (error) {
        sendToBackground("NETWORK_ERROR", {
            url: args[0],
            status: "CRASH",
            error: error.message
        });
        throw error;
    }
};

/**
 * 4. ÉCOUTEUR DE MESSAGES (Réception depuis le Background)
 * Permet d'afficher des alertes ou des overlays si l'IA détecte un bug critique
 */
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.type === "NEW_REPORT_FROM_BACKEND") {
        const data = request.data;
        
        // Si l'IA détecte une priorité CRITICAL, on peut faire clignoter le bord de la page
        if (data.priority === "CRITICAL" || data.priority === "HIGH") {
            showVisualAlert(data.analysis, data.priority);
        }
    }
});

/**
 * 5. FONCTIONS UTILITAIRES
 */
function sendToBackground(type, payload) {
    chrome.runtime.sendMessage({
        type: type,
        payload: payload,
        url: window.location.href,
        title: document.title
    }).catch(() => {
        // Évite les erreurs si l'extension est rechargée
    });
}

function showVisualAlert(analysis, priority) {
    const alertDiv = document.createElement('div');
    alertDiv.style = `
        position: fixed; top: 10px; right: 10px; z-index: 999999;
        background: #B91C1C; color: white; padding: 12px 20px;
        border-radius: 8px; font-family: sans-serif; font-weight: bold;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3); border: 2px solid white;
        animation: slideIn 0.5s ease-out;
    `;
    alertDiv.innerHTML = `⚠️ SmartQA [${priority}] : ${analysis}`;
    document.body.appendChild(alertDiv);
    
    setTimeout(() => alertDiv.remove(), 5000);
}

// Ajout d'une petite animation CSS via JS
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
`;
document.head.appendChild(style);