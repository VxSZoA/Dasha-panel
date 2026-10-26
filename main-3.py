import asyncio, json, os, random
from highrise import BaseBot, User, Position
from highrise.models import Item, SessionMetadata

OWNER = "i.t4"
DATA = "data.json"

# ================= دنس‌ها =================
# ترتیب همین لیسته؛ شماره هر دنس با !dances دیده می‌شه
GROUPS = [
    ("dance-", "macarena floss tiktok2 tiktok8 tiktok9 tiktok10 tiktok11 blackpink pennywise russian shoppingcart weird zombie employee handsup kawai touch sexy icecream wild metal orangejustice jinglebell anime creepypuppet spiritual smoothwalk singlelady"),
    ("emote-", "ghost-idle float hello wave kiss laughing sad shy tired lust greedy model cutey curtsy bow flex gagging judochop theatrical snowball snowangel hot hug no yes confused charging frollicking teleporting telekinesis superpose snake maniac embarrassed boo zombierun shrink swordfight stargazer slap think peekaboo ropepull death death2 fainting gordonshuffle hearteyes heartfingers heartshape celebrationstep apart wings iceskating timejump proposing pose1 pose3 pose5 pose7 pose8"),
    ("idle-", "dance-casual dance-tiktok7 dance-swinging dance-tiktok4 loop-tapdance loop-aerobics loop-happy loop-sad loop-shy loop-tired loop-annoyed guitar uwu fighter hero enthusiastic angry singing"),
    ("emoji-", "angry cursing flex gagging celebrate crying dizzy eyeroll halo hadoken lying naughty pray punch sing scared shake sleep thumbsup arrogance poop"),
]
KEY_OVERRIDE = {"emote-ghost-idle": "ghostfloat"}
DUR = {}            # مدت دقیق دنس‌ها (ثانیه): {"ghostfloat": 20}
DEFAULT_DUR = 10    # مدت پیش‌فرض بین هر تکرار

EMOTES = {}
for prefix, names in GROUPS:
    for n in names.split():
        eid = prefix + n
        key = KEY_OVERRIDE.get(eid) or n.replace("dance-", "", 1).replace("loop-", "", 1)
        if key in EMOTES:
            key = prefix.strip("-") + "_" + key
        EMOTES[key] = (eid, DUR.get(key, DEFAULT_DUR))

PAGES, _cur = [], ""
for _i, _k in enumerate(EMOTES, 1):
    _t = f"{_i}.{_k} "
    if len(_cur) + len(_t) > 230:
        PAGES.append(_cur)
        _cur = ""
    _cur += _t
PAGES.append(_cur)

# ================= پیام‌های لوپ =================
LOOP_MESSAGES = [
    "به روم ما خوش اومدید 💜",
    "قوانین رو رعایت کنید 🙏",
    "برای دیدن لیست دنس‌ها بنویسید: !dances",
]
LOOP_EVERY = 120  # ثانیه

JOKES = [
    "به معلمه میگه: کسی که کار نکرده رو تنبیه نکنید. میگه: آفرین. میگه: پس منو تنبیه نکنید 😂",
    "گفتم رژیم بگیرم، یخچال گفت: منم باهات میام 😅",
    "ساعت ۳ شب مغزم: یادته ۱۰ سال پیش چی گفتی؟ 🤡",
]


def load():
    if os.path.exists(DATA):
        try:
            d = json.load(open(DATA, encoding="utf-8"))
        except Exception:
            d = {}
    else:
        d = {}
    d.setdefault("admins", [])
    d.setdefault("spots", {})
    d.setdefault("banned", {})
    return d


def save(d):
    json.dump(d, open(DATA, "w", encoding="utf-8"), ensure_ascii=False)


