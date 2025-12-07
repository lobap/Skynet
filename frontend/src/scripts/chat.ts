/**
 * Skynet Chat Client
 * WebSocket communication and UI management
 */

// State
let conversationId: number | null = null;
let historyOffset = 0;
let hasMore = false;

// DOM Elements
const $ = (id: string) => document.getElementById(id);

// WebSocket
const ws = new WebSocket(`ws://${window.location.host}/ws`);

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadHistory();
    setupForm();
});

// API
async function loadHistory() {
    try {
        const res = await fetch('/api/chat/latest');
        const data = await res.json();

        if (data.conversation?.id && data.logs.length) {
            conversationId = data.conversation.id;
            $('session-id')!.textContent = `OP-${conversationId.toString().padStart(4, '0')}`;
            hasMore = data.has_more;
            historyOffset = data.logs.length;

            $('chat-box')!.innerHTML = '';
            if (hasMore) addLoadMoreBtn();

            data.logs.forEach((log: any) => {
                if (log.role === 'user' || log.role === 'assistant') {
                    appendMessage(log.role, log.content);
                }
            });

            scrollToBottom('messages-panel');
            logConsole(`✓ Loaded ${data.logs.length} messages`, 'text-emerald-400');
        }
    } catch (e) {
        console.error('Failed to load history:', e);
    }
}

async function loadMore() {
    if (!conversationId || !hasMore) return;

    try {
        const res = await fetch(`/api/conversations/${conversationId}/logs?limit=50&offset=${historyOffset}`);
        const data = await res.json();

        hasMore = data.has_more;
        historyOffset += data.logs.length;

        $('load-more-btn')?.remove();
        if (hasMore) addLoadMoreBtn();

        const chatBox = $('chat-box')!;
        const first = chatBox.firstChild;

        data.logs.reverse().forEach((log: any) => {
            if (log.role === 'user' || log.role === 'assistant') {
                const el = createMsgEl(log.role, log.content);
                if (first?.nextSibling) {
                    chatBox.insertBefore(el, first.nextSibling);
                } else {
                    chatBox.appendChild(el);
                }
            }
        });
    } catch (e) {
        console.error('Load more failed:', e);
    }
}

// UI Helpers
function addLoadMoreBtn() {
    const btn = document.createElement('button');
    btn.id = 'load-more-btn';
    btn.className = 'w-full py-2 text-xs text-indigo-400 hover:text-indigo-300 font-mono border border-dashed border-indigo-500/30 rounded-lg mb-4 hover:bg-indigo-500/10 transition-all';
    btn.innerText = '↑ Load older messages';
    btn.onclick = loadMore;
    $('chat-box')!.prepend(btn);
}

function createMsgEl(role: string, content: string): HTMLElement {
    const div = document.createElement('div');
    const isUser = role === 'user';
    div.className = `flex gap-3 max-w-[90%] ${isUser ? 'ml-auto flex-row-reverse' : ''} mb-4`;

    const bubble = isUser
        ? 'bg-indigo-600/90 text-white shadow-glow-indigo rounded-2xl rounded-tr-sm'
        : 'bg-black/60 border border-slate-700/50 text-slate-200 rounded-2xl rounded-tl-sm backdrop-blur-sm';

    const parsed = (typeof (window as any).marked !== 'undefined' && !isUser)
        ? (window as any).marked.parse(content)
        : content;

    div.innerHTML = `<div class="${bubble} px-5 py-3 text-sm leading-relaxed shadow-lg backdrop-blur-sm">${parsed}</div>`;
    return div;
}

function appendMessage(role: string, content: string) {
    const chatBox = $('chat-box');
    if (!chatBox) return;

    // Clear placeholder
    if (chatBox.children.length === 1 && chatBox.children[0].className.includes('text-center')) {
        chatBox.innerHTML = '';
    }

    const el = createMsgEl(role, content);
    el.classList.add('animate-slide-up');
    chatBox.appendChild(el);
    scrollToBottom('messages-panel');
}

function logConsole(text: string, cls = 'text-slate-400') {
    const console = $('agent-console');
    if (!console) return;

    const div = document.createElement('div');
    div.className = `${cls} animate-fade-in`;
    div.innerText = text;
    console.appendChild(div);
    console.scrollTop = console.scrollHeight;
}

