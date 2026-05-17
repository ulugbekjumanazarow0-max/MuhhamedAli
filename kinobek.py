import telebot
from telebot import types
import sqlite3
from datetime import datetime

# ══════════════════════════════════════════════
#  SAZLAMALAR
# ══════════════════════════════════════════════
BOT_TOKEN  = "8409842921:AAE6-zDCR59qzVyVHo3x7VBIaiorQCOCjtE"
ADMIN_IDS  = [7230464690]          # Admin Telegram ID
DB_FILE    = "kino.db"
# ══════════════════════════════════════════════

bot    = telebot.TeleBot(BOT_TOKEN)
states = {}

# ──────────────────────────────────────────────
# DATABASE
# ──────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS movies (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        code        TEXT UNIQUE,
        title       TEXT,
        year        TEXT,
        genre       TEXT,
        description TEXT,
        file_id     TEXT,
        file_type   TEXT,
        views       INTEGER DEFAULT 0,
        added_at    TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id   INTEGER PRIMARY KEY,
        username  TEXT,
        full_name TEXT,
        joined_at TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS channels (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        channel_id  TEXT UNIQUE,
        title       TEXT,
        invite_link TEXT
    )""")
    conn.commit(); conn.close()

def db():
    return sqlite3.connect(DB_FILE)

# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────
def fix_url(link):
    link = link.strip()
    if link.startswith("@"): return "https://t.me/" + link[1:]
    if not link.startswith("http"): return "https://t.me/" + link
    return link

def is_admin(uid): return uid in ADMIN_IDS

def get_channels():
    conn = db(); c = conn.cursor()
    c.execute("SELECT channel_id, title, invite_link FROM channels")
    r = c.fetchall(); conn.close(); return r

def register_user(user):
    conn = db(); c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE user_id=?", (user.id,))
    if not c.fetchone():
        c.execute("INSERT INTO users VALUES (?,?,?,?)",
                  (user.id, user.username or "",
                   user.full_name or "",
                   datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
    conn.close()

def gen_code():
    conn = db(); c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM movies")
    n = c.fetchone()[0]; conn.close()
    return f"K{str(n+1).zfill(4)}"

# ──────────────────────────────────────────────
# MEJBURY ABUNA — REAL CHECK (bot kanalda admin)
# ──────────────────────────────────────────────
def check_membership(uid):
    """
    Ulanyjy ähli kanallara agza boldumy?
    Bot şol kanallarda ADMIN bolmaly!
    True  = ähli kanallara agza
    False = agza däl (haýsy kanallar eksik)
    """
    channels = get_channels()
    if not channels:
        return True, []

    not_joined = []
    for ch_id, title, link in channels:
        try:
            member = bot.get_chat_member(ch_id, uid)
            if member.status in ("left", "kicked", "banned"):
                not_joined.append((title, link))
        except Exception:
            # Bot kanalda admin däl ýa-da kanal ýalňyş
            not_joined.append((title, link))

    return len(not_joined) == 0, not_joined

def sub_keyboard(not_joined):
    """Diňe agza bolunmadyk kanallar görkezilýär"""
    kb = types.InlineKeyboardMarkup()
    for title, link in not_joined:
        kb.add(types.InlineKeyboardButton(f"📢 {title}", url=fix_url(link)))
    kb.add(types.InlineKeyboardButton("✅ Agza boldum, barla!", callback_data="check_sub"))
    return kb

def require_sub(uid, chat_id):
    """
    Agza däl bolsa habar iber → True (blokla)
    Agza bolsa → False (geç)
    """
    ok, missing = check_membership(uid)
    if ok: return False
    bot.send_message(chat_id,
        "📢 <b>Boty ulanmak üçin\nkanallara agza boluň!</b>\n\n"
        "⬇️ Agza boluň, soňra ✅ düwmesine basyň:",
        parse_mode="HTML",
        reply_markup=sub_keyboard(missing))
    return True

# ──────────────────────────────────────────────
# KLAVIATURALAR
# ──────────────────────────────────────────────
def main_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🔍 Kino gözle", "🎬 Ähli kinolar")
    kb.row("📋 Barada")
    return kb

def admin_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🔍 Kino gözle", "🎬 Ähli kinolar")
    kb.row("➕ Kino goş", "🛠 Admin panel")
    kb.row("📋 Barada")
    return kb

# ──────────────────────────────────────────────
# KINO IBERMEK
# ──────────────────────────────────────────────
def send_movie(chat_id, code):
    conn = db(); c = conn.cursor()
    c.execute("SELECT * FROM movies WHERE code=?", (code.upper(),))
    m = c.fetchone()
    if m:
        c.execute("UPDATE movies SET views=views+1 WHERE code=?", (code.upper(),))
        conn.commit()
    conn.close()

    if not m:
        bot.send_message(chat_id,
            f"❌ <b>{code}</b> kodly kino tapylmady.\n\n"
            f"💡 Dogry kody ýazyň (mysal: <code>K0001</code>)",
            parse_mode="HTML")
        return

    bot_info = bot.get_me()
    deep_link = f"https://t.me/{bot_info.username}?start={m[1]}"

    caption = (
        f"🎬 <b>{m[2]}</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📅 Ýyl: <b>{m[3]}</b>\n"
        f"🎭 Žanr: <b>{m[4]}</b>\n"
        f"📝 {m[5]}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🔢 Kod: <code>{m[1]}</code>\n"
        f"👁 Görüldi: <b>{m[8]}</b> gezek\n\n"
        f"🔗 {deep_link}"
    )
    try:
        if m[7] == "video":
            bot.send_video(chat_id, m[6], caption=caption, parse_mode="HTML")
        elif m[7] in ("document", "animation"):
            bot.send_document(chat_id, m[6], caption=caption, parse_mode="HTML")
        else:
            bot.send_message(chat_id, caption, parse_mode="HTML")
    except Exception as e:
        bot.send_message(chat_id, f"❌ Kino iberilmedi: {e}")

# ──────────────────────────────────────────────
# /start
# ──────────────────────────────────────────────
@bot.message_handler(commands=["start"])
def cmd_start(msg):
    register_user(msg.from_user)
    uid  = msg.from_user.id
    args = msg.text.split()

    # Deep link bilen geldi (kod bilen)
    if len(args) > 1 and args[1].upper().startswith("K"):
        if require_sub(uid, msg.chat.id): return
        send_movie(msg.chat.id, args[1].upper())
        return

    # Abuna barlag
    if require_sub(uid, msg.chat.id): return

    kb = admin_kb() if is_admin(uid) else main_kb()
    bot.send_message(msg.chat.id,
        "🎬 <b>Kino Botyna hoş geldiňiz!</b>\n\n"
        "🔍 Kino <b>adyny</b> ýa-da <b>kodyny</b> ýazyň\n"
        "📥 Mugt kinolary tapyň!\n\n"
        "💡 Mysal: <code>Titanic</code> ýa-da <code>K0001</code>",
        parse_mode="HTML", reply_markup=kb)

# ──────────────────────────────────────────────
# ✅ ABUNA BARLAG CALLBACK
# ──────────────────────────────────────────────
@bot.callback_query_handler(func=lambda c: c.data == "check_sub")
def cb_check_sub(call):
    uid = call.from_user.id
    ok, missing = check_membership(uid)

    if ok:
        bot.answer_callback_query(call.id, "✅ Tassyklandy! Hoş geldiňiz!")
        bot.delete_message(call.message.chat.id, call.message.message_id)
        kb = admin_kb() if is_admin(uid) else main_kb()
        bot.send_message(call.message.chat.id,
            "✅ <b>Sag boluň!</b>\n\n"
            "🔍 Kino adyny ýa-da kodyny ýazyň:",
            parse_mode="HTML", reply_markup=kb)
    else:
        # Henizem agza bolmadyk kanallar bar
        bot.answer_callback_query(call.id,
            f"❌ Heniz {len(missing)} kanala agza bolmadyňyz!",
            show_alert=True)
        # Düwmeleri täzele — diňe agza bolunmadyklar
        try:
            bot.edit_message_reply_markup(
                call.message.chat.id,
                call.message.message_id,
                reply_markup=sub_keyboard(missing))
        except Exception:
            pass

# ──────────────────────────────────────────────
# ULANYJY MENÝUSY
# ──────────────────────────────────────────────
@bot.message_handler(func=lambda m: m.text == "🔍 Kino gözle")
def btn_search(msg):
    if require_sub(msg.from_user.id, msg.chat.id): return
    states[msg.from_user.id] = {"state": "searching"}
    bot.send_message(msg.chat.id,
        "🔍 <b>Kino gözleg</b>\n\n"
        "Kino <b>adyny</b> ýa-da <b>kodyny</b> ýazyň:\n"
        "<i>Mysal: Titanic ýa-da K0001</i>",
        parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "🎬 Ähli kinolar")
def btn_all(msg):
    if require_sub(msg.from_user.id, msg.chat.id): return
    conn = db(); c = conn.cursor()
    c.execute("SELECT code,title,year,genre,views FROM movies ORDER BY id DESC LIMIT 50")
    rows = c.fetchall(); conn.close()
    if not rows:
        bot.send_message(msg.chat.id, "🎬 Heniz kino goşulmady."); return
    text = "🎬 <b>Kinolar sanawy:</b>\n\n"
    for code, title, year, genre, views in rows:
        text += f"<code>{code}</code> | <b>{title}</b> ({year}) — {genre}\n"
    text += "\n📌 Kino almak üçin kodyny ýazyň"
    bot.send_message(msg.chat.id, text, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "📋 Barada")
def btn_about(msg):
    conn = db(); c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM movies");    tm = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users");     tu = c.fetchone()[0]
    c.execute("SELECT SUM(views) FROM movies");  tv = c.fetchone()[0] or 0
    conn.close()
    bot.send_message(msg.chat.id,
        f"ℹ️ <b>Kino Bot</b>\n\n"
        f"🎬 Kinolar: <b>{tm}</b>\n"
        f"👥 Ulanyjylar: <b>{tu}</b>\n"
        f"👁 Jemi görüldi: <b>{tv}</b>\n\n"
        f"🔍 Kino adyny ýa-da kodyny ýazyň",
        parse_mode="HTML")

# ──────────────────────────────────────────────
# ADMIN: KINO GOŞMAK
# ──────────────────────────────────────────────
@bot.message_handler(func=lambda m: m.text == "➕ Kino goş" and m.from_user.id in ADMIN_IDS)
def btn_add_movie(msg):
    states[msg.from_user.id] = {"state": "upload_file"}
    bot.send_message(msg.chat.id,
        "🎬 <b>Kino goşmak — 1/5</b>\n\n"
        "📎 Wideo faýlyny ýükle ýa-da kanaldan <b>forward</b> et\n\n"
        "⚠️ <b>Faýl</b> görnüşinde ýükle (dokument hökmünde)",
        parse_mode="HTML")

# ──────────────────────────────────────────────
# ADMIN PANEL
# ──────────────────────────────────────────────
@bot.message_handler(func=lambda m: m.text == "🛠 Admin panel" and m.from_user.id in ADMIN_IDS)
def btn_admin(msg):
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("📢 Kanal goş",    callback_data="a_add_ch"),
        types.InlineKeyboardButton("🗑 Kanal sil",     callback_data="a_del_ch"),
        types.InlineKeyboardButton("📣 Reklama iber", callback_data="a_bcast"),
        types.InlineKeyboardButton("📊 Statistika",   callback_data="a_stats"),
        types.InlineKeyboardButton("🎬 Kinolar",      callback_data="a_movies"),
        types.InlineKeyboardButton("🗑 Kino poz",     callback_data="a_del_mv"),
        types.InlineKeyboardButton("📋 Kanallar",     callback_data="a_list_ch"),
    )
    bot.send_message(msg.chat.id, "🛠 <b>Admin paneli</b>",
                     parse_mode="HTML", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "a_stats")
def a_stats(call):
    if not is_admin(call.from_user.id): return
    conn = db(); c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM movies");   tm = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users");    tu = c.fetchone()[0]
    c.execute("SELECT SUM(views) FROM movies"); tv = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM channels"); tc = c.fetchone()[0]
    conn.close()
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id,
        f"📊 <b>Statistika</b>\n\n"
        f"🎬 Kinolar: <b>{tm}</b>\n"
        f"👥 Ulanyjylar: <b>{tu}</b>\n"
        f"👁 Jemi görüldi: <b>{tv}</b>\n"
        f"📢 Kanallar: <b>{tc}</b>",
        parse_mode="HTML")

@bot.callback_query_handler(func=lambda c: c.data == "a_movies")
def a_movies(call):
    if not is_admin(call.from_user.id): return
    conn = db(); c = conn.cursor()
    c.execute("SELECT code,title,year,views FROM movies ORDER BY id DESC LIMIT 30")
    rows = c.fetchall(); conn.close()
    bot.answer_callback_query(call.id)
    if not rows:
        bot.send_message(call.message.chat.id, "🎬 Kino ýok."); return
    text = "🎬 <b>Kinolar:</b>\n\n"
    for code, title, year, views in rows:
        text += f"<code>{code}</code> | {title} ({year}) 👁{views}\n"
    bot.send_message(call.message.chat.id, text, parse_mode="HTML")

@bot.callback_query_handler(func=lambda c: c.data == "a_del_mv")
def a_del_mv(call):
    if not is_admin(call.from_user.id): return
    states[call.from_user.id] = {"state": "del_movie"}
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id,
        "🗑 Pozmak isleýän kino <b>kodyny</b> ýaz:\n<i>Mysal: K0001</i>",
        parse_mode="HTML")

@bot.callback_query_handler(func=lambda c: c.data == "a_list_ch")
def a_list_ch(call):
    if not is_admin(call.from_user.id): return
    channels = get_channels(); bot.answer_callback_query(call.id)
    if not channels:
        bot.send_message(call.message.chat.id,
            "📋 Kanal ýok.\n\n"
            "⚠️ Kanal goşanyňyzdan soň\n"
            "boty şol kanalda <b>admin</b> ediň!",
            parse_mode="HTML"); return
    text = "📋 <b>Mejbury kanallar:</b>\n\n"
    for ch_id, title, link in channels:
        text += f"• <b>{title}</b>\n  ID: <code>{ch_id}</code>\n\n"
    text += "⚠️ Bot her kanalda <b>admin</b> bolmaly!"
    bot.send_message(call.message.chat.id, text, parse_mode="HTML")

@bot.callback_query_handler(func=lambda c: c.data == "a_add_ch")
def a_add_ch(call):
    if not is_admin(call.from_user.id): return
    states[call.from_user.id] = {"state": "ch_id"}
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id,
        "📢 <b>Kanal goşmak</b>\n\n"
        "1️⃣ Kanalyň ID-sini ýa-da @username ýaz:\n"
        "<i>Mysal: -1001234567890 ýa-da @mykanalymy</i>\n\n"
        "⚠️ Boty kanalda <b>admin</b> edip goý!",
        parse_mode="HTML")

@bot.callback_query_handler(func=lambda c: c.data == "a_del_ch")
def a_del_ch(call):
    if not is_admin(call.from_user.id): return
    channels = get_channels()
    if not channels:
        bot.answer_callback_query(call.id, "Kanal ýok!", show_alert=True); return
    kb = types.InlineKeyboardMarkup()
    for ch_id, title, _ in channels:
        kb.add(types.InlineKeyboardButton(f"🗑 {title}", callback_data=f"dch_{ch_id}"))
    kb.add(types.InlineKeyboardButton("❌ Ýatyr", callback_data="a_cancel"))
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "Pozmak isleýän kanalyňyzy saýlaň:", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("dch_"))
def do_del_ch(call):
    if not is_admin(call.from_user.id): return
    ch_id = call.data[4:]
    conn = db(); c = conn.cursor()
    c.execute("DELETE FROM channels WHERE channel_id=?", (ch_id,))
    conn.commit(); conn.close()
    bot.answer_callback_query(call.id, "✅ Pozuldy!")
    bot.edit_message_text("✅ Kanal pozuldy.", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda c: c.data == "a_cancel")
def a_cancel(call):
    states.pop(call.from_user.id, None)
    bot.answer_callback_query(call.id)
    bot.edit_message_text("❌ Ýatyryldy.", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda c: c.data == "a_bcast")
def a_bcast(call):
    if not is_admin(call.from_user.id): return
    states[call.from_user.id] = {"state": "bcast"}
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id,
        "📣 <b>Reklama ibermek</b>\n\nHabarňyzy ýazyň:",
        parse_mode="HTML")

@bot.callback_query_handler(func=lambda c: c.data.startswith("getmv_"))
def cb_get_movie(call):
    if require_sub(call.from_user.id, call.message.chat.id): return
    bot.answer_callback_query(call.id)
    send_movie(call.message.chat.id, call.data[6:])

# ──────────────────────────────────────────────
# UNIVERSAL HANDLER
# ──────────────────────────────────────────────
MENU_TEXTS = {"🔍 Kino gözle","🎬 Ähli kinolar","📋 Barada","➕ Kino goş","🛠 Admin panel"}

@bot.message_handler(
    content_types=["text","video","document","animation","photo","sticker"],
    func=lambda m: True)
def universal(msg):
    uid = msg.from_user.id
    sd  = states.get(uid, {})
    st  = sd.get("state")

    # ════ KINO GOŞMAK — faýl ════
    if st == "upload_file" and is_admin(uid):
        fid, ftype = None, None
        if msg.video:
            fid, ftype = msg.video.file_id, "video"
        elif msg.document:
            fid, ftype = msg.document.file_id, "document"
        elif msg.animation:
            fid, ftype = msg.animation.file_id, "animation"
        if not fid:
            bot.send_message(msg.chat.id, "❌ Wideo ýa-da faýl iberiň!"); return
        states[uid] = {"state": "mv_title", "fid": fid, "ftype": ftype}
        bot.send_message(msg.chat.id,
            "✅ Faýl alyndy!\n\n"
            "🎬 <b>2/5</b> — Kino <b>adyny</b> ýazyň:\n<i>Mysal: Titanic</i>",
            parse_mode="HTML"); return

    if st == "mv_title" and is_admin(uid):
        states[uid]["title"] = msg.text; states[uid]["state"] = "mv_year"
        bot.send_message(msg.chat.id,
            "📅 <b>3/5</b> — Çykan <b>ýylyny</b> ýazyň:\n<i>Mysal: 1997</i>",
            parse_mode="HTML"); return

    if st == "mv_year" and is_admin(uid):
        states[uid]["year"] = msg.text; states[uid]["state"] = "mv_genre"
        bot.send_message(msg.chat.id,
            "🎭 <b>4/5</b> — <b>Žanryny</b> ýazyň:\n<i>Mysal: Drama, Romantik</i>",
            parse_mode="HTML"); return

    if st == "mv_genre" and is_admin(uid):
        states[uid]["genre"] = msg.text; states[uid]["state"] = "mv_desc"
        bot.send_message(msg.chat.id,
            "📝 <b>5/5</b> — Gysgaça <b>beýany</b> ýazyň:\n<i>1-3 sözlem</i>",
            parse_mode="HTML"); return

    if st == "mv_desc" and is_admin(uid):
        code = gen_code()
        conn = db(); c = conn.cursor()
        try:
            c.execute("""INSERT INTO movies
                (code,title,year,genre,description,file_id,file_type,views,added_at)
                VALUES (?,?,?,?,?,?,?,0,?)""",
                (code, sd["title"], sd["year"], sd["genre"],
                 msg.text, sd["fid"], sd["ftype"],
                 datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
            states.pop(uid, None)
            bot_info = bot.get_me()
            deep_link = f"https://t.me/{bot_info.username}?start={code}"
            bot.send_message(msg.chat.id,
                f"✅ <b>Kino goşuldy!</b>\n\n"
                f"🎬 <b>{sd['title']}</b> ({sd['year']})\n"
                f"🎭 {sd['genre']}\n"
                f"🔢 Kod: <code>{code}</code>\n\n"
                f"🔗 Paýlaşmak linki:\n<code>{deep_link}</code>",
                parse_mode="HTML")
        except Exception as e:
            bot.send_message(msg.chat.id, f"❌ Ýalňyşlyk: {e}")
        finally:
            conn.close()
        return

    # ════ KANAL GOŞMAK ════
    if st == "ch_id" and is_admin(uid):
        states[uid] = {"state": "ch_link", "channel_id": msg.text.strip()}
        bot.send_message(msg.chat.id,
            "2️⃣ Kanalyň <b>çakylyk linkini</b> ýaz:\n"
            "<i>Mysal: https://t.me/+abc ýa-da @username</i>",
            parse_mode="HTML"); return

    if st == "ch_link" and is_admin(uid):
        states[uid]["invite_link"] = fix_url(msg.text.strip())
        states[uid]["state"] = "ch_title"
        bot.send_message(msg.chat.id,
            "3️⃣ Kanalyň <b>adyny</b> ýaz:", parse_mode="HTML"); return

    if st == "ch_title" and is_admin(uid):
        conn = db(); c = conn.cursor()
        try:
            c.execute("INSERT OR REPLACE INTO channels (channel_id,title,invite_link) VALUES (?,?,?)",
                      (sd["channel_id"], msg.text.strip(), sd["invite_link"]))
            conn.commit()
            bot.send_message(msg.chat.id,
                f"✅ <b>Kanal goşuldy!</b> 📢 {msg.text.strip()}\n\n"
                f"⚠️ Boty kanalda <b>admin</b> edip goýmagy unutmaň!\n"
                f"Admin etmezden abuna barlamak işlemeýär.",
                parse_mode="HTML")
        except Exception as e:
            bot.send_message(msg.chat.id, f"❌ Ýalňyşlyk: {e}")
        finally:
            conn.close()
        states.pop(uid, None); return

    # ════ KINO POZMAK ════
    if st == "del_movie" and is_admin(uid):
        code = (msg.text or "").strip().upper()
        conn = db(); c = conn.cursor()
        c.execute("SELECT title FROM movies WHERE code=?", (code,))
        row = c.fetchone()
        if row:
            c.execute("DELETE FROM movies WHERE code=?", (code,))
            conn.commit()
            bot.send_message(msg.chat.id, f"✅ <b>{row[0]}</b> ({code}) pozuldy.", parse_mode="HTML")
        else:
            bot.send_message(msg.chat.id, f"❌ <b>{code}</b> tapylmady.", parse_mode="HTML")
        conn.close(); states.pop(uid, None); return

    # ════ REKLAMA ════
    if st == "bcast" and is_admin(uid):
        states.pop(uid, None)
        conn = db(); c = conn.cursor()
        c.execute("SELECT user_id FROM users")
        users = c.fetchall(); conn.close()
        sent = failed = 0
        sm = bot.send_message(msg.chat.id, "📣 Iberilýär...")
        for (u,) in users:
            try:
                if   msg.content_type == "text":
                    bot.send_message(u, msg.text, parse_mode="HTML")
                elif msg.content_type == "photo":
                    bot.send_photo(u, msg.photo[-1].file_id, caption=msg.caption or "", parse_mode="HTML")
                elif msg.content_type == "video":
                    bot.send_video(u, msg.video.file_id, caption=msg.caption or "", parse_mode="HTML")
                elif msg.content_type == "document":
                    bot.send_document(u, msg.document.file_id, caption=msg.caption or "", parse_mode="HTML")
                elif msg.content_type == "animation":
                    bot.send_animation(u, msg.animation.file_id, caption=msg.caption or "", parse_mode="HTML")
                sent += 1
            except Exception:
                failed += 1
        bot.edit_message_text(
            f"✅ <b>Reklama iberildi!</b>\n\n"
            f"📨 Iberilen: <b>{sent}</b>\n❌ Iberilmedik: <b>{failed}</b>",
            msg.chat.id, sm.message_id, parse_mode="HTML")
        return

    # ════ MENÝU DÜWMELERI ════
    if msg.content_type != "text": return
    text = msg.text.strip()
    if text in MENU_TEXTS: return

    # ════ GÖZLEG — Ad ýa-da Kod ════
    if require_sub(uid, msg.chat.id): return
    states.pop(uid, None)

    # Kod bilen (K0001)
    if text.upper().startswith("K") and len(text) == 5 and text[1:].isdigit():
        send_movie(msg.chat.id, text.upper()); return

    # Ad bilen gözleg
    conn = db(); c = conn.cursor()
    c.execute("""SELECT code,title,year,genre FROM movies
                 WHERE title LIKE ? OR genre LIKE ?
                 ORDER BY views DESC LIMIT 8""",
              (f"%{text}%", f"%{text}%"))
    results = c.fetchall(); conn.close()

    if not results:
        bot.send_message(msg.chat.id,
            f"❌ <b>'{text}'</b> üçin kino tapylmady.\n\n"
            f"🔍 Başga at ýa-da <code>K0001</code> ýaly kod ýazyň.",
            parse_mode="HTML"); return

    if len(results) == 1:
        send_movie(msg.chat.id, results[0][0]); return

    kb = types.InlineKeyboardMarkup()
    for code, title, year, genre in results:
        kb.add(types.InlineKeyboardButton(
            f"🎬 {title} ({year})", callback_data=f"getmv_{code}"))
    bot.send_message(msg.chat.id,
        f"🔍 <b>'{text}'</b> — {len(results)} kino tapyldy:",
        parse_mode="HTML", reply_markup=kb)


# ──────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    print("🎬 Kino Bot işe başlady...")
    bot.infinity_polling(skip_pending=True)