class Bot(BaseBot):
    async def on_start(self, session_metadata: SessionMetadata) -> None:
        self.db = load()
        self.dances = {}
        asyncio.create_task(self.msg_loop())
        print("Bot started")

    async def msg_loop(self):
        i = 0
        while True:
            await asyncio.sleep(LOOP_EVERY)
            try:
                await self.highrise.chat(LOOP_MESSAGES[i % len(LOOP_MESSAGES)])
            except Exception:
                pass
            i += 1

    # ---------- ابزارها ----------
    def is_admin(self, user):
        return user.username == OWNER or user.username in self.db["admins"]

    async def room_users(self):
        return (await self.highrise.get_room_users()).content

    async def find_user(self, name):
        name = name.lstrip("@").lower()
        for u, _ in await self.room_users():
            if u.username.lower() == name:
                return u

    async def user_pos(self, uid):
        for u, p in await self.room_users():
            if u.id == uid and isinstance(p, Position):
                return p

    # ---------- دنس بی‌پایان ----------
    async def dance_loop(self, uid, emote, dur):
        while True:
            try:
                await self.highrise.send_emote(emote, uid)
            except Exception:
                self.dances.pop(uid, None)
                return
            await asyncio.sleep(dur)

    def stop_dance(self, uid):
        t = self.dances.pop(uid, None)
        if t:
            t.cancel()

    # ---------- رویدادها ----------
    async def on_user_join(self, user: User, position) -> None:
        await self.highrise.chat(f"خوش اومدی {user.username} 🎉")

    async def on_user_leave(self, user: User) -> None:
        self.stop_dance(user.id)

    async def on_chat(self, user: User, message: str) -> None:
        text = message.strip()
        if not text:
            return
        parts = text.split()
        cmd, args = parts[0].lower(), parts[1:]
        word = text.lower()

        # ---- دنس: فقط اسم یا شماره ----
        names = list(EMOTES)
        key = None
        if word in EMOTES:
            key = word
        elif word.isdigit() and 1 <= int(word) <= len(names):
            key = names[int(word) - 1]
        elif cmd == "!dance" and args and args[0].lower() in EMOTES:
            key = args[0].lower()
        if key:
            self.stop_dance(user.id)
            eid, dur = EMOTES[key]
            self.dances[user.id] = asyncio.create_task(self.dance_loop(user.id, eid, dur))
            return

        # ---- دستورهای همگانی ----
        if cmd == "!stop":
            self.stop_dance(user.id)
            return
        if cmd == "!dances":
            p = int(args[0]) if args and args[0].isdigit() else 1
            p = min(max(p, 1), len(PAGES))
            await self.highrise.chat(f"[{p}/{len(PAGES)}] " + PAGES[p - 1])
            return
        if cmd == "!admins":
            await self.highrise.chat("👑 اونر: " + OWNER + " | ادمین‌ها: " + (", ".join(self.db["admins"]) or "ندارد"))
            return
        if cmd == "!joke":
            await self.highrise.chat(random.choice(JOKES))
            return
        if cmd == "!dice":
            await self.highrise.chat(f"🎲 {user.username}: {random.randint(1, 6)}")
            return
        if cmd == "!love" and args:
            await self.highrise.chat(f"💘 عشق {user.username} و {args[0]}: {random.randint(1, 100)}٪")
            return
        if cmd == "!8ball":
            await self.highrise.chat(random.choice(["آره ✅", "نه ❌", "شاید 🤔", "بعداً بپرس 🔮"]))
            return

        # ---- از اینجا فقط ادمین ----
        if not self.is_admin(user):
            return

        if cmd in ("!ban", "!kick") and args:
            t = await self.find_user(args[0])
            if not t:
                await self.highrise.chat("کاربر توی روم نیست")
                return
            if t.username == OWNER:
                return
            if cmd == "!ban":
                self.db["banned"][t.username.lower()] = t.id
                save(self.db)
                await self.highrise.moderate_room(t.id, "ban", 3600 * 24)
                await self.highrise.chat(f"{t.username} بن شد 🚫")
            else:
                await self.highrise.moderate_room(t.id, "kick")
                await self.highrise.chat(f"{t.username} کیک شد 👢")

        elif cmd == "!unban" and args:
            uid = self.db["banned"].pop(args[0].lstrip("@").lower(), None)
            if uid:
                save(self.db)
                await self.highrise.moderate_room(uid, "unban")
                await self.highrise.chat("آنبن شد ✅")
            else:
                await self.highrise.chat("این کاربر توی لیست بن نیست")

        elif cmd == "!setspot" and args:
            p = await self.user_pos(user.id)
            if p:
                self.db["spots"][args[0]] = [p.x, p.y, p.z, p.facing]
                save(self.db)
                await self.highrise.chat(f"موقعیت {args[0]} ذخیره شد 📍")
            else:
                await self.highrise.chat("اول بایست (روی صندلی نباش)")

        elif cmd == "!spots":
            await self.highrise.chat("موقعیت‌ها: " + (", ".join(self.db["spots"]) or "ندارد"))

        elif cmd == "!tp" and len(args) >= 2:
            t = await self.find_user(args[0])
            s = self.db["spots"].get(args[1])
            if t and s:
                await self.highrise.teleport(t.id, Position(*s))

        elif cmd == "!tpme" and args:
            s = self.db["spots"].get(args[0])
            if s:
                await self.highrise.teleport(user.id, Position(*s))

        elif cmd == "!tpall":
            # !tpall -> همه پیش خودت | !tpall نام -> همه به اون موقعیت
            if args:
                s = self.db["spots"].get(args[0])
                dest = Position(*s) if s else None
            else:
                dest = await self.user_pos(user.id)
            if not dest:
                await self.highrise.chat("موقعیت پیدا نشد")
                return
            my_id = getattr(self.highrise, "my_id", None)
            for u, _ in await self.room_users():
                if u.id in (user.id, my_id):
                    continue
                try:
                    await self.highrise.teleport(u.id, dest)
                except Exception:
                    pass

        elif cmd == "!outfit" and args:
            # !outfit id1,id2,id3  (آیدی آیتم‌های لباس)
            items = [Item(type="clothing", amount=1, id=i, account_bound=False, active_palette=-1)
                     for i in args[0].split(",")]
            await self.highrise.set_outfit(items)

        elif cmd == "!say" and args:
            await self.highrise.chat(" ".join(args))

        # ---- فقط اونر ----
        elif cmd == "!addadmin" and args and user.username == OWNER:
            n = args[0].lstrip("@")
            if n not in self.db["admins"]:
                self.db["admins"].append(n)
                save(self.db)
            await self.highrise.chat(f"{n} ادمین شد ✅")

        elif cmd == "!deladmin" and args and user.username == OWNER:
            n = args[0].lstrip("@")
            if n in self.db["admins"]:
                self.db["admins"].remove(n)
                save(self.db)
            await self.highrise.chat(f"{n} از ادمینی حذف شد")
