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
intents.members = True          # สำหรับเรียกชื่อสมาชิก
intents.message_content = True  # สำหรับอ่านคำสั่งข้อความ

bot = commands.Bot(command_prefix="!", intents=intents)

# เก็บปาร์ตี้ {party_name: [user_id, ...]}
parties = {}

@bot.event
async def on_ready():
    print(f"✅ Bot Online as {bot.user}")

# สร้างปาร์ตี้ใหม่
@bot.command()
async def party(ctx, name: str):
    if name in parties:
        await ctx.send(f"❌ ปาร์ตี้ `{name}` มีอยู่แล้ว")
    else:
        parties[name] = []
        await ctx.send(f"🎉 ปาร์ตี้ `{name}` ถูกสร้างแล้ว (รับ 5 คน)")

# ลงชื่อเข้าปาร์ตี้
@bot.command()
async def join(ctx, name: str):
    user_id = ctx.author.id
    if name not in parties:
        await ctx.send(f"❌ ไม่มีปาร์ตี้ชื่อ `{name}`")
        return
    if user_id in parties[name]:
        await ctx.send(f"⚠️ {ctx.author.name} ลงชื่อไปแล้ว")
        return
    if len(parties[name]) >= 5:
        await ctx.send(f"❌ ปาร์ตี้ `{name}` เต็มแล้ว")
        return
    parties[name].append(user_id)
    await ctx.send(f"✅ {ctx.author.name} เข้าปาร์ตี้ `{name}` ({len(parties[name])}/5)")

# ดูรายชื่อคนในปาร์ตี้
@bot.command()
async def list(ctx, name: str):
    if name not in parties:
        await ctx.send(f"❌ ไม่มีปาร์ตี้ชื่อ `{name}`")
        return
    members = parties[name]
    if not members:
        await ctx.send(f"📋 ปาร์ตี้ `{name}` ยังไม่มีคน")
    else:
        member_names = [bot.get_user(uid).name if bot.get_user(uid) else str(uid) for uid in members]
        await ctx.send(f"📋 ปาร์ตี้ `{name}` ({len(members)}/5): {', '.join(member_names)}")

# คำสั่งทดสอบว่าบอททำงาน
@bot.command()
async def test(ctx):
    await ctx.send("Bot รับคำสั่งได้ ✅")

# รันบอทด้วย Token จาก Environment Variable
bot.run(os.environ["DISCORD_BOT_TOKEN"])
