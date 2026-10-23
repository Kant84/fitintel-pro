"""Веб-консоль платформенной поддержки (ТЗ §3.3/§3.4, §18 — веб-вариант).
Вход: одноразовый токен impersonation (5 мин), источник — только платформа (WG)."""
import os, threading, datetime as dt, logging
from fastapi import APIRouter, Request, HTTPException, Header
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import text

router = APIRouter(prefix="/admin/console", tags=["admin-console"])

LOG_FILE = "/app/data/console.log"
_tokens_ddl_done = False

def _is_platform_source(host: str) -> bool:
    return (host.startswith("10.0.0.") or host.startswith("127.") or host == "::1"
            or host.startswith("172."))

def _check(request: Request, token: str):
    if not _is_platform_source(request.client.host):
        raise HTTPException(403, "only platform source")
    if not token:
        raise HTTPException(401, "token required")
    from app.db.session import engine
    global _tokens_ddl_done
    with engine.begin() as c:
        if not _tokens_ddl_done:
            c.execute(text("""CREATE TABLE IF NOT EXISTS impersonation_tokens (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                token TEXT UNIQUE NOT NULL, created_at TIMESTAMPTZ DEFAULT now(),
                expires_at TIMESTAMPTZ NOT NULL, used BOOLEAN DEFAULT FALSE)"""))
            _tokens_ddl_done = True
        r = c.execute(text("""SELECT 1 FROM impersonation_tokens
            WHERE token=:t AND used=FALSE AND expires_at > now()"""), {"t": token}).fetchone()
    if not r:
        raise HTTPException(401, "invalid or expired token")

def _log_setup():
    if not os.path.exists(LOG_FILE):
        h = logging.FileHandler(LOG_FILE)
        h.setLevel(logging.INFO)
        logging.getLogger().addHandler(h)
_log_setup()


def _ser(v):
    return v.isoformat() if hasattr(v, "isoformat") else v

