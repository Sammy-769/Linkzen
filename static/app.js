const form = document.getElementById("chat-form");
const input = document.getElementById("message");
const chat = document.getElementById("chat");
const button = form.querySelector('button[type="submit"]');
const chatImageInput = document.getElementById("chat-image-input");
const chatAttachButton = document.getElementById("chat-attach-image");
const chatImagePreview = document.getElementById("chat-image-preview");
const MAX_CHAT_IMAGE_BYTES = 20 * 1024 * 1024;
const MAX_CHAT_IMAGE_DATA_URL_LENGTH = 7_100_000;
let pendingChatImage = null;

const conversationList =
    document.getElementById("conversation-list");
const conversationSearchInput = document.getElementById("conversation-search-input");
const clearConversationSearch = document.getElementById("clear-conversation-search");

const newChatButton =
    document.getElementById("new-chat");

const chatTitle =
    document.getElementById("chat-title");

const mobileMenu =
    document.getElementById("mobile-menu");

const sidebar =
    document.querySelector(".sidebar");

const usageClock = document.getElementById("usage-clock");
const usagePeak = document.getElementById("usage-peak");
const usageMonth = document.getElementById("usage-month");
const usageMonthValue = document.getElementById("usage-month-value");
const usageAverageValue = document.getElementById("usage-average-value");


const STORAGE_KEY = "linkzen_conversations";
const LEGACY_STORAGE_KEY = "linkedin_ai_conversations";


const memoriesButton =
    document.getElementById("memories-button");

const memoriesPanel =
    document.getElementById("memories-panel");

const closeMemories =
    document.getElementById("close-memories");

const memoryInput =
    document.getElementById("memory-input");

const saveMemoryButton =
    document.getElementById("save-memory");

const memoryList =
    document.getElementById("memory-list");


const settingsButton =
    document.getElementById("settings-button");

const settingsPanel =
    document.getElementById("settings-panel");

const closeSettings =
    document.getElementById("close-settings");

const automaticMemory =
    document.getElementById("automatic-memory");

const ragEnabled =
    document.getElementById("rag-enabled");

const memoryDebug =
    document.getElementById("memory-debug");

const globalPrompt = document.getElementById("global-prompt");
const saveGlobalPromptButton = document.getElementById("save-global-prompt");
const globalPromptStatus = document.getElementById("global-prompt-status");

const knowledgeButton =
    document.getElementById("knowledge-button");

const knowledgePanel =
    document.getElementById("knowledge-panel");

const closeKnowledge =
    document.getElementById("close-knowledge");

const knowledgeUploadForm =
    document.getElementById("knowledge-upload-form");

const knowledgeFile =
    document.getElementById("knowledge-file");

const uploadKnowledgeButton =
    document.getElementById("upload-knowledge");

const reindexAllKnowledgeButton =
    document.getElementById("reindex-all-knowledge");

const knowledgeStatus =
    document.getElementById("knowledge-status");

const knowledgeList =
    document.getElementById("knowledge-list");

const knowledgeBreadcrumbs = document.getElementById("knowledge-breadcrumbs");
const knowledgeCreateFolderForm = document.getElementById("knowledge-create-folder-form");
const knowledgeFolderName = document.getElementById("knowledge-folder-name");
const knowledgeMoveDialog = document.getElementById("knowledge-move-dialog");
const knowledgeMoveForm = document.getElementById("knowledge-move-form");
const knowledgeMoveDestination = document.getElementById("knowledge-move-destination");
let currentKnowledgeFolder = "";
let knowledgeEntries = [];

const linkedinButton =
    document.getElementById("linkedin-button");

const linkedinPanel =
    document.getElementById("linkedin-panel");

const closeLinkedIn =
    document.getElementById("close-linkedin");

const linkedinForm =
    document.getElementById("linkedin-form");

const linkedinInput =
    document.getElementById("linkedin-input");

const linkedinInputLabel =
    document.getElementById("linkedin-input-label");
const linkedinInstructionsField = document.getElementById("linkedin-instructions-field");
const linkedinInstructionsLabel = document.getElementById("linkedin-instructions-label");
const linkedinInstructionsInput = document.getElementById("linkedin-instructions");
const linkedinPerformanceField = document.getElementById("linkedin-performance-field");
const linkedinPerformanceInput = document.getElementById("linkedin-performance-data");

const linkedinSubmit =
    document.getElementById("linkedin-submit");

const linkedinStatus =
    document.getElementById("linkedin-status");

const linkedinResult =
    document.getElementById("linkedin-result");

const linkedinTools =
    document.querySelectorAll(".linkedin-tool");
const linkedinPromptEditor = document.getElementById("linkedin-prompt-editor");
const linkedinPromptInput = document.getElementById("linkedin-prompt-input");
const linkedinPromptStatus = document.getElementById("linkedin-prompt-status");
const linkedinImagesInput = document.getElementById("linkedin-images");
const linkedinImageStatus = document.getElementById("linkedin-image-status");
const linkedinHistoryList = document.getElementById("linkedin-history-list");
const linkedinHistorySummary = document.getElementById("linkedin-history-summary");
let linkedinPromptDefaults = {};
let linkedinPrompts = {};

const linkedinToolOptions = {
    analyze_profile: {
        label: "Profile or question",
        placeholder: "Share the profile URL, paste profile details, or ask for an analysis...",
        submit: "Analyze profile"
    },
    create_post: {
        label: "Request, idea, or draft",
        placeholder: "Create a post, generate hooks or CTAs, critique a draft, or improve it...",
        submit: "Create post"
    },
    analyze_post: {
        label: "LinkedIn post",
        placeholder: "Paste the complete LinkedIn post you want analysed...",
        instructionsLabel: "Additional context (optional)",
        instructionsPlaceholder: "Who was it for? Why did you write it, what were you trying to achieve, or what personal context matters?",
        submit: "Analyse Post",
        performanceLabel: "Performance data (optional)"
    },
    post_ideas: {
        label: "Topic or request (optional)",
        placeholder: "For example: AWS Lambda, cloud networking, or leave blank to use your content pillars and context...",
        submit: "Generate ideas"
    },
    make_comment: {
        label: "Post or context",
        placeholder: "Paste or link the post/context, then describe the kind of comment you want...",
        submit: "Make a comment"
    },
    reply_to_message: {
        label: "Received LinkedIn message",
        placeholder: "Paste the private LinkedIn message or include its URL...",
        instructionsLabel: "Reply instructions or context (optional)",
        instructionsPlaceholder: "For example: Politely decline, or say I'm interested and ask for more details...",
        submit: "Create reply"
    },
    ask_knowledge: {
        label: "Question",
        placeholder: "Ask about LinkedIn strategy, writing, profile optimisation, or saved knowledge...",
        submit: "Ask knowledge"
    }
};

let activeLinkedInAction = "create_post";
const linkedinComposerStates = Object.fromEntries(
    Object.keys(linkedinToolOptions).map(action => [
        action,
        { text: "", instructions: "", performanceData: "", files: [] }
    ])
);

function linkedinComposerState(action = activeLinkedInAction) {
    return linkedinComposerStates[action];
}

function saveActiveLinkedInDraft() {
    const draft = linkedinComposerState();
    draft.text = linkedinInput.value;
    draft.instructions = linkedinInstructionsInput.value;
    draft.performanceData = linkedinPerformanceInput.value;
    if (linkedinImagesInput.files.length) {
        draft.files = [...linkedinImagesInput.files];
    }
}

function restoreLinkedInDraft(action) {
    const draft = linkedinComposerState(action);
    linkedinInput.value = draft.text;
    linkedinInstructionsInput.value = draft.instructions;
    linkedinPerformanceInput.value = draft.performanceData || "";
    linkedinImagesInput.value = "";
    linkedinImageStatus.textContent = draft.files.length
        ? `${draft.files.length} image${draft.files.length === 1 ? "" : "s"} selected.`
        : "";
}

const LINKEDIN_HISTORY_KEY = "linkzen_linkedin_tool_history";
let linkedinHistory = {};
try {
    linkedinHistory = JSON.parse(localStorage.getItem(LINKEDIN_HISTORY_KEY) || "{}");
} catch {
    linkedinHistory = {};
}

    
const savedConversations = localStorage.getItem(STORAGE_KEY);
const legacyConversations = localStorage.getItem(LEGACY_STORAGE_KEY);
let conversations = JSON.parse(
    savedConversations ?? legacyConversations ?? "[]"
);

if (legacyConversations !== null) {
    if (savedConversations === null) {
        localStorage.setItem(STORAGE_KEY, legacyConversations);
    }
    localStorage.removeItem(LEGACY_STORAGE_KEY);
}

let currentConversationId = null;
let pendingSearchMessageIndex = null;
const retryImagePayloads = new Map();

const applicationViews = {
    memories: memoriesPanel,
    settings: settingsPanel,
    knowledge: knowledgePanel,
    linkedin: linkedinPanel
};


function showView(viewName = "chat") {
    Object.entries(applicationViews).forEach(([name, panel]) => {
        const isActive = name === viewName;
        panel.classList.toggle("open", isActive);
        panel.setAttribute("aria-hidden", String(!isActive));
    });
    sidebar.classList.remove("open");
}


