import discord
from discord.ext import commands
import os

# ถ้าอยากให้บอทออนไลน์ตลอด 24/7
try:
    import keep_alive
    keep_alive.keep_alive()
except:
    pass

# ตั้ง intents สำหรับ Discord.py เวอร์ชันใหม่
intents = discord.Intents.default()
intents.members = True  # จำเป็นถ้าเราจะเรียกชื่อผู้ใช้จาก ID
bot = commands.Bot(command_prefix="@", intents=intents)

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
    user_name = ctx.author.name

    if name not in parties:
        await ctx.send(f"❌ ไม่มีปาร์ตี้ชื่อ `{name}`")
        return

    if user_id in parties[name]:
        await ctx.send(f"⚠️ {user_name} ลงชื่อไปแล้ว")
        return

    if len(parties[name]) >= 5:
        await ctx.send(f"❌ ปาร์ตี้ `{name}` เต็มแล้ว")
        return

    parties[name].append(user_id)
    await ctx.send(f"✅ {user_name} เข้าปาร์ตี้ `{name}` ({len(parties[name])}/5)")

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

# รันบอทด้วย Token จาก Environment Variable
bot.run(os.environ["DISCORD_BOT_TOKEN"])