PAGE = """<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8">
<title>FitIntel — консоль поддержки</title>
<style>
body{font:14px/1.5 system-ui,sans-serif;background:#0f172a;color:#e2e8f0;margin:0}
header{background:#7f1d1d;color:#fecaca;padding:10px 18px;font-weight:700}
nav button{background:#1e293b;border:1px solid #334155;color:#94a3b8;padding:6px 14px;border-radius:6px;cursor:pointer;margin-right:6px}
nav button.on{color:#38bdf8;border-color:#38bdf8}
main{padding:18px}.view{display:none}.view.on{display:block}
table{width:100%;border-collapse:collapse;background:#1e293b}
th,td{padding:7px 10px;border-bottom:1px solid #334155;font-size:13px;text-align:left}
th{color:#94a3b8}tr.d{cursor:pointer}button.act{background:#0f172a;border:1px solid #475569;color:#cbd5e1;padding:3px 10px;border-radius:6px;cursor:pointer;font-size:12px}
pre{background:#1e293b;padding:12px;border-radius:8px;font-size:12px;max-height:420px;overflow:auto}
input,select{background:#0f172a;border:1px solid #334155;color:#e2e8f0;padding:5px 8px;border-radius:6px}
.badge{padding:1px 8px;border-radius:8px;font-size:11px}.on{background:#064e3b;color:#34d399}.off{background:#7f1d1d;color:#fca5a5}
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}.kpi{background:#1e293b;border-radius:8px;padding:12px}.kpi b{font-size:18px;color:#38bdf8}
</style></head><body>
<header>КОНСОЛЬ ПОДДЕРЖКИ — сессия платформенного администратора · действия в аудите · токен 5 мин</header>
<nav style="padding:10px 18px">
<button data-v="u" class="on">Пользователи</button><button data-v="h">Health</button><button data-v="l">Логи</button><button data-v="c">Клиенты</button>
<button style="float:right" onclick="if(confirm('Перезапустить API клуба? Сессия прервётся.'))api('POST','restart',{})">Перезапуск API</button>
</nav><main>
<div class="view on" id="v-u">
<div style="margin-bottom:10px">
<input id="nu" placeholder="логин" size="12"><input id="ne" placeholder="email" size="18">
<input id="np" placeholder="пароль (пусто=авто)" size="16"><select id="nr"></select>
<button class="act" onclick="createUser()">Создать</button></div>
<table id="users"><tr><th>Логин</th><th>Email</th><th>ФИО</th><th>Роли</th><th>Активен</th><th></th></tr></table>
</div>
<div class="view" id="v-c">
<div style="margin-bottom:10px"><input id="cq" placeholder="Поиск: фамилия / телефон / email…" size="34">
<button class="act" onclick="loadClients()">Найти</button></div>
<table id="clients"><tr><th>ФИО</th><th>Телефон</th><th>Email</th><th>Статус</th><th>Создан</th></tr></table><div id="cdetail" style="margin-top:14px"></div>
</div>
<div class="view" id="v-h"><div class="kpis" id="hp"></div></div>
<div class="view" id="v-l"><div style="margin-bottom:8px"><input id="ll" value="200" size="5"> строк <button class="act" onclick="loadLogs()">Обновить</button></div><pre id="log">—</pre></div>
</main>
<script>
const T=new URLSearchParams(location.search).get('token');
async function api(m,p,b){const r=await fetch('api/'+p,{method:m,headers:{'Content-Type':'application/json','X-Token':T},body:b?JSON.stringify(b):undefined});
 if(!r.ok)throw new Error(p+' '+r.status+' '+(await r.text()).slice(0,120));return r.json()}
function esc(s){return String(s??'').replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]))}
async function loadUsers(){const d=await api('GET','users');
 document.getElementById('users').querySelectorAll('tr.d').forEach(e=>e.remove());
 for(const u of d.users){const tr=document.createElement('tr');tr.className='d';
  tr.innerHTML=`<td>${esc(u.username)}</td><td>${esc(u.email)}</td><td>${esc(u.full_name)}</td><td>${esc(u.roles)}</td>
   <td><span class="badge ${u.is_active?'on':'off'}">${u.is_active?'да':'нет'}</span></td>
   <td><button class="act" onclick="resetPw('${u.id}')">Сброс пароля</button>
       <button class="act" onclick="toggle('${u.id}',${u.is_active})">${u.is_active?'Блок':'Разблок'}</button></td>`;
  document.getElementById('users').appendChild(tr)}
 const rr=await api('GET','roles');document.getElementById('nr').innerHTML=rr.roles.map(r=>`<option>${esc(r)}</option>`).join('')}
async function createUser(){const b={username:nu.value,email:ne.value,password:np.value,role:nr.value};
 try{await api('POST','users',b);loadUsers()}catch(e){alert(e.message)}}
async function resetPw(id){const p=prompt('Новый пароль (пусто=авто):')||'';try{const r=await api('POST','users/'+id+'/reset-password',{password:p});alert('Новый пароль: '+r.password)}catch(e){alert(e.message)}}
async function toggle(id,act){await api('POST','users/'+id+'/toggle-active',{active:!act});loadUsers()}
async function loadHealth(){const d=await api('GET','health');
 hp.innerHTML=[['БД',d.db],['Диск занято %',d.disk_pct],['Аптайм, ч',d.uptime_h],['Версия',d.version]]
 .map(x=>`<div class="kpi"><b>${esc(x[1])}</b><br><span style="color:#94a3b8;font-size:12px">${x[0]}</span></div>`).join('')}
async function loadLogs(){try{const d=await api('GET','logs?lines='+ll.value);log.textContent=d.lines.join('\n')}catch(e){log.textContent=e.message}}
async function loadClients(){const d=await api('GET','clients?q='+encodeURIComponent(cq.value));
 const tb=document.getElementById('clients');tb.querySelectorAll('tr.d').forEach(e=>e.remove());
 for(const c of d.clients){const tr=document.createElement('tr');tr.className='d';tr.onclick=()=>loadClientCard(c.id);
  const fio=[c.last_name,c.first_name,c.middle_name].filter(Boolean).join(' ');
  tr.innerHTML=`<td>${esc(fio)}</td><td>${esc(c.phone)}</td><td>${esc(c.email)}</td>
   <td>${esc(c.status||'')}</td><td>${esc((c.created_at||'').replace('T',' ').slice(0,16))}</td>`;
  tb.appendChild(tr)}}
async function loadClientCard(id){
 cdetail.innerHTML='<h2>Загрузка…</h2>';
 try{
  const d=await api('GET','clients/'+id+'/card');
  if(!d.client){cdetail.innerHTML='<p>Клиент не найден</p>';return}
  const c=d.client;
  const fio=[c.last_name,c.first_name,c.middle_name].filter(Boolean).join(' ');
  let h=`<h2>${esc(fio)} <span style="color:#94a3b8;font-size:13px">${esc(c.phone||'')} · ${esc(c.email||'')}</span></h2><div class="kv">`;
  const skip=new Set(['id','last_name','first_name','middle_name','photo_url','user_id','parent_id']);
  for(const k in c){if(skip.has(k)||c[k]===null||c[k]==='')continue;
   h+=`<b>${esc(k)}</b><span>${esc(String(c[k]))}</span>`}
  h+='</div>';
  h+=`<h2>Абонементы (${d.subscriptions.length})</h2><table><tr><th>Статус</th><th>С</th><th>По</th><th>Цена</th><th>Визиты</th></tr>`;
  for(const s of d.subscriptions){h+=`<tr><td>${esc(s.status||'')}</td><td>${esc(String(s.start_date||''))}</td><td>${esc(String(s.end_date||''))}</td><td>${esc(String(s.price))} ${esc(s.currency||'')}</td><td>${s.visits_used==null?'':s.visits_used}/${s.visit_limit==null?'∞':s.visit_limit}</td></tr>`}
  h+='</table>';
  h+=`<h2>Платежи (последние ${d.payments.length})</h2><table><tr><th>Сумма</th><th>Метод</th><th>Направление</th><th>Статус</th><th>Дата</th></tr>`;
  for(const p of d.payments){h+=`<tr><td>${esc(String(p.amount))} ${esc(p.currency||'')}</td><td>${esc(p.payment_method||'')}</td><td>${esc(p.payment_direction||'')}</td><td>${esc(p.status||'')}</td><td>${esc(String(p.paid_at||p.created_at||'').replace('T',' ').slice(0,16))}</td></tr>`}
  h+='</table>';
  h+=`<h2>Визиты: всего ${d.visits_total}</h2><table><tr><th>Вход</th><th>Зона</th><th>Способ</th><th>Статус</th></tr>`;
  for(const v of d.visits_last){h+=`<tr><td>${esc(String(v.entry_time||'').replace('T',' ').slice(0,16))}</td><td>${esc(v.zone||'')}</td><td>${esc(v.access_method||'')}</td><td>${esc(v.status||'')}</td></tr>`}
  h+='</table>';
  cdetail.innerHTML=h;
 }catch(e){cdetail.innerHTML='<p>Ошибка: '+esc(e.message)+'</p>'}
}
document.querySelectorAll('nav button[data-v]').forEach(b=>b.onclick=()=>{document.querySelectorAll('nav button').forEach(x=>x.classList.remove('on'));document.querySelectorAll('.view').forEach(x=>x.classList.remove('on'));b.classList.add('on');document.getElementById('v-'+b.dataset.v).classList.add('on')});
loadUsers();loadHealth();loadClients();
</script></body></html>"""