/* ============================================================
   Storage
   ============================================================ */

function saveConversations() {

    localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify(conversations)
    );
}


function toolHistory(action) {
    if (!linkedinHistory[action]) {
        linkedinHistory[action] = { activeSessionId: null, sessions: [] };
    }
    return linkedinHistory[action];
}


function saveLinkedInHistory() {
    try {
        localStorage.setItem(LINKEDIN_HISTORY_KEY, JSON.stringify(linkedinHistory));
    } catch (error) {
        linkedinStatus.textContent = "This result is too large to save in browser history.";
        console.error(error);
    }
}


function startLinkedInSession(action = activeLinkedInAction) {
    const history = toolHistory(action);
    const session = { id: crypto.randomUUID(), startedAt: Date.now(), records: [] };
    history.sessions.unshift(session);
    history.activeSessionId = session.id;
    history.sessions = history.sessions.slice(0, 30);
    saveLinkedInHistory();
    linkedinComposerStates[action] = {
        text: "",
        instructions: "",
        performanceData: "",
        files: []
    };
    if (action === activeLinkedInAction) {
        restoreLinkedInDraft(action);
        linkedinStatus.textContent = "";
        linkedinResult.textContent = "Your result will appear here.";
        renderLinkedInHistory();
    }
}


function renderLinkedInHistory() {
    const history = toolHistory(activeLinkedInAction);
    const sessions = history.sessions || [];
    linkedinHistorySummary.textContent = `Previous sessions (${sessions.reduce((sum, session) => sum + session.records.length, 0)})`;
    linkedinHistoryList.replaceChildren();

    sessions.forEach((session, sessionIndex) => {
        const group = document.createElement("section");
        group.className = "linkedin-history-session";
        const heading = document.createElement("h4");
        heading.textContent = sessionIndex === 0 ? "Latest session" : new Date(session.startedAt).toLocaleString();
        const sessionHeader = document.createElement("div");
        sessionHeader.className = "linkedin-history-session-header";
        const deleteSessionButton = document.createElement("button");
        deleteSessionButton.type = "button";
        deleteSessionButton.className = "linkedin-history-delete";
        deleteSessionButton.textContent = "Delete session";
        deleteSessionButton.setAttribute("aria-label", `Delete ${heading.textContent}`);
        deleteSessionButton.addEventListener("click", () => {
            history.sessions = history.sessions.filter(item => item.id !== session.id);
            if (history.activeSessionId === session.id) {
                history.activeSessionId = history.sessions[0]?.id || null;
            }
            saveLinkedInHistory();
            renderLinkedInHistory();
        });
        sessionHeader.append(heading, deleteSessionButton);
        group.appendChild(sessionHeader);

        [...session.records].reverse().forEach(record => {
            const openButton = document.createElement("button");
            openButton.type = "button";
            openButton.className = "linkedin-history-record";
            openButton.textContent = `${new Date(record.createdAt).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })} · ${(record.request || "Image request").replace(/\s+/g, " ").slice(0, 76)}`;
            openButton.addEventListener("click", () => {
                linkedinInput.value = record.request || "";
                linkedinInstructionsInput.value = record.instructions || "";
                linkedinComposerStates[activeLinkedInAction] = {
                    text: record.request || "",
                    instructions: record.instructions || "",
                    performanceData: record.performance_data || "",
                    files: []
                };
                linkedinPerformanceInput.value = record.performance_data || "";
                linkedinImagesInput.value = "";
                linkedinImageStatus.textContent = record.hadImages
                    ? "This record used an image. Reattach it to include it in a new request."
                    : "";
                renderMarkdown(linkedinResult, record.result, true);
                const knowledgeStatus = createKnowledgeStatus(record.sources);
                if (knowledgeStatus) linkedinResult.appendChild(knowledgeStatus);
                const memoryStatus = createMemoryContextStatus(record.memory_context);
                if (memoryStatus) linkedinResult.appendChild(memoryStatus);
                linkedinStatus.textContent = "Opened saved record. Edit the request or run it again to reuse it.";
            });
            const recordRow = document.createElement("div");
            recordRow.className = "linkedin-history-record-row";
            const deleteRecordButton = document.createElement("button");
            deleteRecordButton.type = "button";
            deleteRecordButton.className = "linkedin-history-delete";
            deleteRecordButton.textContent = "Delete";
            deleteRecordButton.setAttribute("aria-label", "Delete saved result");
            deleteRecordButton.addEventListener("click", () => {
                session.records = session.records.filter(item => item.id !== record.id);
                if (!session.records.length) {
                    history.sessions = history.sessions.filter(item => item.id !== session.id);
                    if (history.activeSessionId === session.id) {
                        history.activeSessionId = history.sessions[0]?.id || null;
                    }
                }
                saveLinkedInHistory();
                renderLinkedInHistory();
            });
            recordRow.append(openButton, deleteRecordButton);
            group.appendChild(recordRow);
        });
        linkedinHistoryList.appendChild(group);
    });

    if (!sessions.length) {
        const empty = document.createElement("p");
        empty.textContent = "No previous sessions for this tool.";
        linkedinHistoryList.appendChild(empty);
    }
}


function recentLinkedInWork() {
    return Object.values(linkedinHistory)
        .flatMap(history => (history.sessions || []).flatMap(session => session.records || []))
        .sort((first, second) => second.createdAt - first.createdAt)
        .slice(0, 8)
        .map(record => ({ request: record.request || "", result: record.result || "" }));
}


function readFileAsDataUrl(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = () => reject(new Error(`Could not read ${file.name}.`));
        reader.readAsDataURL(file);
    });
}


/* ============================================================
   Conversation helpers
   ============================================================ */

function createConversation() {

    const emptyConversation = conversations.find(
        conversation => Array.isArray(conversation.messages) && conversation.messages.length === 0
    );

    if (emptyConversation) {
        currentConversationId = emptyConversation.id;
        showView("chat");
        renderConversationList();
        renderConversation();
        input.focus();
        return emptyConversation;
    }

    const conversation = {
        id: crypto.randomUUID(),
        title: "New chat",
        messages: [],
        createdAt: Date.now()
    };

    conversations.unshift(conversation);

    currentConversationId = conversation.id;

    saveConversations();

    renderConversationList();

    renderConversation();

    input.focus();
    return conversation;
}


async function consumeAssistantStream(response, onStatus, onToken) {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let pending = "";
    let answer = "";
    let sources = [];
    let memoryContext = [];
    let complete = false;

    while (!complete) {
        const { value, done } = await reader.read();
        pending += decoder.decode(value || new Uint8Array(), { stream: !done });
        const events = pending.split(/\r?\n\r?\n/);
        pending = events.pop() || "";

        for (const eventText of events) {
            const dataLine = eventText.split(/\r?\n/).find(line => line.startsWith("data: "));
            if (!dataLine) continue;

            const event = JSON.parse(dataLine.slice(6));
            if (event.type === "status") {
                onStatus(event.message);
            } else if (event.type === "token") {
                answer += event.text;
                onToken(answer);
            } else if (event.type === "error") {
                throw new Error(event.message);
            } else if (event.type === "done") {
                answer = event.answer || answer;
                sources = Array.isArray(event.sources) ? event.sources : [];
                memoryContext = Array.isArray(event.memory_context) ? event.memory_context : [];
                complete = true;
                break;
            }
        }

        if (done && !complete) {
            if (pending.trim()) {
                const finalLine = pending.split(/\r?\n/).find(line => line.startsWith("data: "));
                if (finalLine) {
                    const event = JSON.parse(finalLine.slice(6));
                    if (event.type === "error") throw new Error(event.message);
                    if (event.type === "done") {
                        answer = event.answer || answer;
                        sources = Array.isArray(event.sources) ? event.sources : [];
                        memoryContext = Array.isArray(event.memory_context) ? event.memory_context : [];
                    }
                }
            }
            complete = true;
        }
    }

    return { answer, sources, memoryContext };
}


function getCurrentConversation() {

    return conversations.find(
        conversation =>
            conversation.id === currentConversationId
    );
}


function deleteConversation(id) {

    conversations =
        conversations.filter(
            conversation =>
                conversation.id !== id
        );

    saveConversations();

    if (currentConversationId === id) {

        if (conversations.length > 0) {

            currentConversationId =
                conversations[0].id;

        } else {

            currentConversationId = null;

        }
    }

    renderConversationList();

    renderConversation();
}


/* ============================================================
   Sidebar
   ============================================================ */

