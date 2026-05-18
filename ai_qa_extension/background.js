// Smart QA Assistant – Service Worker (v3.0.0 - IA & Priority Bridge)

chrome.runtime.onInstalled.addListener(() => {
  console.log("%c🚀 Smart QA Bridge v3 Activé", "color: #4f46e5; font-weight: bold;");
  chrome.storage.local.get(['actions'], (res) => {
    if (!res.actions) chrome.storage.local.set({ actions: [] });
  });
});

/**
 * 1. LE BRIDGE : POLLING ACTIF (Récupération des analyses FastAPI)
 */
const BRIDGE_URL = "http://127.0.0.1:8000/get-bridge-data";
const POLLING_RATE = 2000; 

setInterval(async () => {
  try {
    const response = await fetch(BRIDGE_URL);
    if (!response.ok) return; 

    const data = await response.json();

    // Vérification de la présence de nouvelles données (has_new_data envoyé par FastAPI)
    if (data && data.has_new_data) {
      console.log(`🤖 Rapport IA reçu [${data.priority}] : ${data.scenario_name}`);
      
      // 1. Sauvegarde enrichie
      saveReportToStorage(data);
      
      // 2. Mise à jour du badge (Alerte visuelle basée sur l'importance)
      updateBadge(data.status, data.priority);

      // 3. Notification aux onglets (Content Scripts)
      notifyContentScripts(data);
    }
  } catch (err) {
    // Silencieux si le backend est éteint
  }
}, POLLING_RATE);

/**
 * 2. SAUVEGARDE ENRICHIE (Intégration de la Priorité)
 */
function saveReportToStorage(data) {
  chrome.storage.local.get({ actions: [] }, (res) => {
    let actions = res.actions;
    
    const isError = (data.status === "FAILED" || data.status === "ERROR");

    const newReport = {
      type: isError ? "AI_ERROR" : "TEST_SUCCESS",
      scenario_name: data.scenario_name || "Scénario inconnu",
      status: data.status,
      steps: data.steps || [],
      priority: data.priority || "LOW", // Récupéré de l'IA (via CSV)
      analysis: data.analysis || "Analyse indisponible",
      suggestion: data.suggestion || "Vérifiez les logs du serveur.",
      screenshot: data.screenshot || null,
      timestamp: data.timestamp || new Date().toLocaleTimeString(),
      isReport: true 
    };

    actions.push(newReport);

    // Nettoyage intelligent : On garde 15 rapports (Le Base64 des screenshots est lourd)
    if (actions.length > 15) actions.shift();

    chrome.storage.local.set({ 
      actions: actions,
      lastUpdate: Date.now() 
    });
  });
}

/**
 * 3. GESTION DU BADGE (Priorisation Visuelle)
 */
function updateBadge(status, priority) {
  const isError = (status === "FAILED" || status === "ERROR");
  
  if (!isError) {
    chrome.action.setBadgeText({ text: "OK" });
    chrome.action.setBadgeBackgroundColor({ color: "#10B981" }); // Vert
    setTimeout(() => chrome.action.setBadgeText({ text: "" }), 3000);
    return;
  }

  // Si erreur, le texte dépend de la priorité détectée par l'IA
  const badgeText = priority === "HIGH" || priority === "CRITICAL" ? "!!!" : "ERR";
  const badgeColor = priority === "HIGH" || priority === "CRITICAL" ? "#B91C1C" : "#EF4444";

  chrome.action.setBadgeText({ text: badgeText });
  chrome.action.setBadgeBackgroundColor({ color: badgeColor });
}

/**
 * 4. GESTION DES MESSAGES (Communication Inter-Composants)
 */
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  
  if (request.type === "CLEAR_SESSION") {
    chrome.storage.local.set({ actions: [] });
    chrome.action.setBadgeText({ text: "" });
    sendResponse({ status: "cleared" });
  }

  // Transmission de la demande de ticket Jira vers FastAPI
  if (request.type === "CREATE_JIRA_TICKET_SESSION") {
    fetch("http://127.0.0.1:8000/jira/create-session-ticket", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request.payload)
    })
    .then(response => response.json())
    .then(data => sendResponse(data))
    .catch(err => sendResponse({ success: false, error: err.message }));
    
    return true; // Garde le canal ouvert pour la réponse asynchrone
  }

  if (request.type === "CLEAR_BADGE") {
    chrome.action.setBadgeText({ text: "" });
  }
});

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {

    if (msg.type === "SEND_TO_XRAY_EXECUTION") {

        fetch("http://127.0.0.1:8000/xray/execute", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(msg.payload)
        })
        .then(res => res.json())
        .then(data => sendResponse(data))
        .catch(err => sendResponse({
            success: false,
            error: err.message
        }));

        return true; // async
    }
});

/**
 * 5. NOTIFICATION DES TABS
 */
function notifyContentScripts(data) {
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (tabs[0]) {
      chrome.tabs.sendMessage(tabs[0].id, {
        type: "NEW_REPORT_FROM_BACKEND",
        data: data
      }).catch(() => {}); 
    }
  });
}