@router.get("", response_class=HTMLResponse)
def page(request: Request, token: str = ""):
    if not token:
        return HTMLResponse("<h3 style='font-family:sans-serif'>403: токен не передан</h3>", status_code=403)
    _check(request, token)
    return PAGE

@router.get("/api/users")
def users(request: Request, x_token: str = Header(default="", alias="X-Token")):
    _check(request, x_token)
    from app.db.session import engine
    with engine.begin() as c:
        rows = c.execute(text("""
            SELECT u.id::text, u.username, u.email, u.full_name, u.is_active,
              (SELECT string_agg(r.code, ', ' ORDER BY r.code) FROM user_roles ur
                JOIN roles r ON r.id=ur.role_id WHERE ur.user_id=u.id) AS roles
            FROM users u WHERE u.deleted_at IS NULL ORDER BY u.created_at""")).mappings().all()
    return JSONResponse({"users": [dict(r) for r in rows]})

@router.get("/api/clients")
def clients_list(request: Request, q: str = "", limit: int = 200,
                 x_token: str = Header(default="", alias="X-Token")):
    _check(request, x_token)
    from app.db.session import engine
    limit = max(1, min(limit, 500))
    with engine.begin() as c:
        cols = {r[0] for r in c.execute(text(
            "SELECT column_name FROM information_schema.columns WHERE table_name='clients'"
        )).fetchall()}
        has_deleted = "deleted_at" in cols
        where = "deleted_at IS NULL" if has_deleted else "TRUE"
        params = {"q": q.strip(), "lim": limit}
        search = ""
        if q.strip():
            parts = []
            for col in ("last_name", "first_name", "phone", "email"):
                if col in cols:
                    parts.append("%s ILIKE '%%' || :q || '%%'" % col)
            if parts:
                search = " AND (" + " OR ".join(parts) + ")"
        sel = [('id::text AS id' if k == 'id' else k)
               for k in ('id', 'last_name', 'first_name', 'middle_name',
                         'phone', 'email', 'status', 'created_at') if k in cols]
        order = "created_at" if "created_at" in cols else "id"
        sql = "SELECT %s FROM clients WHERE %s%s ORDER BY %s DESC LIMIT :lim" % (
            ", ".join(sel), where, search, order)
        rows = c.execute(text(sql), params).mappings().all()
    return JSONResponse({"clients": [{k: _ser(v) for k, v in dict(r).items()} for r in rows]})