function renderConversationList() {

    conversationList.innerHTML = "";

    const query = conversationSearchInput.value.trim();
    clearConversationSearch.hidden = !query;

    function createConversationItem(conversation, searchResult = null) {
        const item = document.createElement("div");
        item.className = "conversation";
        if (searchResult) item.classList.add("search-result");
        if (conversation.id === currentConversationId) item.classList.add("active");

        const content = document.createElement("div");
        content.className = searchResult ? "conversation-result-content" : "conversation-title";
        content.textContent = conversation.title || "New chat";

        if (searchResult) {
            const preview = document.createElement("div");
            preview.className = "conversation-snippet";
            preview.textContent = searchResult.snippet;
            content.appendChild(preview);
        }

        const pinButton = document.createElement("button");
        pinButton.type = "button";
        pinButton.className = "pin-chat";
        pinButton.textContent = conversation.pinned ? "Unpin" : "Pin";
        pinButton.title = conversation.pinned ? "Unpin chat" : "Pin chat";
        pinButton.setAttribute("aria-label", pinButton.title);
        pinButton.setAttribute("aria-pressed", String(Boolean(conversation.pinned)));
        pinButton.addEventListener("click", event => {
            event.stopPropagation();
            conversation.pinned = !conversation.pinned;
            saveConversations();
            renderConversationList();
        });

        const deleteButton = document.createElement("button");
        deleteButton.type = "button";
        deleteButton.className = "delete-chat";
        deleteButton.textContent = "×";
        deleteButton.title = "Delete chat";
        deleteButton.setAttribute("aria-label", "Delete chat");
        deleteButton.addEventListener("click", event => {
            event.stopPropagation();
            deleteConversation(conversation.id);
        });

        item.append(content, pinButton, deleteButton);
        item.addEventListener("click", () => {
            currentConversationId = conversation.id;
            pendingSearchMessageIndex = searchResult?.messageMatch >= 0
                ? searchResult.messageMatch
                : null;
            showView("chat");
            renderConversationList();
            renderConversation();
            sidebar.classList.remove("open");
        });
        return item;
    }

    function appendConversationSection(title, sectionConversations, searchResults = null) {
        if (sectionConversations.length === 0) return;

        const section = document.createElement("section");
        section.className = "conversation-section";
        const heading = document.createElement("h3");
        heading.className = "conversation-section-heading";
        heading.textContent = title;
        section.appendChild(heading);

        sectionConversations.forEach(conversation => {
            const result = searchResults?.find(item => item.conversation.id === conversation.id) || null;
            section.appendChild(createConversationItem(conversation, result));
        });
        conversationList.appendChild(section);
    }

    if (query) {
        const terms = query.toLocaleLowerCase().split(/\s+/).filter(Boolean);
        const results = conversations.map(conversation => {
            const messages = Array.isArray(conversation.messages) ? conversation.messages : [];
            const searchableText = [conversation.title || "", ...messages.map(message => message.content || "")]
                .join(" ").toLocaleLowerCase();
            if (!terms.every(term => searchableText.includes(term))) return null;

            const messageMatch = messages.findIndex(message =>
                terms.some(term => String(message.content || "").toLocaleLowerCase().includes(term))
            );
            const matchedMessage = messageMatch >= 0 ? messages[messageMatch] : null;
            let snippet = "Title match";
            if (matchedMessage) {
                const content = String(matchedMessage.content || "").replace(/\s+/g, " ").trim();
                const foldedContent = content.toLocaleLowerCase();
                const matchPositions = terms
                    .map(term => foldedContent.indexOf(term))
                    .filter(position => position >= 0);
                const matchPosition = Math.min(...matchPositions);
                const start = Math.max(0, matchPosition - 60);
                const end = Math.min(content.length, matchPosition + 140);
                const excerpt = `${start > 0 ? "..." : ""}${content.slice(start, end)}${end < content.length ? "..." : ""}`;
                snippet = `${matchedMessage.role === "user" ? "You" : "Linkzen"}: ${excerpt}`;
            }
            return { conversation, messageMatch, snippet };
        }).filter(Boolean);

        if (results.length === 0) {
            const empty = document.createElement("div");
            empty.className = "conversation-empty";
            empty.textContent = "No conversations found";
            conversationList.appendChild(empty);
            return;
        }

        const matchedConversations = results.map(result => result.conversation);
        appendConversationSection(
            "Pinned",
            matchedConversations.filter(conversation => conversation.pinned),
            results
        );
        appendConversationSection(
            "Conversations",
            matchedConversations.filter(conversation => !conversation.pinned),
            results
        );
        return;
    }

    appendConversationSection("Pinned", conversations.filter(conversation => conversation.pinned));
    appendConversationSection("Conversations", conversations.filter(conversation => !conversation.pinned));
}


/* ============================================================
   Chat rendering
   ============================================================ */

