let selectedStepIndex = null;

/**
 * 1. SURVEILLANCE DES CHANGEMENTS (Temps réel)
 */
chrome.storage.onChanged.addListener((changes, area) => {
    if (area === 'local' && (changes.actions || changes.lastUpdate)) {
        renderTimeline();
        if (selectedStepIndex !== null) {
            chrome.storage.local.get({ actions: [] }, (data) => {
                const filteredActions = getFilteredActions(data.actions);
                if (filteredActions[selectedStepIndex]) {
                    renderDetailsContent(filteredActions[selectedStepIndex]);
                }
            });
        }
    }
});

/**
 * 2. INITIALISATION
 */
document.addEventListener('DOMContentLoaded', () => {
    detectWebdriverMode();
    renderTimeline();
    
    // Efface le badge dès qu'on ouvre l'extension
    chrome.runtime.sendMessage({ type: "CLEAR_BADGE" });
    
    // Bouton Export JSON
    const downloadBtn = document.getElementById('download-report-btn');
    if (downloadBtn) downloadBtn.onclick = () => exportFullSession(true);

    // Bouton Jira Global
    const jiraBtn = document.getElementById('jira-global-btn');
    if (jiraBtn) jiraBtn.onclick = () => exportFullSession(false);

    // Bouton Nettoyer Session
    const clearBtn = document.getElementById('clear-btn');
    if (clearBtn) {
        clearBtn.onclick = () => {
            if (confirm("Voulez-vous vider l'historique de cette session ?")) {
                chrome.runtime.sendMessage({ type: "CLEAR_SESSION" }, () => {
                    selectedStepIndex = null;
                    document.getElementById('details-panel').style.display = 'none';
                    renderTimeline();
                });
            }
        };
    }

    // Fermeture du panel de détails
    const closeBtn = document.getElementById('close-panel');
    if (closeBtn) {
        closeBtn.onclick = () => {
            const panel = document.getElementById('details-panel');
            panel.style.transform = 'translateY(100%)'; 
            setTimeout(() => { panel.style.display = 'none'; }, 300);
            selectedStepIndex = null;
            renderTimeline();
        };
    }
});

/**
 * 3. LOGIQUE D'EXPORTATION (JSON & JIRA)
 */
function exportFullSession(shouldDownload = true) {
    chrome.storage.local.get({ actions: [] }, (data) => {
        const filtered = getFilteredActions(data.actions);
        if (filtered.length === 0) {
            alert("Aucun scénario valide à exporter.");
            return;
        }

        const sessionReport = {
            project_info: {
                name: "SmartQA Professional Export",
                date: new Date().toLocaleString(),
                total_scenarios: filtered.length
            },
            test_results: filtered.map(action => ({
                scenario: action.scenario_name,
                status: action.status,
                priority: action.priority || "MEDIUM",
                timestamp: action.timestamp,
                ia_analysis: {
                    suggestion: action.suggestion || "N/A",
                    details: action.analysis || "N/A"
                },
                steps: action.steps || [],
                screenshot: action.screenshot || null
            }))
        };

        if (shouldDownload) {
            downloadJsonReport(sessionReport);
        } else {
            sendToJira(sessionReport);
        }
    });
}

function sendToJira(sessionReport) {
    const jiraBtn = document.getElementById('jira-global-btn');
    const originalContent = jiraBtn.innerHTML;
    
    jiraBtn.disabled = true;
    jiraBtn.innerHTML = `<i class="material-icons rotate">sync</i> <span>ENVOI...</span>`;

    chrome.runtime.sendMessage({ 
        type: "CREATE_JIRA_TICKET_SESSION", 
        payload: sessionReport 
    }, (response) => {
        jiraBtn.disabled = false;
        jiraBtn.innerHTML = originalContent;
        if (response && response.success) {
            alert(`Ticket Jira créé avec succès : ${response.issueKey}`);
        } else {
            alert("Erreur Jira : " + (response?.error || "Vérifiez votre Backend FastAPI"));
        }
    });
}

/**
 * 4. RENDU DE LA TIMELINE
 */
function getFilteredActions(actions) {
    return actions.filter(a => a.scenario_name && a.isReport);
}

