"""FastAPI server for Buddy Care - the customer-care / BPO surface.

Exposes:
  - POST /api/care/chat          customer support chat (SSE streaming)
  - GET  /api/care/sessions      conversation list (supervisor view)
  - GET  /api/care/conversation  full transcript for a session
  - GET  /api/care/tickets       raised tickets
  - GET  /api/care/escalations   pending human handoffs
  - GET  /api/care/analytics     volume / deflection / CSAT / sentiment
  - GET/POST /api/care/settings  persona, model, knowledge, escalation rules
  - POST /api/care/knowledge     append to the knowledge base
  - GET  /                       built-in admin dashboard + chat widget demo
"""

from __future__ import annotations

import json
import os
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import Body, FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

from buddy.care import analytics, store
from buddy.care.agent import build_support_agent
from buddy.care.settings import CareSettings, load_settings, merge_settings_update, save_settings
from buddy.code.server.app import _load_env, _normalize_event, _sse


class _State:
    """Holds settings + a per-session agent cache (keeps chat history)."""

    def __init__(self) -> None:
        self._settings: Optional[CareSettings] = None
        self._agents: Dict[str, Any] = {}
        self._lock = threading.Lock()

    @property
    def settings(self) -> CareSettings:
        if self._settings is None:
            self._settings = load_settings()
        return self._settings

    def update_settings(self, update: dict) -> CareSettings:
        with self._lock:
            self._settings = save_settings(merge_settings_update(self.settings, update))
            self._agents.clear()  # rebuild agents with new config/knowledge
        return self._settings

    def agent_for(self, session_id: str):
        with self._lock:
            agent = self._agents.get(session_id)
            if agent is None:
                agent = build_support_agent(self.settings, session_id)
                self._agents[session_id] = agent
            return agent


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    channel: str = "web"


class CsatRequest(BaseModel):
    session_id: str
    score: int
    comment: str = ""


class KnowledgeRequest(BaseModel):
    text: str


def create_app() -> FastAPI:
    _load_env()
    app = FastAPI(title="Buddy Care", version="1.0", docs_url="/api/docs")
    state = _State()

    @app.post("/api/care/chat")
    def chat(req: ChatRequest):
        session_id = req.session_id or ("web-" + uuid.uuid4().hex[:10])

        def stream():
            yield _sse({"type": "session", "session_id": session_id})
            store.log_message(session_id, "user", req.message, req.channel)

            # Keyword-based auto-escalation (defensive, in addition to the LLM tool).
            settings = state.settings
            low = req.message.lower()
            if any(k in low for k in settings.escalation_keywords):
                store.create_escalation(session_id, f"keyword match in: {req.message[:120]}",
                                         analytics.sentiment_of(req.message))

            try:
                agent = state.agent_for(session_id)
            except Exception as e:
                yield _sse({"type": "error", "content": f"Failed to build agent: {e}"})
                yield "data: [DONE]\n\n"
                return

            parts: list[str] = []
            try:
                for event in agent.run(req.message, stream=True):
                    payload = _normalize_event(event)
                    if payload:
                        if payload.get("type") == "content":
                            parts.append(payload["content"])
                        yield _sse(payload)
            except Exception as e:
                yield _sse({"type": "error", "content": str(e)})

            reply = "".join(parts).strip()
            if reply:
                store.log_message(session_id, "assistant", reply, req.channel)
            yield _sse({"type": "completed"})
            yield "data: [DONE]\n\n"

        return StreamingResponse(stream(), media_type="text/event-stream")

    @app.get("/api/care/sessions")
    def sessions(limit: int = Query(100)):
        return {"sessions": store.list_sessions(limit=limit)}

    @app.get("/api/care/conversation")
    def conversation(session_id: str = Query(...)):
        return {"session_id": session_id, "messages": store.conversation(session_id)}

    @app.get("/api/care/tickets")
    def tickets():
        return {"tickets": store.list_tickets()}

    @app.get("/api/care/escalations")
    def escalations():
        return {"escalations": store.list_escalations()}

    @app.get("/api/care/analytics")
    def get_analytics():
        return analytics.overview()

    @app.post("/api/care/csat")
    def csat(req: CsatRequest):
        store.record_csat(req.session_id, req.score, req.comment)
        return {"ok": True}

    @app.get("/api/care/settings")
    def get_settings():
        return state.settings.redacted().model_dump()

    @app.post("/api/care/settings")
    def post_settings(update: dict = Body(...)):
        return state.update_settings(update).redacted().model_dump()

    @app.post("/api/care/knowledge")
    def add_knowledge(req: KnowledgeRequest):
        current = state.settings
        merged = (current.knowledge_text + "\n\n" + req.text).strip() if current.knowledge_text else req.text.strip()
        state.update_settings({"knowledge_text": merged})
        return {"ok": True, "chars": len(merged)}

    @app.get("/", response_class=HTMLResponse)
    def index():
        return HTMLResponse(_ADMIN_HTML)

    @app.get("/widget", response_class=HTMLResponse)
    def widget():
        return HTMLResponse(_WIDGET_HTML)

    return app


