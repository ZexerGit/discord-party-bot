import os
import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ------------------------------
# โครงสร้างปาร์ตี้
# ------------------------------
parties = {
    "16.00": {"CH-1": {}, "CH-2": {}},
    "18.00": {"CH-1": {}, "CH-2": {}},
    "22.00": {"CH-1": {}, "CH-2": {}}
}

boss_list = ["Sylph", "Undine", "Gnome", "Salamander"]
for t in parties:
    for ch in parties[t]:
        for boss in boss_list:
            parties[t][ch][boss] = []

user_party = {}  # user_id → (time, ch, boss)

# ------------------------------
# View สำหรับ Join
# ------------------------------
class JoinView(discord.ui.View):
    def __init__(self, user):
        super().__init__(timeout=120)
        self.user = user
        self.selected_time = None
        self.selected_ch = None
        self.selected_boss = None

        # เวลา
        self.time_select = discord.ui.Select(
            placeholder="เลือกเวลา",
            options=[discord.SelectOption(label=t) for t in parties.keys()]
        )
        self.time_select.callback = self.time_callback
        self.add_item(self.time_select)

        # Channel
        self.ch_select = discord.ui.Select(
            placeholder="เลือก Channel",
            options=[discord.SelectOption(label="CH-1"), discord.SelectOption(label="CH-2")]
        )
        self.ch_select.callback = self.ch_callback
        self.add_item(self.ch_select)

        # Boss
        self.boss_select = discord.ui.Select(
            placeholder="เลือกบอส",
            options=[discord.SelectOption(label=boss) for boss in boss_list]
        )
        self.boss_select.callback = self.boss_callback
        self.add_item(self.boss_select)

        # Confirm button
        self.confirm_button = discord.ui.Button(label="✅ ยืนยัน", style=discord.ButtonStyle.green)
        self.confirm_button.callback = self.confirm_callback
        self.add_item(self.confirm_button)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.user:
            await interaction.response.send_message("❌ คุณไม่สามารถกด UI ของคนอื่นได้", ephemeral=True)
            return False
        return True

    async def time_callback(self, interaction: discord.Interaction):
        self.selected_time = self.time_select.values[0]
        await interaction.response.defer()

    async def ch_callback(self, interaction: discord.Interaction):
        self.selected_ch = self.ch_select.values[0]
        await interaction.response.defer()

    async def boss_callback(self, interaction: discord.Interaction):
        self.selected_boss = self.boss_select.values[0]
        await interaction.response.defer()

    async def confirm_callback(self, interaction: discord.Interaction):
        if not (self.selected_time and self.selected_ch and self.selected_boss):
            await interaction.response.send_message("⚠️ ต้องเลือกครบทั้ง เวลา, Channel, และ Boss ก่อน", ephemeral=True)
            return

        user_id = self.user.id
        user_name = self.user.display_name

        if user_id in user_party:
            await interaction.response.send_message("⚠️ คุณอยู่ปาร์ตี้อื่นอยู่แล้ว ใช้ !leave ก่อน", ephemeral=True)
            return

        members = parties[self.selected_time][self.selected_ch][self.selected_boss]
        if len(members) >= 5:
            await interaction.response.send_message("❌ ปาร์ตี้นี้เต็มแล้ว", ephemeral=True)
            return

        members.append(user_name)
        user_party[user_id] = (self.selected_time, self.selected_ch, self.selected_boss)
        await interaction.response.send_message(
            f"✅ {user_name} เข้าร่วมปาร์ตี้ {self.selected_time} {self.selected_ch} {self.selected_boss}", ephemeral=True
        )
        self.stop()  # ปิด View หลัง Confirm

# ------------------------------
# คำสั่งบอท
# ------------------------------
@bot.command()
async def join(ctx):
    """เริ่มต้นการ Join แบบ UI เลือกครบ 3 อย่าง"""
    view = JoinView(ctx.author)
    await ctx.send("เลือก เวลา / Channel / Boss แล้วกด ✅ ยืนยัน", view=view)

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
    msg = (
        "📖 **วิธีใช้งานบอทปาร์ตี้**\n"
        "`!join` → เลือก เวลา / Channel / Boss พร้อมกัน\n"
        "`!leave` → ออกจากปาร์ตี้ปัจจุบัน\n"
        "`!list [เวลา]` → ดูรายชื่อปาร์ตี้ (ใส่เวลา เช่น `16.00` หรือไม่ใส่เพื่อดูทั้งหมด)\n"
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