function appendInlineMarkdown(parent, text) {

    const tokenPattern = /(`+)(.+?)\1|\*\*(.+?)\*\*|__(.+?)__|\*(.+?)\*|_(.+?)_|\[([^\]]+)\]\(([^)\s]+)(?:\s+["'][^"']*["'])?\)/g;
    let lastIndex = 0;
    let match;

    while ((match = tokenPattern.exec(text)) !== null) {

        parent.appendChild(
            document.createTextNode(text.slice(lastIndex, match.index))
        );

        if (match[1]) {
            const code = document.createElement("code");
            code.textContent = match[2];
            parent.appendChild(code);
        } else if (match[3] || match[4]) {
            const strong = document.createElement("strong");
            appendInlineMarkdown(strong, match[3] || match[4]);
            parent.appendChild(strong);
        } else if (match[5] || match[6]) {
            const emphasis = document.createElement("em");
            appendInlineMarkdown(emphasis, match[5] || match[6]);
            parent.appendChild(emphasis);
        } else {
            let url;
            try {
                url = new URL(match[8], window.location.href);
            } catch {
                url = null;
            }

            if (url && ["http:", "https:", "mailto:"].includes(url.protocol)) {
                const link = document.createElement("a");
                link.href = url.href;
                link.target = "_blank";
                link.rel = "noopener noreferrer";
                appendInlineMarkdown(link, match[7]);
                parent.appendChild(link);
            } else {
                parent.appendChild(document.createTextNode(match[0]));
            }
        }

        lastIndex = tokenPattern.lastIndex;
    }

    parent.appendChild(document.createTextNode(text.slice(lastIndex)));
}


function renderMarkdownBlocks(container, markdown) {

    const lines = markdown.replace(/\r\n?/g, "\n").split("\n");
    let index = 0;

    const isListLine = line =>
        /^\s{0,3}(?:[-*+]\s+|\d+[.)]\s+)/.test(line);

    const isBlockStart = line =>
        /^\s*```/.test(line) ||
        /^\s{0,3}#{1,6}\s+/.test(line) ||
        /^\s{0,3}>/.test(line) ||
        /^\s{0,3}(?:[-*_]\s*){3,}$/.test(line) ||
        isListLine(line);

    const splitTableRow = line =>
        line.trim().replace(/^\|/, "").replace(/\|$/, "")
            .split("|").map(cell => cell.trim());

    while (index < lines.length) {

        if (!lines[index].trim()) {
            index += 1;
            continue;
        }

        const fence = lines[index].match(/^\s*```([^`]*)$/);
        if (fence) {
            const language = fence[1].trim().split(/\s+/)[0] || "";
            index += 1;
            const codeLines = [];
            while (index < lines.length && !/^\s*```\s*$/.test(lines[index])) {
                codeLines.push(lines[index]);
                index += 1;
            }
            if (index < lines.length) index += 1;

            const block = document.createElement("div");
            block.className = "markdown-code-block";
            const toolbar = document.createElement("div");
            toolbar.className = "markdown-code-toolbar";
            const languageLabel = document.createElement("span");
            languageLabel.textContent = language || "Code";
            const copyButton = document.createElement("button");
            copyButton.type = "button";
            copyButton.className = "markdown-copy-button";
            copyButton.textContent = "Copy";
            copyButton.setAttribute("aria-label", "Copy code block");
            const codeText = codeLines.join("\n");
            copyButton.addEventListener("click", async () => {
                try {
                    await navigator.clipboard.writeText(codeText);
                    copyButton.textContent = "Copied";
                } catch {
                    copyButton.textContent = "Copy failed";
                }
            });
            toolbar.append(languageLabel, copyButton);

            const pre = document.createElement("pre");
            const code = document.createElement("code");
            code.textContent = codeText;
            pre.appendChild(code);
            block.append(toolbar, pre);
            container.appendChild(block);
            continue;
        }

        const heading = lines[index].match(/^\s{0,3}(#{1,6})\s+(.+?)\s*#*\s*$/);
        if (heading) {
            const element = document.createElement(`h${heading[1].length}`);
            appendInlineMarkdown(element, heading[2]);
            container.appendChild(element);
            index += 1;
            continue;
        }

        if (/^\s{0,3}(?:[-*_]\s*){3,}$/.test(lines[index])) {
            container.appendChild(document.createElement("hr"));
            index += 1;
            continue;
        }

        if (
            index + 1 < lines.length &&
            lines[index].includes("|") &&
            /^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(lines[index + 1])
        ) {
            const headers = splitTableRow(lines[index]);
            index += 2;
            const table = document.createElement("table");
            const thead = document.createElement("thead");
            const headerRow = document.createElement("tr");
            headers.forEach(text => {
                const cell = document.createElement("th");
                appendInlineMarkdown(cell, text);
                headerRow.appendChild(cell);
            });
            thead.appendChild(headerRow);
            table.appendChild(thead);

            const tbody = document.createElement("tbody");
            while (index < lines.length && lines[index].includes("|")) {
                const cells = splitTableRow(lines[index]);
                const row = document.createElement("tr");
                headers.forEach((_, cellIndex) => {
                    const cell = document.createElement("td");
                    appendInlineMarkdown(cell, cells[cellIndex] || "");
                    row.appendChild(cell);
                });
                tbody.appendChild(row);
                index += 1;
            }
            table.appendChild(tbody);
            container.appendChild(table);
            continue;
        }

        if (/^\s{0,3}>/.test(lines[index])) {
            const quoteLines = [];
            while (index < lines.length && /^\s{0,3}>/.test(lines[index])) {
                quoteLines.push(lines[index].replace(/^\s{0,3}> ?/, ""));
                index += 1;
            }
            const quote = document.createElement("blockquote");
            renderMarkdownBlocks(quote, quoteLines.join("\n"));
            container.appendChild(quote);
            continue;
        }

        if (isListLine(lines[index])) {
            const ordered = /^\s{0,3}\d+[.)]\s+/.test(lines[index]);
            const list = document.createElement(ordered ? "ol" : "ul");
            while (index < lines.length && isListLine(lines[index])) {
                const item = lines[index].replace(
                    /^\s{0,3}(?:[-*+]\s+|\d+[.)]\s+)/,
                    ""
                );
                const listItem = document.createElement("li");
                appendInlineMarkdown(listItem, item);
                list.appendChild(listItem);
                index += 1;
            }
            container.appendChild(list);
            continue;
        }

        const paragraphLines = [lines[index]];
        index += 1;
        while (
            index < lines.length &&
            lines[index].trim() &&
            !isBlockStart(lines[index]) &&
            !(index + 1 < lines.length && lines[index].includes("|") && /^\s*\|?\s*:?-{3,}/.test(lines[index + 1]))
        ) {
            paragraphLines.push(lines[index]);
            index += 1;
        }
        const paragraph = document.createElement("p");
        paragraphLines.forEach((line, lineIndex) => {
            if (lineIndex > 0) paragraph.appendChild(document.createElement("br"));
            appendInlineMarkdown(paragraph, line);
        });
        container.appendChild(paragraph);
    }
}


function markdownNodeToPlainText(node) {
    if (node.nodeType === Node.TEXT_NODE) {
        return node.nodeValue;
    }
    if (node.nodeType !== Node.ELEMENT_NODE) {
        return "";
    }

    const tag = node.tagName.toLowerCase();
    if (node.classList.contains("markdown-code-toolbar")) {
        return "";
    }
    if (tag === "br") {
        return "\n";
    }
    if (tag === "pre") {
        return `${node.textContent}\n\n`;
    }
    if (tag === "ul" || tag === "ol") {
        const items = [...node.children].filter(child => child.tagName === "LI");
        return items.map((item, index) => {
            const marker = tag === "ul" ? "• " : `${index + 1}. `;
            return `${marker}${markdownNodeToPlainText(item).trim()}\n`;
        }).join("") + "\n";
    }
    if (tag === "li") {
        return [...node.childNodes].map(markdownNodeToPlainText).join("");
    }
    if (tag === "tr") {
        return [...node.children].map(markdownNodeToPlainText).join(" | ") + "\n";
    }

    const content = [...node.childNodes].map(markdownNodeToPlainText).join("");
    if (/^h[1-6]$/.test(tag) || ["p", "blockquote", "table"].includes(tag)) {
        return `${content.trim()}\n\n`;
    }
    if (tag === "hr") {
        return "\n";
    }
    if (tag === "a") {
        const label = content.trim();
        const href = node.getAttribute("href");
        return href && label !== href ? `${label} (${href})` : label;
    }
    return content;
}


function addMarkdownCopyActions(container, markdown) {
    const plainText = [...container.childNodes]
        .map(markdownNodeToPlainText)
        .join("")
        .trim();
    const actions = document.createElement("div");
    actions.className = "message-copy-actions";

    [
        { label: "Copy Md", value: markdown },
        { label: "Copy Txt", value: plainText }
    ].forEach(({ label, value }) => {
        const copyButton = document.createElement("button");
        copyButton.type = "button";
        copyButton.className = "message-copy-button";
        copyButton.textContent = label;
        copyButton.addEventListener("click", async () => {
            try {
                await navigator.clipboard.writeText(value);
                copyButton.textContent = "Copied";
            } catch {
                copyButton.textContent = "Copy failed";
            }
            window.setTimeout(() => {
                copyButton.textContent = label;
            }, 1400);
        });
        actions.appendChild(copyButton);
    });

    container.appendChild(actions);
}


function renderMarkdown(container, markdown, includeCopyActions = false) {
    const markdownSource = String(markdown ?? "");
    container.replaceChildren();
    renderMarkdownBlocks(container, markdownSource);
    if (includeCopyActions) {
        addMarkdownCopyActions(container, markdownSource);
    }
}


function createKnowledgeStatus(sources) {
    if (!Array.isArray(sources) || sources.length === 0) return null;
    const validSources = sources.map(source => {
        if (Array.isArray(source)) {
            return { source: source[0], distance: source[1] };
        }
        return typeof source === "string" ? { source } : source;
    }).filter(source =>
        source && typeof source === "object" && (source.filename || source.source || source.path)
    );
    if (validSources.length === 0) return null;

    const sourceDetails = document.createElement("details");
    sourceDetails.className = "message-sources";
    const summary = document.createElement("summary");
    summary.textContent = `Knowledge sources · ${validSources.length}`;
    const sourceList = document.createElement("ul");
    validSources.forEach(source => {
        const item = document.createElement("li");
        const sourceName = document.createElement("strong");
        sourceName.textContent = source.filename || source.source || source.path;
        item.appendChild(sourceName);
        if (source.filename && source.path && source.path !== source.filename) {
            const path = document.createElement("span");
            path.className = "source-path";
            path.textContent = ` · ${source.path}`;
            item.appendChild(path);
        }
        if (source.excerpt) {
            const excerpt = document.createElement("p");
            excerpt.className = "source-excerpt";
            excerpt.textContent = source.excerpt;
            item.appendChild(excerpt);
        }
        if (typeof source.distance === "number") {
            const distance = document.createElement("span");
            distance.className = "source-distance";
            distance.textContent = ` · squared L2 distance ${source.distance}`;
            item.appendChild(distance);
        }
        sourceList.appendChild(item);
    });
    sourceDetails.append(summary, sourceList);
    return sourceDetails;
}


function createMemoryContextStatus(memories) {
    if (!Array.isArray(memories) || memories.length === 0) return null;

    const memoryDetails = document.createElement("details");
    memoryDetails.className = "message-sources message-memory-context";
    const summary = document.createElement("summary");
    summary.textContent = `Memory context · ${memories.length}`;
    const memoryList = document.createElement("ul");
    memories.forEach(memory => {
        const item = document.createElement("li");
        item.textContent = typeof memory === "string" ? memory : memory.memory || "Saved memory";
        memoryList.appendChild(item);
    });
    memoryDetails.append(summary, memoryList);
    return memoryDetails;
}


function addMessage(text, type, includeCopyActions = type === "assistant", image = null, sources, memoryContext) {

    const message =
        document.createElement("div");

    message.className =
        `message ${type}`;


    const bubble =
        document.createElement("div");

    bubble.className = "bubble";

    if (type === "assistant") {
        renderMarkdown(bubble, text, includeCopyActions);
    } else {
        bubble.textContent = text;
        if (image) {
            const attachment = document.createElement("div");
            attachment.className = "chat-message-attachment";
            if (image.previewUrl) {
                const thumbnail = document.createElement("img");
                thumbnail.src = image.previewUrl;
                thumbnail.alt = `Attached image: ${image.name}`;
                attachment.appendChild(thumbnail);
            } else {
                const indicator = document.createElement("span");
                indicator.className = "chat-message-attachment-indicator";
                indicator.textContent = `🖼 Image attached${image.name ? ` · ${image.name}` : ""}`;
                attachment.appendChild(indicator);
            }
            message.appendChild(attachment);
        }
    }


    message.appendChild(bubble);

    if (type === "assistant") {
        const knowledgeStatus = createKnowledgeStatus(sources);
        if (knowledgeStatus) message.appendChild(knowledgeStatus);
        const memoryStatus = createMemoryContextStatus(memoryContext);
        if (memoryStatus) message.appendChild(memoryStatus);
    }

    chat.appendChild(message);

    chat.scrollTop =
        chat.scrollHeight;


    return bubble;
}


function renderConversation() {

    chat.innerHTML = "";

    const conversation =
        getCurrentConversation();


    if (!conversation) {

        chatTitle.textContent =
            "New chat";

        const welcome =
            document.createElement("div");

        welcome.className = "welcome";

        welcome.innerHTML = `
            <h2>How can I help?</h2>
            <p>
                Ask me about your knowledge, AWS learning,
                LinkedIn content, or anything else.
            </p>
        `;

        chat.appendChild(welcome);

        return;
    }


    chatTitle.textContent =
        conversation.title;


    if (conversation.messages.length === 0) {

        const welcome =
            document.createElement("div");

        welcome.className = "welcome";

        welcome.innerHTML = `
            <h2>How can I help?</h2>
            <p>
                Ask me about your knowledge, AWS learning,
                LinkedIn content, or anything else.
            </p>
        `;

        chat.appendChild(welcome);

        return;
    }


    conversation.messages.forEach(
        (message, index) => {
            const bubble = addMessage(
                message.content,
                message.role,
                message.role === "assistant" && message.status !== "pending",
                message.image,
                message.sources,
                message.memory_context
            );
            bubble.parentElement.dataset.messageIndex = String(index);

            if (message.role === "assistant" && message.status === "failed") {
                const retryButton = document.createElement("button");
                retryButton.type = "button";
                retryButton.className = "message-retry-button";
                retryButton.textContent = "↻ Try again";
                retryButton.addEventListener("click", () => {
                    retryFailedAssistant(conversation, index);
                });
                bubble.parentElement.appendChild(retryButton);
            }

        }
    );

    if (pendingSearchMessageIndex !== null) {
        const target = chat.querySelector(`[data-message-index="${pendingSearchMessageIndex}"]`);
        target?.scrollIntoView({ block: "center" });
        pendingSearchMessageIndex = null;
    }
}


function readBlobAsDataUrl(blob) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = () => reject(new Error("Could not prepare the selected image."));
        reader.readAsDataURL(blob);
    });
}


function canvasToBlob(canvas, quality) {
    return new Promise(resolve => canvas.toBlob(resolve, "image/jpeg", quality));
}


async function prepareChatImage(file) {
    const supportedTypes = new Set(["image/jpeg", "image/png", "image/webp", "image/gif"]);
    if (!supportedTypes.has(file.type.toLowerCase())) {
        throw new Error("Choose a JPEG, PNG, WebP, or GIF image.");
    }
    if (file.size > MAX_CHAT_IMAGE_BYTES) {
        throw new Error("Images must be 20 MB or smaller.");
    }

    let bitmap;
    try {
        bitmap = await createImageBitmap(file);
    } catch {
        throw new Error("This image could not be opened. Try a JPEG, PNG, WebP, or GIF file.");
    }

    const scale = Math.min(1, 1800 / Math.max(bitmap.width, bitmap.height));
    const canvas = document.createElement("canvas");
    canvas.width = Math.max(1, Math.round(bitmap.width * scale));
    canvas.height = Math.max(1, Math.round(bitmap.height * scale));
    const context = canvas.getContext("2d", { alpha: false });
    context.fillStyle = "#ffffff";
    context.fillRect(0, 0, canvas.width, canvas.height);
    context.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    bitmap.close();

    let compressed = await canvasToBlob(canvas, 0.86);
    if (compressed && compressed.size > 5 * 1024 * 1024) {
        compressed = await canvasToBlob(canvas, 0.68);
    }
    if (!compressed || compressed.size > 5 * 1024 * 1024) {
        throw new Error("This image is still too large after compression. Choose a smaller image.");
    }

    const dataUrl = await readBlobAsDataUrl(compressed);
    if (dataUrl.length > MAX_CHAT_IMAGE_DATA_URL_LENGTH) {
        throw new Error("This image is too large to send. Choose a smaller image.");
    }
    return {
        dataUrl,
        name: file.name || "pasted-image.jpg",
        type: "image/jpeg",
        previewUrl: URL.createObjectURL(compressed)
    };
}


function showChatImageError(message) {
    chatImagePreview.replaceChildren();
    const error = document.createElement("span");
    error.className = "chat-image-preview-name chat-image-error";
    error.textContent = message;
    chatImagePreview.appendChild(error);
    chatImagePreview.hidden = false;
}


function removePendingChatImage(revoke = true) {
    if (pendingChatImage?.previewUrl && revoke) {
        URL.revokeObjectURL(pendingChatImage.previewUrl);
    }
    pendingChatImage = null;
    chatImageInput.value = "";
    chatImagePreview.replaceChildren();
    chatImagePreview.hidden = true;
}


async function attachChatImage(file) {
    if (!file) return;
    try {
        const attachment = await prepareChatImage(file);
        removePendingChatImage();
        pendingChatImage = attachment;

        const thumbnail = document.createElement("img");
        thumbnail.src = attachment.previewUrl;
        thumbnail.alt = "Selected image preview";
        const filename = document.createElement("span");
        filename.className = "chat-image-preview-name";
        filename.textContent = attachment.name;
        const removeButton = document.createElement("button");
        removeButton.type = "button";
        removeButton.className = "chat-image-preview-remove";
        removeButton.textContent = "×";
        removeButton.setAttribute("aria-label", "Remove attached image");
        removeButton.addEventListener("click", () => removePendingChatImage());
        chatImagePreview.replaceChildren(thumbnail, filename, removeButton);
        chatImagePreview.hidden = false;
    } catch (error) {
        removePendingChatImage();
        showChatImageError(error.message);
    }
}


chatAttachButton.addEventListener("click", () => chatImageInput.click());
chatImageInput.addEventListener("change", () => attachChatImage(chatImageInput.files[0]));

input.addEventListener("paste", event => {
    const imageItem = [...(event.clipboardData?.items || [])]
        .find(item => item.kind === "file" && item.type.startsWith("image/"));
    if (!imageItem) return;
    const blob = imageItem.getAsFile();
    if (!blob) return;
    event.preventDefault();
    const extension = blob.type.split("/")[1] || "jpg";
    attachChatImage(new File([blob], `pasted-image.${extension}`, { type: blob.type }));
});

form.addEventListener("dragover", event => {
    if ([...(event.dataTransfer?.items || [])].some(item => item.type.startsWith("image/"))) {
        event.preventDefault();
        form.classList.add("is-dragover");
    }
});

form.addEventListener("dragleave", event => {
    if (!form.contains(event.relatedTarget)) form.classList.remove("is-dragover");
});

form.addEventListener("drop", event => {
    form.classList.remove("is-dragover");
    const imageFile = [...(event.dataTransfer?.files || [])]
        .find(file => file.type.startsWith("image/"));
    if (!imageFile) return;
    event.preventDefault();
    attachChatImage(imageFile);
});


/* ============================================================
   Sending messages
   ============================================================ */

function retryPayloadKey(conversationId, userIndex) {
    return `${conversationId}:${userIndex}`;
}


async function requestAssistantResponse(conversation, userIndex, assistantIndex, bubble, imageData = null) {
    const userMessage = conversation.messages[userIndex];
    const assistantMessage = conversation.messages[assistantIndex];
    button.disabled = true;

    try {
        const response = await fetch("/api/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                message: userMessage.content,
                image: imageData,
                history: conversation.messages
                    .slice(0, userIndex)
                    .filter(item => item.status !== "failed" && item.status !== "pending")
                    .slice(-10)
                    .map(item => {
                        const imageMarker = item.image
                            ? `[Image attached: ${item.image.name || "image"}]`
                            : "";
                        return {
                            role: item.role,
                            content: `${item.content.slice(-1200)}${imageMarker ? `\n${imageMarker}` : ""}`
                        };
                    })
            })
        });

        if (!response.ok) {
            throw new Error(await responseError(response, "Could not send the message."));
        }

        let streamedAnswer = "";
        const result = await consumeAssistantStream(
            response,
            status => { bubble.textContent = status; },
            text => { streamedAnswer = text; bubble.textContent = text; }
        );
        const answer = result.answer || streamedAnswer;

        assistantMessage.content = answer;
        assistantMessage.status = "complete";
        assistantMessage.sources = result.sources;
        assistantMessage.memory_context = result.memoryContext;
        saveConversations();
        retryImagePayloads.delete(retryPayloadKey(conversation.id, userIndex));

        if (currentConversationId === conversation.id) {
            renderConversation();
        }
    } catch (error) {
        assistantMessage.content = error.message || "Sorry, something went wrong.";
        assistantMessage.status = "failed";
        assistantMessage.sources = [];
        assistantMessage.memory_context = [];
        saveConversations();
        console.error(error);

        if (currentConversationId === conversation.id) {
            renderConversation();
        }
    } finally {
        button.disabled = false;
        input.focus();
    }
}


async function retryFailedAssistant(conversation, assistantIndex) {
    if (button.disabled) return;

    const assistantMessage = conversation.messages[assistantIndex];
    const userIndex = assistantIndex - 1;
    const userMessage = conversation.messages[userIndex];
    if (
        assistantMessage.status !== "failed" ||
        !userMessage ||
        userMessage.role !== "user"
    ) {
        return;
    }

    assistantMessage.content = "Thinking...";
    assistantMessage.status = "pending";
    assistantMessage.sources = [];
    assistantMessage.memory_context = [];
    renderConversation();

    const bubble = chat.querySelector(`[data-message-index="${assistantIndex}"] .bubble`);
    await requestAssistantResponse(
        conversation,
        userIndex,
        assistantIndex,
        bubble,
        retryImagePayloads.get(retryPayloadKey(conversation.id, userIndex)) || null
    );
}


form.addEventListener(
    "submit",
    async event => {

        event.preventDefault();
        if (button.disabled) return;

        const message =
            input.value.trim();


        const attachment = pendingChatImage;
        if (!message && !attachment) {
            return;
        }


        if (!currentConversationId) {
            createConversation();
        }


        const conversation =
            getCurrentConversation();


        const userMessage = {
            role: "user",
            content: message,
            ...(attachment ? {
                image: {
                    name: attachment.name,
                    type: attachment.type
                }
            } : {})
        };
        conversation.messages.push(userMessage);
        const userIndex = conversation.messages.length - 1;


        /*
         * Use the first user message as the
         * conversation title.
         */

        if (
            conversation.title ===
            "New chat"
        ) {

            conversation.title =
                !message && attachment
                    ? "Image"
                    : message.length > 35
                    ? message.slice(0, 35) + "..."
                    : message;
        }


        saveConversations();

        renderConversationList();

        addMessage(
            message,
            "user",
            false,
            attachment ? { name: attachment.name, type: attachment.type } : null
        );


        input.value = "";

        const assistantMessage = {
            role: "assistant",
            content: "Thinking...",
            status: "pending"
        };
        conversation.messages.push(assistantMessage);
        const assistantIndex = conversation.messages.length - 1;
        const thinkingBubble = addMessage("Thinking...", "assistant", false);
        thinkingBubble.parentElement.dataset.messageIndex = String(assistantIndex);
        if (attachment) {
            retryImagePayloads.set(retryPayloadKey(conversation.id, userIndex), attachment.dataUrl);
        }

        await requestAssistantResponse(
            conversation,
            userIndex,
            assistantIndex,
            thinkingBubble,
            attachment?.dataUrl || null
        );
        removePendingChatImage();

    }
);


/* ============================================================
   Keyboard behaviour
   ============================================================ */

input.addEventListener(
    "keydown",
    event => {

        if (
            event.key === "Enter" &&
            !event.shiftKey
        ) {

            event.preventDefault();

            form.requestSubmit();

        }

    }
);

/* ============================================================
   New chat
   ============================================================ */

newChatButton.addEventListener(
    "click",
    () => {

        createConversation();

        sidebar.classList.remove("open");

    }
);

/* ============================================================
   Mobile sidebar
   ============================================================ */

mobileMenu.addEventListener(
    "click",
    () => {

        sidebar.classList.toggle(
            "open"
        );

    }
);

conversationSearchInput.addEventListener("input", renderConversationList);
clearConversationSearch.addEventListener("click", () => {
    conversationSearchInput.value = "";
    renderConversationList();
    conversationSearchInput.focus();
});


/* ============================================================
   Startup
   ============================================================ */

if (conversations.length > 0) {

    currentConversationId =
        conversations[0].id;

}

renderConversationList();

function compactTokenCount(value) {
    return new Intl.NumberFormat(undefined, {
        notation: "compact",
        maximumFractionDigits: 1
    }).format(value);
}

async function refreshUsageMonitor() {
    try {
        const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
        const response = await fetch(`/api/usage?timezone=${encodeURIComponent(timezone)}`);
        if (!response.ok) {
            throw new Error("Failed to load usage summary");
        }

        const usage = await response.json();
        usageClock.querySelector(".usage-value").innerHTML =
            `<span aria-hidden="true">🕐</span> ${usage.local_time}`;
        usagePeak.textContent = usage.peak_status;
        usageClock.classList.toggle("is-peak", usage.peak);
        usageClock.classList.toggle("is-off-peak", !usage.peak);
        usageMonthValue.innerHTML =
            `<span aria-hidden="true">🪙</span> ${compactTokenCount(usage.month_tokens)}`;
        usageAverageValue.innerHTML =
            `<span aria-hidden="true">📊</span> ${compactTokenCount(usage.daily_average_tokens)}`;
        usageMonth.classList.toggle("is-warning", usage.monthly_warning);
    } catch (error) {
        console.error("Could not refresh usage monitor:", error);
    }
}

refreshUsageMonitor();
setInterval(refreshUsageMonitor, 30_000);

renderConversation();


/* ============================================================
   Memories
   ============================================================ */

async function loadMemories() {

    memoryList.innerHTML =
        "<p>Loading memories...</p>";

    try {

        const response =
            await fetch("/api/memories");

        if (!response.ok) {
            throw new Error("Failed to load memories");
        }

        const data =
            await response.json();

        renderMemories(data.memories);

    } catch (error) {

        memoryList.innerHTML =
            "<p>Could not load memories.</p>";

        console.error(error);
    }
}


function renderMemories(memories) {

    memoryList.innerHTML = "";


    if (memories.length === 0) {

        memoryList.innerHTML =
            "<p>No saved memories.</p>";

        return;
    }


    memories.forEach(memory => {

        const item =
            document.createElement("div");

        item.className = "memory-item";


        const content =
            document.createElement("div");

        content.className = "memory-content";


        const text =
            document.createElement("div");

        text.className = "memory-text";

        text.textContent =
            memory.memory;


        const meta =
            document.createElement("div");

        meta.className = "memory-meta";

        meta.textContent =
            `${memory.category} • ${memory.memory_type}`;


        content.appendChild(text);

        content.appendChild(meta);


        const deleteButton =
            document.createElement("button");

        deleteButton.className =
            "delete-memory";

        deleteButton.textContent =
            "×";

        deleteButton.title =
            "Delete memory";


        deleteButton.addEventListener(
            "click",
            () => deleteMemory(memory.id)
        );


        item.appendChild(content);

        item.appendChild(deleteButton);

        memoryList.appendChild(item);

    });
}


async function deleteMemory(memoryId) {

    if (!confirm("Delete this memory?")) {
        return;
    }


    try {

        const response =
            await fetch(
                `/api/memories/${memoryId}`,
                {
                    method: "DELETE"
                }
            );


        if (!response.ok) {
            throw new Error(
                "Failed to delete memory"
            );
        }


        await loadMemories();

    } catch (error) {

        alert("Could not delete memory.");

        console.error(error);
    }
}


async function saveManualMemory() {

    const memory =
        memoryInput.value.trim();


    if (!memory) {
        return;
    }


    saveMemoryButton.disabled = true;


    try {

        const response =
            await fetch(
                "/api/memories",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({
                        memory: memory
                    })
                }
            );


        if (!response.ok) {
            throw new Error(
                "Failed to save memory"
            );
        }


        memoryInput.value = "";

        await loadMemories();


    } catch (error) {

        alert("Could not save memory.");

        console.error(error);

    } finally {

        saveMemoryButton.disabled = false;

    }
}


memoriesButton.addEventListener(
    "click",
    async () => {
        showView("memories");

        await loadMemories();

    }
);

/* ============================================================
   Settings
   ============================================================ */

async function loadSettings() {

    try {

        const response = await fetch("/api/settings");

        if (!response.ok) {
            throw new Error("Failed to load settings");
        }

        const settings = await response.json();
        automaticMemory.checked = settings.automatic_memory;
        ragEnabled.checked = settings.rag_enabled;
        memoryDebug.checked = settings.memory_debug;
        globalPrompt.value = settings.global_prompt || "";
        linkedinPromptDefaults = settings.linkedin_prompt_defaults || {};
        linkedinPrompts = settings.linkedin_prompts || {};
        linkedinPromptInput.value = linkedinPrompts[activeLinkedInAction]
            ?? linkedinPromptDefaults[activeLinkedInAction]
            ?? "";

    } catch (error) {

        alert("Could not load settings.");
        console.error(error);
    }
}

async function saveSetting(name, value) {

    try {

        const response = await fetch(
            "/api/settings",
            {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ [name]: value })
            }
        );

        if (!response.ok) {
            throw new Error("Failed to save setting");
        }

    } catch (error) {

        alert("Could not save setting.");
        await loadSettings();
        console.error(error);
    }
}

async function saveGlobalPrompt() {
    saveGlobalPromptButton.disabled = true;
    globalPromptStatus.textContent = "Saving...";
    try {
        const response = await fetch("/api/settings", {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ global_prompt: globalPrompt.value })
        });
        if (!response.ok) {
            throw new Error("Failed to save Global Prompt");
        }
        globalPromptStatus.textContent = "Saved.";
    } catch (error) {
        globalPromptStatus.textContent = "Could not save Global Prompt.";
        console.error(error);
    } finally {
        saveGlobalPromptButton.disabled = false;
    }
}


async function saveLinkedInPrompt(promptValue = linkedinPromptInput.value) {
    linkedinPromptStatus.textContent = "Saving...";
    try {
        const response = await fetch("/api/settings", {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                linkedin_prompts: { [activeLinkedInAction]: promptValue }
            })
        });
        if (!response.ok) throw new Error("Could not save tool prompt.");
        linkedinPrompts[activeLinkedInAction] = promptValue;
        linkedinPromptInput.value = promptValue;
        linkedinPromptStatus.textContent = "Saved.";
    } catch (error) {
        linkedinPromptStatus.textContent = error.message;
        console.error(error);
    }
}


settingsButton.addEventListener(
    "click",
    async () => {
        showView("settings");
        await loadSettings();
    }
);


closeSettings.addEventListener("click", () => showView("chat"));

memoryDebug.addEventListener(
    "change",
    () => saveSetting(
        "memory_debug",
        memoryDebug.checked
    )
);

saveGlobalPromptButton.addEventListener("click", saveGlobalPrompt);
document.getElementById("save-linkedin-prompt").addEventListener("click", () => saveLinkedInPrompt());
document.getElementById("reset-linkedin-prompt").addEventListener("click", () => {
    const defaultPrompt = linkedinPromptDefaults[activeLinkedInAction] || "";
    saveLinkedInPrompt(defaultPrompt);
});
document.getElementById("hide-linkedin-prompt").addEventListener("click", () => {
    linkedinPromptEditor.open = false;
});


closeMemories.addEventListener(
    "click",
    () => showView("chat")
);


saveMemoryButton.addEventListener(
    "click",
    saveManualMemory
);


/* ============================================================
   Knowledge
   ============================================================ */

function formatFileSize(size) {

    if (size < 1024) {
        return `${size} B`;
    }

    if (size < 1024 * 1024) {
        return `${(size / 1024).toFixed(1)} KB`;
    }

    return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}


async function responseError(response, fallback) {

    try {
        const data = await response.json();
        return data.detail || fallback;
    } catch (error) {
        return fallback;
    }
}


async function loadKnowledge(folder = currentKnowledgeFolder) {
    currentKnowledgeFolder = folder;
    knowledgeList.textContent = "Loading Knowledge...";
    try {
        const response = await fetch(`/api/knowledge?path=${encodeURIComponent(folder)}`);
        if (!response.ok) {
            throw new Error(await responseError(response, "Could not load Knowledge."));
        }
        const data = await response.json();
        knowledgeEntries = data.entries;
        renderKnowledge(data.entries, data.path);
        knowledgeStatus.textContent = "";
    } catch (error) {
        knowledgeList.textContent = error.message;
        console.error(error);
    }
}


function renderKnowledge(entries, folder) {
    knowledgeBreadcrumbs.replaceChildren();
    const rootLink = document.createElement("button");
    rootLink.type = "button";
    rootLink.textContent = "📚 Knowledge";
    rootLink.addEventListener("click", () => loadKnowledge(""));
    knowledgeBreadcrumbs.appendChild(rootLink);

    const parts = folder ? folder.split("/") : [];
    let accumulated = "";
    parts.forEach((part, index) => {
        const separator = document.createElement("span");
        separator.textContent = "/";
        separator.setAttribute("aria-hidden", "true");
        knowledgeBreadcrumbs.appendChild(separator);
        accumulated = accumulated ? `${accumulated}/${part}` : part;
        const crumb = document.createElement("button");
        crumb.type = "button";
        const labels = { linkedin: "LinkedIn" };
        crumb.textContent = labels[part] || part;
        const destination = accumulated;
        crumb.setAttribute("aria-current", index === parts.length - 1 ? "page" : "false");
        crumb.addEventListener("click", () => loadKnowledge(destination));
        knowledgeBreadcrumbs.appendChild(crumb);
    });

    knowledgeList.replaceChildren();
    if (!entries.length) {
        const empty = document.createElement("p");
        empty.className = "knowledge-empty";
        empty.textContent = "This folder is empty.";
        knowledgeList.appendChild(empty);
        return;
    }

    entries.forEach(entry => {
        const item = document.createElement("div");
        item.className = `knowledge-item ${entry.type === "folder" ? "is-folder" : "is-file"}`;

        const openButton = document.createElement("button");
        openButton.type = "button";
        openButton.className = "knowledge-open";
        const icon = document.createElement("span");
        icon.className = "knowledge-entry-icon";
        icon.textContent = entry.type === "folder" ? "📁" : entry.extension === ".pdf" ? "📕" : "📄";
        const name = document.createElement("span");
        name.className = "knowledge-name";
        const rootFolderLabels = {
            aws: "AWS",
            linkedin: "LinkedIn",
            documents: "Documents",
            other: "Other"
        };
        name.textContent = currentKnowledgeFolder
            ? entry.name
            : (rootFolderLabels[entry.path] || entry.name);
        openButton.setAttribute("aria-label", `${entry.type === "folder" ? "Open folder" : "File"} ${name.textContent}`);
        openButton.append(icon, name);
        if (entry.type === "folder") {
            openButton.addEventListener("click", () => loadKnowledge(entry.path));
        } else {
            openButton.disabled = true;
        }

        const meta = document.createElement("span");
        meta.className = "knowledge-meta";
        meta.textContent = entry.type === "folder"
            ? "Folder"
            : `${entry.extension} · ${formatFileSize(entry.size)} · ${entry.indexed ? "Indexed" : "Not indexed"}`;

        const actions = document.createElement("div");
        actions.className = "knowledge-actions";
        if (entry.type === "file") {
            const reindexButton = document.createElement("button");
            reindexButton.type = "button";
            reindexButton.className = "knowledge-action";
            reindexButton.textContent = "Re-index";
            reindexButton.addEventListener("click", () => reindexKnowledge(entry.path));
            actions.appendChild(reindexButton);
        }

        const moveButton = document.createElement("button");
        moveButton.type = "button";
        moveButton.className = "knowledge-action";
        moveButton.textContent = "Move";
        moveButton.addEventListener("click", () => openKnowledgeMoveDialog(entry));

        const renameButton = document.createElement("button");
        renameButton.type = "button";
        renameButton.className = "knowledge-action";
        renameButton.textContent = "Rename";
        renameButton.addEventListener("click", () => renameKnowledge(entry));

        const deleteButton = document.createElement("button");
        deleteButton.type = "button";
        deleteButton.className = "knowledge-action delete";
        deleteButton.textContent = "Delete";
        deleteButton.addEventListener("click", () => deleteKnowledge(entry));

        actions.append(moveButton, renameButton, deleteButton);
        item.append(openButton, meta, actions);
        knowledgeList.appendChild(item);
    });
}


async function openKnowledgeMoveDialog(entry) {
    try {
        const response = await fetch("/api/knowledge/folders");
        if (!response.ok) throw new Error("Could not load destination folders.");
        const { folders } = await response.json();
        knowledgeMoveDestination.replaceChildren();
        folders
            .filter(folder => !(entry.type === "folder" && (folder === entry.path || folder.startsWith(`${entry.path}/`))))
            .forEach(folder => {
                const option = document.createElement("option");
                option.value = folder;
                option.textContent = folder ? `Knowledge/${folder}` : "Knowledge (root)";
                option.selected = folder === currentKnowledgeFolder;
                knowledgeMoveDestination.appendChild(option);
            });
        knowledgeMoveForm.dataset.path = entry.path;
        knowledgeMoveDialog.showModal();
    } catch (error) {
        knowledgeStatus.textContent = error.message;
    }
}


async function renameKnowledge(entry) {
    const name = prompt("Enter a new name:", entry.name);
    if (!name || name === entry.name) return;
    await mutateKnowledge("/api/knowledge/rename", "PATCH", { path: entry.path, name }, "Item renamed.");
}


async function mutateKnowledge(url, method, body, successMessage) {
    knowledgeStatus.textContent = "Updating Knowledge...";
    try {
        const response = await fetch(url, {
            method,
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body)
        });
        if (!response.ok) throw new Error(await responseError(response, "Could not update Knowledge."));
        knowledgeStatus.textContent = successMessage;
        await loadKnowledge(currentKnowledgeFolder);
    } catch (error) {
        knowledgeStatus.textContent = error.message;
    }
}


knowledgeButton.addEventListener(
    "click",
    async () => {
        showView("knowledge");
        await loadKnowledge();
    }
);


closeKnowledge.addEventListener(
    "click",
    () => showView("chat")
);


knowledgeUploadForm.addEventListener(
    "submit",
    async event => {
        event.preventDefault();

        const file = knowledgeFile.files[0];
        if (!file) {
            return;
        }

        uploadKnowledgeButton.disabled = true;
        knowledgeStatus.textContent = "Uploading and indexing...";

        try {
            const query = new URLSearchParams({
                folder: currentKnowledgeFolder,
                filename: file.name
            });
            const response = await fetch(`/api/knowledge/upload?${query}`, {
                method: "POST",
                body: file
            });

            if (!response.ok) {
                throw new Error(
                    await responseError(response, "Could not upload the file.")
                );
            }

            knowledgeFile.value = "";
            knowledgeStatus.textContent = "Uploaded and indexed.";
            await loadKnowledge(currentKnowledgeFolder);

        } catch (error) {
            knowledgeStatus.textContent = error.message;
            console.error(error);

        } finally {
            uploadKnowledgeButton.disabled = false;
        }
    }
);


knowledgeCreateFolderForm.addEventListener("submit", async event => {
    event.preventDefault();
    const name = knowledgeFolderName.value.trim();
    if (!name) return;
    knowledgeStatus.textContent = "Creating folder...";
    try {
        const response = await fetch("/api/knowledge/folders", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ parent: currentKnowledgeFolder, name })
        });
        if (!response.ok) throw new Error(await responseError(response, "Could not create folder."));
        knowledgeFolderName.value = "";
        knowledgeStatus.textContent = "Folder created.";
        await loadKnowledge(currentKnowledgeFolder);
    } catch (error) {
        knowledgeStatus.textContent = error.message;
    }
});


knowledgeMoveForm.addEventListener("submit", async event => {
    event.preventDefault();
    const path = knowledgeMoveForm.dataset.path;
    const destinationFolder = knowledgeMoveDestination.value;
    knowledgeMoveDialog.close();
    await mutateKnowledge(
        "/api/knowledge/move",
        "PATCH",
        { path, destination_folder: destinationFolder },
        "Item moved. Knowledge index updated."
    );
});


document.getElementById("knowledge-move-cancel").addEventListener("click", () => {
    knowledgeMoveDialog.close();
});


async function reindexKnowledge(path) {

    knowledgeStatus.textContent = "Re-indexing file...";

    try {
        const response = await fetch("/api/knowledge/reindex", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ path })
        });

        if (!response.ok) {
            throw new Error(
                await responseError(response, "Could not re-index the file.")
            );
        }

        knowledgeStatus.textContent = "File re-indexed.";
        await loadKnowledge();

    } catch (error) {
        knowledgeStatus.textContent = error.message;
        console.error(error);
    }
}


async function reindexAllKnowledge() {
    const originalLabel = reindexAllKnowledgeButton.textContent;
    reindexAllKnowledgeButton.disabled = true;
    reindexAllKnowledgeButton.textContent = "Re-indexing...";
    knowledgeStatus.textContent = "Re-indexing all supported Knowledge files. This may take a few minutes...";

    try {
        const response = await fetch("/api/knowledge/reindex-all", { method: "POST" });
        if (!response.ok) {
            throw new Error(await responseError(response, "Could not re-index all Knowledge files."));
        }
        const result = await response.json();
        await loadKnowledge(currentKnowledgeFolder);
        knowledgeStatus.textContent = `Re-index complete. ${result.indexed_files} files are indexed.`;
    } catch (error) {
        knowledgeStatus.textContent = error.message;
    } finally {
        reindexAllKnowledgeButton.disabled = false;
        reindexAllKnowledgeButton.textContent = originalLabel;
    }
}


reindexAllKnowledgeButton.addEventListener("click", reindexAllKnowledge);


async function deleteKnowledge(file) {

    const promptText = file.type === "folder"
        ? `Delete folder ${file.name} and everything inside it? Indexed files will be removed from Knowledge search.`
        : `Delete ${file.name} and remove it from the Knowledge index?`;
    if (!confirm(promptText)) {
        return;
    }

    knowledgeStatus.textContent = "Deleting Knowledge item and updating index...";

    try {
        const response = await fetch(
            `/api/knowledge/${file.path.split("/").map(encodeURIComponent).join("/")}`,
            { method: "DELETE" }
        );

        if (!response.ok) {
            throw new Error(
                await responseError(response, "Could not delete the file.")
            );
        }

        knowledgeStatus.textContent = "Item deleted. Knowledge index updated.";
        await loadKnowledge(currentKnowledgeFolder);

    } catch (error) {
        knowledgeStatus.textContent = error.message;
        console.error(error);
    }
}


linkedinTools.forEach(toolButton => {
    toolButton.addEventListener("click", () => {
        saveActiveLinkedInDraft();
        activeLinkedInAction = toolButton.dataset.action;
        const options = linkedinToolOptions[activeLinkedInAction];

        linkedinTools.forEach(button => button.classList.remove("active"));
        toolButton.classList.add("active");
        restoreLinkedInDraft(activeLinkedInAction);
        linkedinInputLabel.textContent = options.label;
        linkedinInput.placeholder = options.placeholder;
        linkedinInstructionsField.hidden = !options.instructionsLabel;
        linkedinPerformanceField.hidden = !options.performanceLabel;
        if (options.instructionsLabel) {
            linkedinInstructionsLabel.textContent = options.instructionsLabel;
            linkedinInstructionsInput.placeholder = options.instructionsPlaceholder;
        }
        linkedinSubmit.textContent = options.submit;
        linkedinStatus.textContent = "";
        linkedinResult.textContent = "Your result will appear here.";
        linkedinPromptInput.value = linkedinPrompts[activeLinkedInAction]
            ?? linkedinPromptDefaults[activeLinkedInAction]
            ?? "";
        linkedinPromptStatus.textContent = "";
        renderLinkedInHistory();
    });
});


document.getElementById("linkedin-new-session").addEventListener("click", () => {
    startLinkedInSession();
});


linkedinImagesInput.addEventListener("change", () => {
    const files = [...linkedinImagesInput.files];
    const totalBytes = files.reduce((sum, file) => sum + file.size, 0);
    if (files.length > 4 || totalBytes > 8_500_000) {
        linkedinImagesInput.value = "";
        linkedinComposerState().files = [];
        linkedinImageStatus.textContent = "Choose up to four images totalling no more than 8 MB.";
        return;
    }
    linkedinComposerState().files = files;
    linkedinImageStatus.textContent = files.length
        ? `${files.length} image${files.length === 1 ? "" : "s"} selected.`
        : "";
});


linkedinButton.addEventListener("click", async () => {
    showView("linkedin");
    await loadSettings();
    renderLinkedInHistory();
});


closeLinkedIn.addEventListener("click", () => showView("chat"));


linkedinForm.addEventListener("submit", async event => {
    event.preventDefault();

    const action = activeLinkedInAction;
    const draft = linkedinComposerState(action);
    const text = linkedinInput.value.trim();
    const instructions = ["reply_to_message", "analyze_post"].includes(action)
        ? linkedinInstructionsInput.value.trim()
        : "";
    const performanceData = action === "analyze_post"
        ? linkedinPerformanceInput.value.trim()
        : "";
    draft.text = linkedinInput.value;
    draft.instructions = linkedinInstructionsInput.value;
    draft.performanceData = linkedinPerformanceInput.value;
    if (linkedinImagesInput.files.length) {
        draft.files = [...linkedinImagesInput.files];
    }
    const files = [...draft.files];
    if (action !== "post_ideas" && !text && !files.length) {
        linkedinStatus.textContent = action === "analyze_post"
            ? "Paste or attach a LinkedIn post before running this tool."
            : "Add a request, URL, or image before running this tool.";
        linkedinInput.focus();
        return;
    }

    linkedinSubmit.disabled = true;
    linkedinStatus.textContent = action === "analyze_post"
        ? "Analysing your post with relevant saved context..."
        : "Working with your saved context...";
    linkedinResult.textContent = action === "analyze_post" ? "Analysing post..." : "Generating...";

    try {
        const images = await Promise.all(files.map(readFileAsDataUrl));
        const response = await fetch("/api/linkedin", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                action,
                text,
                instructions,
                performance_data: performanceData,
                history: [],
                images,
                prior_work: action === "post_ideas" ? recentLinkedInWork() : []
            })
        });

        if (!response.ok) {
            throw new Error(
                await responseError(response, "The LinkedIn tool could not complete the request.")
            );
        }

        let streamedResult = "";
        const streamResult = await consumeAssistantStream(
            response,
            message => {
                if (activeLinkedInAction === action) linkedinStatus.textContent = message;
            },
            text => {
                streamedResult = text;
                if (activeLinkedInAction === action) linkedinResult.textContent = text;
            }
        );
        const result = streamResult.answer;
        if (activeLinkedInAction === action) {
            renderMarkdown(linkedinResult, result || streamedResult, true);
            const knowledgeStatus = createKnowledgeStatus(streamResult.sources);
            if (knowledgeStatus) linkedinResult.appendChild(knowledgeStatus);
            const memoryStatus = createMemoryContextStatus(streamResult.memoryContext);
            if (memoryStatus) linkedinResult.appendChild(memoryStatus);
            linkedinStatus.textContent = "Done.";
        }

        const history = toolHistory(action);
        let session = history.sessions.find(item => item.id === history.activeSessionId);
        if (!session) {
            session = { id: crypto.randomUUID(), startedAt: Date.now(), records: [] };
            history.sessions.unshift(session);
            history.activeSessionId = session.id;
        }
        session.records.push({
            id: crypto.randomUUID(),
            createdAt: Date.now(),
            request: text,
            instructions,
            performance_data: performanceData,
            result: result || streamedResult,
            sources: streamResult.sources,
            memory_context: streamResult.memoryContext,
            hadImages: files.length > 0
        });
        session.records = session.records.slice(-30);
        saveLinkedInHistory();
        if (activeLinkedInAction === action) renderLinkedInHistory();

    } catch (error) {
        if (activeLinkedInAction === action) {
            linkedinResult.textContent = error.message;
            linkedinStatus.textContent = error.message;
        }
        console.error(error);

    } finally {
        linkedinSubmit.disabled = false;
    }
});