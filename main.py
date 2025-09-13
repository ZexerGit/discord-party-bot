import discord
from discord.ext import commands
import os

# Keep-alive สำหรับ Railway
try:
    import keep_alive
    keep_alive.keep_alive()
except:
    pass

# ตั้ง intents
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# กำหนดปาร์ตี้ล่วงหน้า
times = ["16.00", "18.00", "22.00"]
channels = ["CH-1", "CH-2"]
bosses = ["Sylph", "Undine", "Gnome", "Salamander"]

parties = {}
for t in times:
    parties[t] = {}
    for ch in channels:
        parties[t][ch] = {}
        for b in bosses:
            parties[t][ch][b] = []

# เก็บ mapping คน -> ปาร์ตี้ที่ join
user_party = {}  # user_id : (time, channel, boss)

@bot.event
async def on_ready():
    print(f"✅ Bot Online as {bot.user}")

# join ปาร์ตี้
@bot.command()
async def join(ctx, time: str, channel: str, boss_name: str):
    user_id = ctx.author.id
    user_name = ctx.author.name

    if time not in parties or channel not in parties[time] or boss_name not in parties[time][channel]:
        await ctx.send(f"❌ ไม่พบปาร์ตี้ `{time} {channel} {boss_name}`")
        return

    if user_id in user_party:
        await ctx.send(f"⚠️ {user_name} คุณอยู่ปาร์ตี้อื่นอยู่แล้ว ใช้ `!leave` ก่อน join ใหม่")
        return

    if len(parties[time][channel][boss_name]) >= 5:
        await ctx.send(f"❌ ปาร์ตี้ `{time} {channel} {boss_name}` เต็มแล้ว")
        return

    parties[time][channel][boss_name].append(user_id)
    user_party[user_id] = (time, channel, boss_name)
    await ctx.send(f"✅ {user_name} เข้าปาร์ตี้ `{time} {channel} {boss_name}` ({len(parties[time][channel][boss_name])}/5)")

# leave ปาร์ตี้
@bot.command()
async def leave(ctx):
    user_id = ctx.author.id
    user_name = ctx.author.name

    if user_id not in user_party:
        await ctx.send(f"⚠️ {user_name} คุณไม่ได้อยู่ปาร์ตี้ใดๆ")
        return

    time, channel, boss_name = user_party[user_id]
    parties[time][channel][boss_name].remove(user_id)
    del user_party[user_id]
    await ctx.send(f"✅ {user_name} ออกจากปาร์ตี้ `{time} {channel} {boss_name}` เรียบร้อยแล้ว")

# list ปาร์ตี้
@bot.command()
async def list(ctx, time: str, channel: str = None, boss_name: str = None):
    if time not in parties:
        await ctx.send(f"❌ ไม่มีปาร์ตี้เวลา `{time}`")
        return

    # ถ้าใส่ channel และ boss_name (แบบเดิม)
    if channel and boss_name:
        if channel not in parties[time] or boss_name not in parties[time][channel]:
            await ctx.send(f"❌ ไม่พบปาร์ตี้ `{time} {channel} {boss_name}`")
            return
        members = parties[time][channel][boss_name]
        if not members:
            await ctx.send(f"📋 ปาร์ตี้ `{time} {channel} {boss_name}` ยังไม่มีคน")
        else:
            member_names = [bot.get_user(uid).name if bot.get_user(uid) else str(uid) for uid in members]
            await ctx.send(f"📋 ปาร์ตี้ `{time} {channel} {boss_name}` ({len(members)}/5): {', '.join(member_names)}")
        return

    # ถ้าใส่แค่เวลา → list ทุกปาร์ตี้ในเวลานั้น
    msg = f"📋 รายชื่อปาร์ตี้ทั้งหมด เวลา `{time}`:\n"
    for ch in parties[time]:
        for b in parties[time][ch]:
            members = parties[time][ch][b]
            if members:
                member_names = [bot.get_user(uid).name if bot.get_user(uid) else str(uid) for uid in members]
                msg += f"- {ch} {b} ({len(members)}/5): {', '.join(member_names)}\n"
            else:
                msg += f"- {ch} {b} (0/5): ยังไม่มีคน\n"
    await ctx.send(msg)

# ล้างรายชื่อทั้งหมด
@bot.command()
async def clear(ctx):
    global parties, user_party
    for t in parties:
        for ch in parties[t]:
            for b in parties[t][ch]:
                parties[t][ch][b] = []
    user_party = {}
    await ctx.send("✅ ล้างรายชื่อปาร์ตี้ทั้งหมดเรียบร้อยแล้ว")

# คำสั่งทดสอบ
@bot.command()
async def test(ctx):
    await ctx.send("Bot รับคำสั่งได้ ✅")

# คำสั่ง myhelp อธิบายการใช้งานทั้งหมด
@bot.command(name="myhelp")
async def myhelp(ctx):
    help_text = (
        "**📌 วิธีใช้งานบอทปาร์ตี้**\n\n"
        "**!join <เวลา> <ช่อง> <บอส>** → ลงชื่อเข้าปาร์ตี้ ตัวอย่าง: `!join 16.00 CH-1 Sylph`\n"
        "**!leave** → ออกจากปาร์ตี้ที่คุณอยู่\n"
        "**!list <เวลา> <ช่อง> <บอส>** → ดูรายชื่อปาร์ตี้เฉพาะบอส\n"
        "**!list <เวลา>** → ดูรายชื่อปาร์ตี้ทั้งหมดในเวลานั้น\n"
        "**!clear** → ล้างรายชื่อปาร์ตี้ทั้งหมด\n"
        "**!test** → ทดสอบบอทว่าทำงานหรือไม่\n"
        "**!myhelp** → แสดงข้อความช่วยเหลือวิธีใช้งานนี้\n\n"
        "**🕒 รอบปาร์ตี้:** 16.00 / 18.00 / 22.00\n"
        "**🏰 ช่อง:** CH-1 / CH-2\n"
        "**👹 บอส:** Sylph / Undine / Gnome / Salamander\n"
        "ตี้ละ 5 คน / คนเดียว join ได้แค่ปาร์ตี้เดียว ต้อง `!leave` ก่อน join ใหม่"
    )
    await ctx.send(help_text)

# รันบอท
bot.run(os.environ["DISCORD_BOT_TOKEN"])
