import os
import discord
from discord.ext import commands
from flask import Flask
from threading import Thread

# =======================
# Flask keep-alive server
# =======================
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!"

def run():
    app.run(host="0.0.0.0", port=8080)

def keep_alive():
    Thread(target=run).start()


# =======================
# Discord Bot
# =======================
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ตั้งค่ารอบ / ช่อง / บอส
times = ["16.00", "18.00", "22.00"]
channels = ["CH-1", "CH-2"]
bosses = ["Sylph", "Undine", "Gnome", "Salamander"]

# เก็บข้อมูลปาร์ตี้
parties = {t: {c: {b: [] for b in bosses} for c in channels} for t in times}
user_party = {}  # เก็บ user_id → (time, channel, boss)


# =======================
# UI Components (Dropdown)
# =======================
class TimeSelect(discord.ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label=t, description=f"เลือกเวลา {t}") for t in times]
        super().__init__(placeholder="เลือกเวลา", options=options)

    async def callback(self, interaction: discord.Interaction):
        time = self.values[0]
        await interaction.response.edit_message(
            content=f"⏰ คุณเลือกเวลา {time}\nเลือก Channel ต่อไป:",
            view=ChannelView(time)
        )

class ChannelSelect(discord.ui.Select):
    def __init__(self, time):
        self.time = time
        options = [discord.SelectOption(label=c) for c in channels]
        super().__init__(placeholder="เลือก Channel", options=options)

    async def callback(self, interaction: discord.Interaction):
        ch = self.values[0]
        await interaction.response.edit_message(
            content=f"🛡️ คุณเลือก {self.time} {ch}\nเลือกบอสต่อไป:",
            view=BossView(self.time, ch)
        )

class BossSelect(discord.ui.Select):
    def __init__(self, time, ch):
        self.time = time
        self.ch = ch
        options = [discord.SelectOption(label=b) for b in bosses]
        super().__init__(placeholder="เลือกบอส", options=options)

    async def callback(self, interaction: discord.Interaction):
        boss = self.values[0]
        uid = interaction.user.id
        uname = interaction.user.name

        if uid in user_party:
            await interaction.response.send_message(
                f"⚠️ {uname} คุณ join ไปแล้ว ต้องใช้ `!leave` ก่อน", ephemeral=True
            )
            return

        if len(parties[self.time][self.ch][boss]) >= 5:
            await interaction.response.send_message(
                f"❌ ปาร์ตี้ {self.time} {self.ch} {boss} เต็มแล้ว", ephemeral=True
            )
            return

        parties[self.time][self.ch][boss].append(uid)
        user_party[uid] = (self.time, self.ch, boss)
        await interaction.response.send_message(
            f"✅ {uname} เข้าปาร์ตี้ {self.time} {self.ch} {boss}", ephemeral=False
        )

class TimeView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(TimeSelect())

class ChannelView(discord.ui.View):
    def __init__(self, time):
        super().__init__()
        self.add_item(ChannelSelect(time))

class BossView(discord.ui.View):
    def __init__(self, time, ch):
        super().__init__()
        self.add_item(BossSelect(time, ch))


# =======================
# Bot Commands
# =======================
@bot.event
async def on_ready():
    print(f"✅ Bot Online as {bot.user}")

# interactive join
@bot.command()
async def join(ctx):
    await ctx.send("โปรดเลือกเวลา:", view=TimeView())

# leave
@bot.command()
async def leave(ctx):
    uid = ctx.author.id
    uname = ctx.author.name
    if uid not in user_party:
        await ctx.send(f"⚠️ {uname} คุณไม่ได้อยู่ในปาร์ตี้")
        return
    time, ch, boss = user_party[uid]
    parties[time][ch][boss].remove(uid)
    del user_party[uid]
    await ctx.send(f"✅ {uname} ออกจากปาร์ตี้ {time} {ch} {boss}")

# list
@bot.command()
async def list(ctx, time: str, channel: str = None, boss: str = None):
    if time not in parties:
        await ctx.send(f"❌ ไม่มีปาร์ตี้เวลา `{time}`")
        return

    if channel and boss:
        if channel not in parties[time] or boss not in parties[time][channel]:
            await ctx.send(f"❌ ไม่พบปาร์ตี้ `{time} {channel} {boss}`")
            return
        members = parties[time][channel][boss]
        if not members:
            await ctx.send(f"📋 ปาร์ตี้ `{time} {channel} {boss}` ยังไม่มีคน")
        else:
            names = [bot.get_user(uid).name if bot.get_user(uid) else str(uid) for uid in members]
            await ctx.send(f"📋 ปาร์ตี้ `{time} {channel} {boss}` ({len(members)}/5): {', '.join(names)}")
        return

    # list ทุกปาร์ตี้ในเวลานั้น
    msg = f"📋 รายชื่อปาร์ตี้ทั้งหมด เวลา `{time}`:\n"
    for ch in parties[time]:
        for b in parties[time][ch]:
            members = parties[time][ch][b]
            if members:
                names = [bot.get_user(uid).name if bot.get_user(uid) else str(uid) for uid in members]
                msg += f"- {ch} {b} ({len(members)}/5): {', '.join(names)}\n"
            else:
                msg += f"- {ch} {b} (0/5): ยังไม่มีคน\n"
    await ctx.send(msg)

# clear
@bot.command()
async def clear(ctx):
    global parties, user_party
    parties = {t: {c: {b: [] for b in bosses} for c in channels} for t in times}
    user_party = {}
    await ctx.send("🧹 เคลียร์รายชื่อปาร์ตี้ทั้งหมดแล้ว")

# custom help
@bot.command(name="myhelp")
async def myhelp(ctx):
    help_text = (
        "**📌 วิธีใช้งานบอทปาร์ตี้**\n\n"
        "**!join** → ลงชื่อแบบเลือกเวลา/Channel/บอสผ่านเมนู\n"
        "**!leave** → ออกจากปาร์ตี้ที่คุณอยู่\n"
        "**!list <เวลา> <ช่อง> <บอส>** → ดูรายชื่อปาร์ตี้เฉพาะบอส\n"
        "**!list <เวลา>** → ดูรายชื่อปาร์ตี้ทั้งหมดในเวลานั้น\n"
        "**!clear** → ล้างรายชื่อปาร์ตี้ทั้งหมด\n"
        "**!myhelp** → แสดงข้อความช่วยเหลือนี้\n\n"
        "**🕒 รอบ:** 16.00 / 18.00 / 22.00\n"
        "**🏰 ช่อง:** CH-1 / CH-2\n"
        "**👹 บอส:** Sylph / Undine / Gnome / Salamander\n"
        "ตี้ละ 5 คน / คนเดียว join ได้แค่ปาร์ตี้เดียว ต้อง `!leave` ก่อน join ใหม่"
    )
    await ctx.send(help_text)


# =======================
# Run bot
# =======================
keep_alive()
bot.run(os.environ["DISCORD_BOT_TOKEN"])