def serve(host: str = "127.0.0.1", port: int = 8700, reload: bool = False) -> None:
    import uvicorn

    if reload:
        uvicorn.run("buddy.care.server.app:create_app", host=host, port=port, reload=True, factory=True)
    else:
        uvicorn.run(create_app(), host=host, port=port)


_WIDGET_HTML = """<!doctype html><html><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>Support</title><style>
*{box-sizing:border-box;font-family:system-ui,Segoe UI,Roboto,sans-serif}
body{margin:0;background:#0f1117;color:#e7e9ee;height:100vh;display:flex;flex-direction:column}
header{padding:14px 18px;background:#161922;border-bottom:1px solid #232838;font-weight:600;display:flex;align-items:center;gap:8px}
.dot{width:9px;height:9px;border-radius:50%;background:#22c55e}
#log{flex:1;overflow:auto;padding:18px;display:flex;flex-direction:column;gap:12px}
.msg{max-width:78%;padding:10px 14px;border-radius:14px;line-height:1.45;white-space:pre-wrap}
.user{align-self:flex-end;background:#3b82f6;color:#fff;border-bottom-right-radius:4px}
.bot{align-self:flex-start;background:#1d2230;border-bottom-left-radius:4px}
.chips{display:flex;flex-wrap:wrap;gap:8px;padding:0 18px 8px}
.chip{background:#1d2230;border:1px solid #2a3042;color:#cdd3df;padding:8px 12px;border-radius:20px;font-size:13px;cursor:pointer}
.chip:hover{border-color:#3b82f6}
form{display:flex;gap:8px;padding:14px;background:#161922;border-top:1px solid #232838}
input{flex:1;padding:12px 14px;border-radius:10px;border:1px solid #2a3042;background:#0f1117;color:#e7e9ee}
button{padding:12px 18px;border:0;border-radius:10px;background:#3b82f6;color:#fff;font-weight:600;cursor:pointer}
</style></head><body>
<header><span class=dot></span>Customer Support</header>
<div id=log></div>
<div class=chips id=chips></div>
<form id=f><input id=m placeholder="Type your message..." autocomplete=off>
<button>Send</button></form>
<script>
let sid=null;const log=document.getElementById('log');
function add(t,c){const d=document.createElement('div');d.className='msg '+c;d.textContent=t;log.appendChild(d);log.scrollTop=log.scrollHeight;return d}
add("Hi! I'm here to help. Ask me anything, or tap a question below.",'bot');
['What are your hours?','Where is my order?','I need a refund','Talk to a human']
 .forEach(q=>{const c=document.createElement('div');c.className='chip';c.textContent=q;
  c.onclick=()=>{document.getElementById('m').value=q;document.getElementById('f').requestSubmit();};
  document.getElementById('chips').appendChild(c);});
document.getElementById('f').onsubmit=async e=>{e.preventDefault();
 const m=document.getElementById('m');const text=m.value.trim();if(!text)return;m.value='';
 document.getElementById('chips').innerHTML='';
 add(text,'user');const bot=add('','bot');bot.textContent='...';let started=false;
 const r=await fetch('/api/care/chat',{method:'POST',headers:{'Content-Type':'application/json'},
   body:JSON.stringify({message:text,session_id:sid})});
 const reader=r.body.getReader();const dec=new TextDecoder();let buf='';
 while(true){const{value,done}=await reader.read();if(done)break;buf+=dec.decode(value,{stream:true});
  let i;while((i=buf.indexOf('\\n\\n'))>=0){const line=buf.slice(0,i);buf=buf.slice(i+2);
   if(!line.startsWith('data: '))continue;const data=line.slice(6);if(data==='[DONE]')break;
   try{const o=JSON.parse(data);if(o.type==='session')sid=o.session_id;
    if(o.type==='content'){if(!started){bot.textContent='';started=true;}bot.textContent+=o.content;}
    if(o.type==='error')bot.textContent+='\\n[error] '+o.content;}catch(_){}}}}
</script></body></html>"""