@router.get("/api/clients/{cid}/card")
def client_card(request: Request, cid: str, x_token: str = Header(default="", alias="X-Token")):
    _check(request, x_token)
    from app.db.session import engine
    with engine.begin() as c:
        row = c.execute(text(
            "SELECT * FROM clients WHERE id::text=:i"), {"i": cid}).mappings().first()
        client = {k: _ser(v) for k, v in dict(row).items()} if row else None
        subs = c.execute(text("""
            SELECT id::text, status, start_date, end_date, price, currency,
                   visit_limit, visits_used, is_unlimited, frozen_until, auto_renew
            FROM subscriptions WHERE client_id::text=:i
            ORDER BY created_at DESC LIMIT 10"""), {"i": cid}).mappings().all()
        pays = c.execute(text("""
            SELECT id::text, amount, currency, payment_method, payment_direction,
                   status, paid_at, created_at
            FROM payments WHERE client_id::text=:i
            ORDER BY created_at DESC LIMIT 10"""), {"i": cid}).mappings().all()
        vtot = c.execute(text(
            "SELECT count(*) FROM visits WHERE client_id::text=:i"), {"i": cid}).fetchone()
        vlast = c.execute(text("""
            SELECT entry_time, zone, access_method, status
            FROM visits WHERE client_id::text=:i
            ORDER BY entry_time DESC LIMIT 5"""), {"i": cid}).mappings().all()
    cl = lambda rows: [{k: _ser(v) for k, v in dict(r).items()} for r in rows]
    return JSONResponse({"client": client,
                         "subscriptions": cl(subs), "payments": cl(pays),
                         "visits_total": vtot[0] if vtot else 0,
                         "visits_last": cl(vlast)})


@router.get("/api/roles")
def roles(request: Request, x_token: str = Header(default="", alias="X-Token")):
    _check(request, x_token)
    from app.db.session import engine
    with engine.begin() as c:
        rows = c.execute(text("SELECT code FROM roles ORDER BY code")).fetchall()
    return JSONResponse({"roles": [r[0] for r in rows]})

