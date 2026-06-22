//Initialisation
chrome.runtime.onInstalled.addListener(() => {
  console.log("%c🚀 Smart QA Bridge v3 Activé", "color: #4f46e5; font-weight: bold;");
  chrome.storage.local.get(['actions'], (res) => {
    if (!res.actions) chrome.storage.local.set({ actions: [] });
  });
});

//Polling
const BRIDGE_URL = "http://127.0.0.1:8000/get-bridge-data";
const POLLING_RATE = 3000; 

let skipCycles = 0;

setInterval(async () => {
  if (skipCycles > 0) {
    skipCycles--;
    return;
  }

  try {
    const response = await fetch(BRIDGE_URL);
    if (!response.ok) {
      skipCycles = 4;
      return; 
    }

    const data = await response.json();

    if (data && data.has_new_data) {
      console.log(`🤖 Rapport IA reçu [${data.priority}] : ${data.scenario_name}`);
      saveReportToStorage(data);
      updateBadge(data.status, data.priority);
      notifyContentScripts(data);
      skipCycles = 0;
    } else {
      skipCycles = 4; 
    }
  } catch (err) {
    skipCycles = 4;
  }
}, POLLING_RATE);

//Sauvegarde du Rapport
function saveReportToStorage(data) {
  chrome.storage.local.get({ actions: [] }, (res) => {
    let actions = res.actions;
    
    const isError = (data.status === "FAILED" || data.status === "ERROR");

    const newReport = {
      type: isError ? "AI_ERROR" : "TEST_SUCCESS",
      scenario_name: data.scenario_name || "Scénario inconnu",
      status: data.status,
      steps: data.steps || [],
      priority: data.priority || "LOW",
      analysis: data.analysis || "Analyse indisponible",
      suggestion: data.suggestion || "Vérifiez les logs du serveur.",
      screenshot: data.screenshot || null,
      timestamp: data.timestamp || new Date().toLocaleTimeString(),
      isReport: true 
    };

    actions.push(newReport);
    if (actions.length > 15) actions.shift();

    chrome.storage.local.set({ 
      actions: actions,
      lastUpdate: Date.now() 
    });
  });
}

//Gestion du Badge
function updateBadge(status, priority) {
  const isError = (status === "FAILED" || status === "ERROR");
  
  if (!isError) {
    chrome.action.setBadgeText({ text: "OK" });
    chrome.action.setBadgeBackgroundColor({ color: "#10B981" });
    setTimeout(() => chrome.action.setBadgeText({ text: "" }), 3000);
    return;
  }

  const badgeText = priority === "HIGH" || priority === "CRITICAL" ? "!!!" : "ERR";
  const badgeColor = priority === "HIGH" || priority === "CRITICAL" ? "#B91C1C" : "#EF4444";

  chrome.action.setBadgeText({ text: badgeText });
  chrome.action.setBadgeBackgroundColor({ color: badgeColor });
}

//Communication
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

        return true;
    }
});

//Notification
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