function renderTimeline() {
    chrome.storage.local.get({ actions: [] }, (data) => {
        const container = document.getElementById('timeline');
        if (!container) return;

        const filteredActions = getFilteredActions(data.actions).reverse(); // Derniers en haut

        updateStatsUI(
            filteredActions.length, 
            filteredActions.filter(a => ['PASSED', 'SUCCESS'].includes(a.status)).length,
            filteredActions.filter(a => ['FAILED', 'ERROR'].includes(a.status)).length
        );

        if (filteredActions.length === 0) {
            container.innerHTML = `<div class="empty-state">En attente de tests...</div>`;
            return;
        }

        container.innerHTML = ''; 
        filteredActions.forEach((action, index) => {
            const isFailed = action.status === 'FAILED' || action.status === 'ERROR';
            const step = document.createElement('div');
            step.className = `timeline-step ${isFailed ? 'failed-step' : 'passed-step'} ${selectedStepIndex === index ? 'active' : ''}`;
            
            // On affiche un badge de priorité si c'est une erreur
            const priorityBadge = isFailed ? `<span class="prio-tag ${action.priority?.toLowerCase()}">${action.priority}</span>` : '';

            step.innerHTML = `
                <div class="step-header">
                    <span class="badge ${getStatusBadgeClass(action.status)}">${action.status}</span>
                    ${priorityBadge}
                    <span class="step-time">${action.timestamp || '--:--'}</span>
                </div>
                <div class="step-body">${action.scenario_name}</div>
            `;
            step.onclick = () => selectStep(index, filteredActions);
            container.appendChild(step);
        });
    });
}

/**
 * 5. RENDU DES DÉTAILS (IA & PRIORITÉ)
 */
function selectStep(index, filteredList) {
    selectedStepIndex = index;
    const panel = document.getElementById('details-panel');
    panel.style.display = 'flex';
    setTimeout(() => { panel.style.transform = 'translateY(0)'; }, 10);
    renderDetailsContent(filteredList[index]);
    renderTimeline();
}

function renderDetailsContent(action) {
    const detailContent = document.getElementById('detail-content');
    if (!detailContent) return;

    const isError = action.status === 'FAILED' || action.status === 'ERROR';
    const priority = action.priority || "LOW";
    
    // Détermination de la couleur de l'IA selon la priorité
    const aiColor = priority === "CRITICAL" || priority === "HIGH" ? "#ef4444" : "#10b981";
    const aiBg = priority === "CRITICAL" || priority === "HIGH" ? "#fef2f2" : "#f0fdf4";

    detailContent.innerHTML = `
        <div class="detail-card">
            <div class="detail-section">
                <strong><i class="material-icons">info</i> Statut :</strong>
                <p>${action.scenario_name} <span class="prio-tag ${priority.toLowerCase()}">${priority}</span></p>
            </div>
            
            ${action.steps && action.steps.length > 0 ? `
            <div class="detail-section">
                <strong><i class="material-icons">list</i> Étapes Gherkin :</strong>
                <div class="gherkin-container">
                    ${action.steps.map(s => {
                        const sStatus = (s.status || 'pending').toLowerCase();
                        const icon = sStatus === 'passed' ? 'check_circle' : sStatus === 'failed' ? 'cancel' : 'radio_button_unchecked';
                        const color = sStatus === 'passed' ? '#10b981' : sStatus === 'failed' ? '#ef4444' : '#64748b';
                        return `
                            <div class="gherkin-step" style="color:${color}">
                                <i class="material-icons" style="font-size:16px;">${icon}</i>
                                <span>${s.text}</span>
                            </div>
                        `;
                    }).join('')}
                </div>
            </div>` : ''}

            <div class="detail-section">
                <strong><i class="material-icons">psychology</i> Analyse SmartQA :</strong>
                <div class="ai-box" style="background:${aiBg}; border-left:4px solid ${aiColor};">
                    <p class="ai-title" style="color:${aiColor}">${action.analysis || "Diagnostic en cours"}</p>
                    <p class="ai-desc">${action.suggestion || "Analyse des logs en cours..."}</p>
                </div>
            </div>

            ${action.screenshot ? `
                <div class="detail-section">
                    <strong><i class="material-icons">camera_alt</i> Capture d'écran :</strong>
                    <img src="${action.screenshot}" class="img-preview" onclick="window.open('${action.screenshot}')">
                </div>` : ''}
        </div>`;
}

function getStatusBadgeClass(label) {
    if (['PASSED', 'SUCCESS'].includes(label)) return 'badge-success';
    if (['FAILED', 'ERROR'].includes(label)) return 'badge-error';
    return 'badge-user';
}

function updateStatsUI(total, passed, failed) {
    document.getElementById('total-count').innerText = total;
    document.getElementById('passed-count').innerText = passed;
    document.getElementById('failed-count').innerText = failed;
}

function detectWebdriverMode() {
    if (navigator.webdriver) {
        document.getElementById('selenium-notice').style.display = 'flex';
    }
}