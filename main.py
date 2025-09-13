import os
import discord
from discord.ext import commands

# ------------------------------
# ตั้งค่า Intents
# ------------------------------
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ------------------------------
# โครงสร้างปาร์ตี้
# ------------------------------
parties = {
    "16.00": {
        "CH-1": {"Sylph": [], "Undine": [], "Gnome": [], "Salamander": []},
        "CH-2": {"Sylph": [], "Undine": [], "Gnome": [], "Salamander": []}
    },
    "18.00": {
        "CH-1": {"Sylph": [], "Undine": [], "Gnome": [], "Salamander": []},
        "CH-2": {"Sylph": [], "Undine": [], "Gnome": [], "Salamander": []}
    },
    "22.00": {
        "CH-1": {"Sylph": [], "Undine": [], "Gnome": [], "Salamander": []},
        "CH-2": {"Sylph": [], "Undine": [], "Gnome": [], "Salamander": []}
    }
}

user_party = {}  # user_id → (time, ch, boss)

# ------------------------------
# UI Dropdowns (เวลา / CH / Boss)
# ------------------------------
class BossSelect(discord.ui.Select):
    def __init__(self, time, ch):
        self.time = time
        self.ch = ch
        options = [discord.SelectOption(label=boss) for boss in parties[time][ch].keys()]
        super().__init__(placeholder="เลือกบอส", options=options)

    async def callback(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        user_name = interaction.user.display_name
        boss = self.values[0]

        if user_id in user_party:
            await interaction.response.send_message("⚠️ คุณอยู่ปาร์ตี้อื่นอยู่แล้ว ใช้ !leave ก่อน", ephemeral=True)
            return

        members = parties[self.time][self.ch][boss]
        if len(members) >= 5:
            await interaction.response.send_message("❌ ปาร์ตี้นี้เต็มแล้ว", ephemeral=True)
            return

        members.append(user_name)
        user_party[user_id] = (self.time, self.ch, boss)
        await interaction.response.send_message(
            f"✅ {user_name} เข้าร่วมปาร์ตี้ {self.time} {self.ch} {boss}", ephemeral=True
        )

class ChannelSelect(discord.ui.Select):
    def __init__(self, time):
        self.time = time
        options = [discord.SelectOption(label="CH-1"), discord.SelectOption(label="CH-2")]
        super().__init__(placeholder="เลือก Channel", options=options)

    async def callback(self, interaction: discord.Interaction):
        ch = self.values[0]
        view = discord.ui.View()
        view.add_item(BossSelect(self.time, ch))
        await interaction.response.send_message(f"เลือก Boss ใน {ch}", view=view, ephemeral=True)

class TimeSelect(discord.ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label=t) for t in parties.keys()]
        super().__init__(placeholder="เลือกเวลา", options=options)

    async def callback(self, interaction: discord.Interaction):
        time = self.values[0]
        view = discord.ui.View()
        view.add_item(ChannelSelect(time))
        await interaction.response.send_message(f"เลือก Channel สำหรับเวลา {time}", view=view, ephemeral=True)

# ------------------------------
# คำสั่งบอท
# ------------------------------
@bot.command()
async def join(ctx):
    """เริ่มต้นการ Join แบบเมนูเลือก"""
    view = discord.ui.View()
    view.add_item(TimeSelect())
    await ctx.send("เลือกเวลา:", view=view)

@bot.command()
async def leave(ctx):
    """ออกจากปาร์ตี้"""
    user_id = ctx.author.id
    if user_id not in user_party:
        await ctx.send("⚠️ คุณไม่ได้อยู่ในปาร์ตี้ใดๆ")
        return

    time, ch, boss = user_party[user_id]
    parties[time][ch][boss].remove(ctx.author.display_name)
    del user_party[user_id]
    await ctx.send(f"↩️ {ctx.author.display_name} ออกจากปาร์ตี้ {time} {ch} {boss}")

@bot.command()
async def list(ctx, time: str = None):
    """แสดงรายชื่อผู้เล่น"""
    if time:
        if time not in parties:
            await ctx.send("⚠️ เวลาไม่ถูกต้อง (ใช้ 16.00, 18.00, 22.00)")
            return
        msg = f"📋 รายชื่อปาร์ตี้เวลา {time}\n"
        for ch in parties[time]:
            msg += f"\n**{ch}**\n"
            for boss, members in parties[time][ch].items():
                names = ", ".join(members) if members else "-"
                msg += f"- {boss}: {names}\n"
        await ctx.send(msg)
    else:
        msg = "📋 **รายชื่อทุกเวลา**\n"
        for t in parties:
            msg += f"\n⏰ เวลา {t}\n"
            for ch in parties[t]:
                msg += f"\n**{ch}**\n"
                for boss, members in parties[t][ch].items():
                    names = ", ".join(members) if members else "-"
                    msg += f"- {boss}: {names}\n"
        await ctx.send(msg)

@bot.command()
async def clear(ctx):
    """ล้างข้อมูลปาร์ตี้ทั้งหมด"""
    for t in parties:
        for ch in parties[t]:
            for boss in parties[t][ch]:
                parties[t][ch][boss] = []
    user_party.clear()
    await ctx.send("🧹 ล้างข้อมูลปาร์ตี้ทั้งหมดแล้ว")

@bot.command(name="helpme")
async def helpme(ctx):
    """แสดงวิธีใช้งาน"""
    msg = (
        "📖 **วิธีใช้งานบอทปาร์ตี้**\n"
        "`!join` → เลือกเวลา, Channel, Boss เพื่อเข้าปาร์ตี้\n"
        "`!leave` → ออกจากปาร์ตี้ปัจจุบัน\n"
        "`!list [เวลา]` → ดูรายชื่อปาร์ตี้ (ใส่เวลาเช่น `16.00` หรือไม่ใส่เพื่อดูทั้งหมด)\n"
        "`!clear` → ล้างข้อมูลปาร์ตี้ทั้งหมด (แอดมินใช้)\n"
    )
    await ctx.send(msg)

# ------------------------------
# Run bot
# ------------------------------
@bot.event
async def on_ready():
    print(f"✅ Bot Online as {bot.user}")

bot.run(os.environ["DISCORD_BOT_TOKEN"])