@router.post("/api/users")
def user_create(request: Request, body: dict, x_token: str = Header(default="", alias="X-Token")):
    _check(request, x_token)
    import secrets as _s
    from app.core.security import get_password_hash
    from app.db.session import engine
    username = str(body.get("username") or "").strip()
    if not username:
        raise HTTPException(400, "username required")
    password = str(body.get("password") or "") or _s.token_urlsafe(9)[:12]
    uid = str(__import__("uuid").uuid4())
    now = dt.datetime.now(dt.timezone.utc)
    with engine.begin() as c:
        dup = c.execute(text("SELECT 1 FROM users WHERE username=:u"), {"u": username}).fetchone()
        if dup:
            raise HTTPException(409, "username exists")
        c.execute(text("""INSERT INTO users (id, username, email, password_hash, is_active,
            is_superuser, is_verified, is_fired, failed_login_count, created_at, updated_at)
            VALUES (:i,:u,:e,:p,TRUE,FALSE,TRUE,FALSE,0,:n,:n)"""),
            {"i": uid, "u": username, "e": body.get("email") or None,
             "p": get_password_hash(password), "n": now})
        rc = body.get("role")
        if rc:
            c.execute(text("""INSERT INTO user_roles (id, user_id, role_id, assigned_at, created_at, updated_at)
                SELECT gen_random_uuid(), :u, r.id, now(), now(), now() FROM roles r
                WHERE r.code=:rc ON CONFLICT (user_id, role_id) DO NOTHING"""), {"u": uid, "rc": rc})
    return JSONResponse({"ok": True, "id": uid, "username": username, "password": password})

@router.post("/api/users/{uid}/reset-password")
def user_reset(request: Request, uid: str, body: dict, x_token: str = Header(default="", alias="X-Token")):
    _check(request, x_token)
    import secrets as _s
    from app.core.security import get_password_hash
    from app.db.session import engine
    password = str(body.get("password") or "") or _s.token_urlsafe(9)[:12]
    with engine.begin() as c:
        n = c.execute(text("UPDATE users SET password_hash=:p, failed_login_count=0, locked_until=NULL WHERE id::text=:i"),
                      {"p": get_password_hash(password), "i": uid}).rowcount
    if not n:
        raise HTTPException(404, "user not found")
    return JSONResponse({"ok": True, "password": password})

@router.post("/api/users/{uid}/toggle-active")
def user_toggle(request: Request, uid: str, body: dict, x_token: str = Header(default="", alias="X-Token")):
    _check(request, x_token)
    from app.db.session import engine
    active = bool(body.get("active"))
    with engine.begin() as c:
        n = c.execute(text("UPDATE users SET is_active=:a WHERE id::text=:i"), {"a": active, "i": uid}).rowcount
    if not n:
        raise HTTPException(404, "user not found")
    return JSONResponse({"ok": True, "active": active})

@router.get("/api/health")
def health(request: Request, x_token: str = Header(default="", alias="X-Token")):
    _check(request, x_token)
    import shutil
    from app.db.session import engine
    t0 = dt.datetime.now()
    with engine.begin() as c:
        c.execute(text("SELECT 1"))
    db_ms = int((dt.datetime.now() - t0).total_seconds() * 1000)
    du = shutil.disk_usage("/")
    uptime_h = round(float(open("/proc/uptime").read().split()[0]) / 3600, 1)
    return JSONResponse({"db": "ok %d ms" % db_ms, "disk_pct": int(du.used * 100 / du.total),
                         "uptime_h": uptime_h, "version": os.environ.get("APP_VERSION", "1.6.1")})

@router.get("/api/logs")
def logs(request: Request, lines: int = 200, x_token: str = Header(default="", alias="X-Token")):
    _check(request, x_token)
    if not os.path.exists(LOG_FILE):
        return JSONResponse({"lines": ["(лог-файл появится после перезапуска api; история — docker logs deploy-api-1)"]})
    data = open(LOG_FILE, encoding="utf-8", errors="replace").read().splitlines()
    return JSONResponse({"lines": data[-min(lines, 2000):]})

@router.post("/api/restart")
def restart(request: Request, x_token: str = Header(default="", alias="X-Token")):
    _check(request, x_token)
    threading.Timer(1.0, os._exit, args=(0,)).start()
    return JSONResponse({"ok": True, "note": "api exit -> контейнер перезапустится (restart policy)"})