function logTerminal(text: string, cls = 'text-slate-400') {
    const term = $('terminal-output');
    if (!term) return;

    const time = new Date().toISOString().split('T')[1].split('.')[0];
    const line = document.createElement('div');
    line.className = `font-mono whitespace-pre-wrap ${cls} text-[9px]`;
    line.innerText = `[${time}] ${text}`;
    term.appendChild(line);
    term.scrollTop = term.scrollHeight;
}

function setThinking(active: boolean) {
    const status = $('agent-status');
    if (!status) return;

    if (active) {
        status.textContent = 'PROCESSING...';
        status.className = 'px-4 py-1.5 rounded-full bg-black/60 border border-white/10 backdrop-blur-md text-[10px] font-mono text-emerald-400 animate-pulse mb-8 transition-all';
    } else {
        status.textContent = 'SYSTEM IDLE';
        status.className = 'px-4 py-1.5 rounded-full bg-black/60 border border-white/10 backdrop-blur-md text-[10px] font-mono text-slate-400 mb-8 transition-all';
    }
}

function scrollToBottom(id: string) {
    const el = $(id);
    if (el) el.scrollTop = el.scrollHeight;
}

// WebSocket Handler
ws.onmessage = (e) => {
    const data = JSON.parse(e.data);

    if (data.type === 'conversation_created') {
        conversationId = data.id;
        $('session-id')!.textContent = `OP-${data.id.toString().padStart(4, '0')}`;
        return;
    }

    switch (data.role) {
        case 'agent-thought':
            logConsole(`> ${data.content}`, 'pl-2 border-l-2 border-indigo-500/30 text-indigo-300/80');
            logTerminal(`[THOUGHT] ${data.content}`, 'text-purple-400/80');
            (window as any).positronicBrain?.fireSignal(data.content);
            setThinking(true);
            break;

        case 'agent-action':
            const isError = data.content.includes('Error');
            logConsole(`[${isError ? 'ERR' : 'EXE'}] ${data.content}`,
                `pl-2 border-l-2 ${isError ? 'border-red-500 text-red-400' : 'border-emerald-500 text-emerald-400'} font-bold`);
            logTerminal(`[ACTION] ${data.content}`, 'text-amber-400/80');
            (window as any).positronicBrain?.fireSignal(data.content);
            setThinking(true);
            break;

        case 'terminal-output':
            try {
                const term = JSON.parse(data.content);
                const termEl = $('terminal-output');
                if (!termEl) return;

                const entry = document.createElement('div');
                entry.className = 'mb-3 pb-1 font-mono text-[10px]';

                if (term.type === 'thought') {
                    entry.innerHTML = `<span class="text-slate-500 italic"># ${term.content}</span>`;
                } else {
                    const out = (term.output?.length > 500)
                        ? term.output.substring(0, 500) + '... [truncated]'
                        : (term.output || '');
                    entry.innerHTML = `
                        <div class="flex items-center gap-2 text-emerald-400 font-bold">
                            <span class="text-blue-500">root@skynet</span>:<span class="text-blue-300">~</span>$ ${term.command || 'unknown'}
                        </div>
                        <div class="mt-1 text-slate-300 whitespace-pre-wrap leading-tight pl-4 border-l-2 border-emerald-500/20 py-1">${out}</div>
                    `;
                }
                termEl.appendChild(entry);
                termEl.scrollTop = termEl.scrollHeight;
            } catch { }
            break;

        case 'assistant':
            appendMessage('assistant', data.content);
            (window as any).positronicBrain?.fireSignal(data.content);
            setThinking(false);
            break;

        case 'system':
            break;

        default:
            appendMessage(data.role, data.content);
    }
};

// Form Setup
function setupForm() {
    const form = $('chat-form');
    const input = $('prompt-input') as HTMLInputElement;

    form?.addEventListener('submit', (e) => {
        e.preventDefault();
        const goal = input?.value?.trim();
        if (!goal) return;

        appendMessage('user', goal);
        ws.send(JSON.stringify({ goal, conversation_id: conversationId }));
        input.value = '';
        setThinking(true);
    });
}

// Export for global access
(window as any).skynetChat = { appendMessage, setThinking, loadHistory };