_ADMIN_HTML = """<!doctype html><html><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1"><title>Buddy Care - Console</title><style>
*{box-sizing:border-box;font-family:system-ui,Segoe UI,Roboto,sans-serif}
body{margin:0;background:#0f1117;color:#e7e9ee}
header{padding:16px 22px;background:#161922;border-bottom:1px solid #232838;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
h1{font-size:18px;margin:0;margin-right:auto}
.btn{background:#3b82f6;color:#fff;border:0;text-decoration:none;padding:8px 14px;border-radius:9px;font-size:13px;cursor:pointer}
.btn.ghost{background:#1d2230;border:1px solid #2a3042}
.wrap{padding:22px;display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px}
.card{background:#161922;border:1px solid #232838;border-radius:14px;padding:16px;position:relative}
.card .v{font-size:26px;font-weight:700;margin-top:6px}
.card .l{color:#9aa3b2;font-size:13px}
.card .q{position:absolute;top:12px;right:14px;color:#5b657a;cursor:help;font-size:13px}
.section{padding:0 22px 22px}
.section h2{font-size:15px;color:#9aa3b2;font-weight:600}
table{width:100%;border-collapse:collapse;background:#161922;border-radius:12px;overflow:hidden}
th,td{text-align:left;padding:10px 14px;border-bottom:1px solid #232838;font-size:13px}
th{color:#9aa3b2}
.badge{padding:2px 8px;border-radius:8px;font-size:11px;background:#1d2230}
.empty{padding:22px;text-align:center;color:#8a93a6;font-size:13px}
.banner{margin:0 22px 18px;background:linear-gradient(90deg,#1e293b,#162033);border:1px solid #2a3a55;border-radius:14px;padding:18px 20px;display:flex;align-items:center;gap:16px}
.banner b{font-size:16px}
/* modal + wizard */
.overlay{position:fixed;inset:0;background:rgba(5,7,12,.72);display:none;align-items:center;justify-content:center;z-index:40}
.overlay.show{display:flex}
.modal{background:#12151d;border:1px solid #283042;border-radius:18px;width:min(560px,92vw);padding:26px}
.modal h2{margin:0 0 4px}
.modal p.sub{color:#9aa3b2;margin:0 0 18px;font-size:14px}
.steps{display:flex;gap:6px;margin-bottom:18px}
.steps i{flex:1;height:5px;border-radius:3px;background:#2a3042}
.steps i.on{background:#3b82f6}
label{display:block;font-size:13px;color:#cdd3df;margin:12px 0 6px}
input,textarea,select{width:100%;padding:11px 13px;border-radius:10px;border:1px solid #2a3042;background:#0f1117;color:#e7e9ee;font-size:14px}
textarea{min-height:120px;resize:vertical}
.row{display:flex;gap:10px}.row>*{flex:1}
.modal .actions{display:flex;gap:10px;margin-top:22px}
.modal .actions .sp{margin-right:auto}
.hint{font-size:12px;color:#7c879b;margin-top:6px}
/* tour */
.tour{position:fixed;inset:0;background:rgba(5,7,12,.55);display:none;z-index:50}
.tour.show{display:block}
.tip{position:fixed;left:50%;bottom:34px;transform:translateX(-50%);background:#12151d;border:1px solid #3b82f6;border-radius:14px;width:min(440px,92vw);padding:18px 20px;box-shadow:0 18px 50px rgba(0,0,0,.5)}
.tip h3{margin:0 0 6px;font-size:16px}
.tip p{margin:0;color:#bcc4d4;font-size:14px;line-height:1.5}
.tip .actions{display:flex;gap:10px;margin-top:16px;align-items:center}
.tip .prog{margin-right:auto;color:#7c879b;font-size:12px}
.spot{position:relative;z-index:51;outline:3px solid #3b82f6;outline-offset:4px;border-radius:12px;transition:outline .15s}
</style></head><body>
<header>
  <h1>Buddy Care</h1>
  <button class="btn ghost" id=tourBtn>Take a tour</button>
  <button class="btn ghost" id=setupBtn>Setup</button>
  <a class=btn id=openChat href="/widget" target=_blank>Open chat widget</a>
</header>
<div class=banner id=welcome style=display:none>
  <div style=font-size:30px>👋</div>
  <div><b>Welcome! Let's get your assistant ready.</b><div style="color:#9aa3b2;font-size:14px;margin-top:3px">It takes about 2 minutes. We'll name it, teach it about your business, and switch it on.</div></div>
  <button class=btn id=startSetup style=margin-left:auto>Start setup</button>
</div>
<div class=wrap id=kpis></div>
<div class=section id=secEsc><h2>People waiting for a human</h2><table id=esc></table></div>
<div class=section><h2>Tickets (issues to follow up)</h2><table id=tix></table></div>
<div class=section id=secSes><h2>Recent conversations</h2><table id=ses></table></div>

<!-- Setup wizard -->
<div class=overlay id=wiz>
 <div class=modal>
  <div class=steps><i id=s0></i><i id=s1></i><i id=s2></i></div>
  <div id=step0>
    <h2>1. Name your assistant</h2>
    <p class=sub>This is who your customers will talk to.</p>
    <label>Assistant name</label><input id=fBot placeholder="e.g. Aria">
    <label>Your company name</label><input id=fCompany placeholder="e.g. Sunrise Foods">
    <label>Main language</label><input id=fLang placeholder="e.g. English" value=English>
  </div>
  <div id=step1 style=display:none>
    <h2>2. Teach it about your business</h2>
    <p class=sub>Paste your FAQs, policies, hours, prices - anything a customer might ask. Plain text is perfect.</p>
    <label>Knowledge (FAQ / policies)</label>
    <textarea id=fKnow placeholder="Our store hours are 9am-6pm Mon-Sat.&#10;Refunds are processed within 5-7 business days.&#10;Shipping is free on orders over $50."></textarea>
    <div class=hint>Tip: more detail = better answers. You can add more later from Setup.</div>
  </div>
  <div id=step2 style=display:none>
    <h2>3. Give it a brain</h2>
    <p class=sub>Pick an AI provider and paste your key. The key stays on your computer.</p>
    <div class=row>
      <div><label>Provider</label>
        <select id=fProv><option value=anthropic>Anthropic (Claude)</option><option value=openai>OpenAI (GPT)</option><option value=google>Google (Gemini)</option><option value=groq>Groq</option></select></div>
      <div><label>API key</label><input id=fKey placeholder="paste key (sk-...)"></div>
    </div>
    <div class=hint>Don't have a key yet? Skip this - you can add it later, or run a free offline model.</div>
  </div>
  <div class=actions>
   <button class="btn ghost sp" id=wizSkip>Skip for now</button>
   <button class="btn ghost" id=wizBack style=display:none>Back</button>
   <button class=btn id=wizNext>Next</button>
  </div>
 </div>
</div>

<!-- Guided tour -->
<div class=tour id=tour>
 <div class=tip>
  <h3 id=tipTitle></h3><p id=tipText></p>
  <div class=actions><span class=prog id=tipProg></span>
   <button class="btn ghost" id=tourBack>Back</button>
   <button class=btn id=tourNext>Next</button></div>
 </div>
</div>

<script>
const $=id=>document.getElementById(id);
function kpi(l,v,help){return `<div class=card><span class=q title="${help}">?</span><div class=l>${l}</div><div class=v>${v}</div></div>`}

async function load(){
 let a={};try{a=await (await fetch('/api/care/analytics')).json();}catch(e){return}
 $('kpis').innerHTML=[
  kpi('Conversations',a.total_conversations,'How many chats your assistant has handled.'),
  kpi('Solved without a human',((a.deflection_rate||0)*100).toFixed(0)+'%','Share of chats finished without needing a person. Higher is better - it saves time and money.'),
  kpi('Waiting for a human',a.escalations,'Chats handed off to your team. Check these quickly.'),
  kpi('Open tickets',a.open_tickets,'Issues logged for follow-up.'),
  kpi('Happiness (CSAT)',a.avg_csat??'-','Average rating customers gave, from 1 to 5.'),
  kpi('Mood (good / upset)',(a.sentiment?.positive||0)+' / '+(a.sentiment?.negative||0),'How customers sounded: happy vs upset messages.'),
 ].join('');

 const esc=(await (await fetch('/api/care/escalations')).json()).escalations;
 $('esc').innerHTML = esc.length
  ? '<tr><th>ID</th><th>Chat</th><th>Why</th><th>When</th></tr>'+esc.map(e=>`<tr><td>${e.id}</td><td>${e.session_id}</td><td>${e.reason||''}</td><td>${(e.ts||'').slice(0,19)}</td></tr>`).join('')
  : '<tr><td class=empty>Nobody is waiting right now. When a customer needs a person, they show up here.</td></tr>';

 const tix=(await (await fetch('/api/care/tickets')).json()).tickets;
 $('tix').innerHTML = tix.length
  ? '<tr><th>ID</th><th>Subject</th><th>Priority</th><th>Status</th></tr>'+tix.map(t=>`<tr><td>${t.id}</td><td>${t.subject||''}</td><td><span class=badge>${t.priority}</span></td><td>${t.status}</td></tr>`).join('')
  : '<tr><td class=empty>No tickets yet.</td></tr>';

 const ses=(await (await fetch('/api/care/sessions')).json()).sessions;
 $('ses').innerHTML = ses.length
  ? '<tr><th>Chat</th><th>Channel</th><th>Msgs</th><th>Preview</th></tr>'+ses.map(s=>`<tr><td>${s.session_id}</td><td>${s.channel||'web'}</td><td>${s.messages}</td><td>${s.preview||''}</td></tr>`).join('')
  : '<tr><td class=empty>No conversations yet. Click "Open chat widget" and say hello to test it!</td></tr>';

 $('welcome').style.display = (a.total_conversations===0 && !localStorage.getItem('care_setup_done')) ? 'flex' : 'none';
}

/* ---------- Setup wizard ---------- */
let step=0;
function showStep(n){step=n;[0,1,2].forEach(i=>{$('step'+i).style.display=i===n?'block':'none';$('s'+i).className=i<=n?'on':'';});
 $('wizBack').style.display=n===0?'none':'inline-block';$('wizNext').textContent=n===2?'Finish':'Next';}
function openWiz(){step=0;showStep(0);$('wiz').classList.add('show');
 fetch('/api/care/settings').then(r=>r.json()).then(s=>{$('fBot').value=s.bot_name||'';$('fCompany').value=s.company_name||'';$('fLang').value=(s.languages&&s.languages[0])||'English';});}
function closeWiz(){$('wiz').classList.remove('show');}
$('setupBtn').onclick=openWiz;$('startSetup').onclick=openWiz;$('wizSkip').onclick=()=>{localStorage.setItem('care_setup_done','1');closeWiz();load();};
$('wizBack').onclick=()=>showStep(step-1);
$('wizNext').onclick=async()=>{
 if(step<2){showStep(step+1);return;}
 await fetch('/api/care/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
   bot_name:$('fBot').value||'Aria',company_name:$('fCompany').value||'Acme Support',
   languages:[$('fLang').value||'English'],
   api_keys:$('fKey').value?{[$('fProv').value]:$('fKey').value}:{}})});
 if($('fKnow').value.trim())await fetch('/api/care/knowledge',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:$('fKnow').value})});
 localStorage.setItem('care_setup_done','1');closeWiz();load();
 alert("All set! Click 'Open chat widget' to talk to your assistant.");
};

/* ---------- Guided tour ---------- */
const TOUR=[
 {el:'welcome',t:'This is your console',x:"Everything about your support assistant lives here. Let's look around - it's quick."},
 {el:'setupBtn',t:'Set up in 3 steps',x:'Click Setup any time to name your assistant, teach it about your business, and add an AI key.'},
 {el:'kpis',t:'Your numbers, in plain words',x:'These cards show how busy your assistant is and how well it\\'s doing. Hover the "?" on any card to learn more.'},
 {el:'secEsc',t:'When a person is needed',x:'If a customer is upset or asks for a human, the chat appears here so your team can jump in.'},
 {el:'openChat',t:'See what customers see',x:'This opens the chat window your customers use. Try sending a message to test your assistant!'},
];
let ti=0,spotEl=null;
function clearSpot(){if(spotEl){spotEl.classList.remove('spot');spotEl=null;}}
function showTip(i){ti=i;const s=TOUR[i];clearSpot();const el=$(s.el);if(el){el.classList.add('spot');spotEl=el;el.scrollIntoView({behavior:'smooth',block:'center'});}
 $('tipTitle').textContent=s.t;$('tipText').textContent=s.x;$('tipProg').textContent=(i+1)+' / '+TOUR.length;
 $('tourBack').style.display=i===0?'none':'inline-block';$('tourNext').textContent=i===TOUR.length-1?'Done':'Next';}
function startTour(){$('tour').classList.add('show');showTip(0);}
function endTour(){clearSpot();$('tour').classList.remove('show');localStorage.setItem('care_tour_done','1');}
$('tourBtn').onclick=startTour;
$('tourBack').onclick=()=>showTip(ti-1);
$('tourNext').onclick=()=>{ti===TOUR.length-1?endTour():showTip(ti+1);};

load();setInterval(load,5000);
// First visit: gently auto-start the tour once.
if(!localStorage.getItem('care_tour_done'))setTimeout(startTour,900);
</script></body></html>"""


__all__ = ["create_app", "serve"]
