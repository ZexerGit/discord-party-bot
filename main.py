import os
import discord
from discord.ext import commands
from discord import app_commands

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ------------------------------
# ตั้งค่า
ADMIN_PASSWORD = "osysadmin"
DEFAULT_JOIN_TIME = "12.00"

# ------------------------------
# โครงสร้างปาร์ตี้
parties = {t: {ch: {boss: [] for boss in ["Sylph", "Undine", "Gnome", "Salamander"]}
            for ch in ["CH-1", "CH-2"]} for t in ["16.00", "18.00", "22.00"]}

user_party = {}  # user_id -> (time, ch, boss, count)
join_time = DEFAULT_JOIN_TIME  # เวลาเริ่ม join

# ------------------------------
# UI Join View
class JoinView(discord.ui.View):
    def __init__(self, user):
        super().__init__(timeout=180)
        self.user = user
        self.selected_time = None
        self.selected_ch = None
        self.selected_boss = None
        self.selected_count = 1

        self.time_select = discord.ui.Select(
            placeholder="เลือกเวลา",
            options=[discord.SelectOption(label=t) for t in parties.keys()]
        )
        self.time_select.callback = self.time_callback
        self.add_item(self.time_select)

        self.ch_select = discord.ui.Select(
            placeholder="เลือก Channel",
            options=[discord.SelectOption(label="CH-1"), discord.SelectOption(label="CH-2")]
        )
        self.ch_select.callback = self.ch_callback
        self.add_item(self.ch_select)

        self.boss_select = discord.ui.Select(
            placeholder="เลือก Boss",
            options=[discord.SelectOption(label=boss) for boss in ["Sylph", "Undine", "Gnome", "Salamander"]]
        )
        self.boss_select.callback = self.boss_callback
        self.add_item(self.boss_select)

        self.count_select = discord.ui.Select(
            placeholder="เลือกจำนวนคน (1–5)",
            options=[discord.SelectOption(label=str(i)) for i in range(1, 6)]
        )
        self.count_select.callback = self.count_callback
        self.add_item(self.count_select)

        self.confirm_button = discord.ui.Button(label="✅ ยืนยันเข้าปาร์ตี้", style=discord.ButtonStyle.green)
        self.confirm_button.callback = self.confirm_callback
        self.add_item(self.confirm_button)

        self.leave_button = discord.ui.Button(label="↩️ ออกจากปาร์ตี้", style=discord.ButtonStyle.red)
        self.leave_button.callback = self.leave_callback
        self.add_item(self.leave_button)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.user:
            await interaction.response.send_message("❌ คุณไม่สามารถกด UI ของคนอื่นได้", ephemeral=True)
            return False
        return True

    async def time_callback(self, interaction: discord.Interaction):
        self.selected_time = self.time_select.values[0]
        await interaction.response.defer(ephemeral=True)

    async def ch_callback(self, interaction: discord.Interaction):
        self.selected_ch = self.ch_select.values[0]
        await interaction.response.defer(ephemeral=True)

    async def boss_callback(self, interaction: discord.Interaction):
        self.selected_boss = self.boss_select.values[0]
        await interaction.response.defer(ephemeral=True)

    async def count_callback(self, interaction: discord.Interaction):
        self.selected_count = int(self.count_select.values[0])
        await interaction.response.defer(ephemeral=True)

    async def confirm_callback(self, interaction: discord.Interaction):
        import datetime
        now_hour = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7))).hour
        now_min = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7))).minute
        current_time = f"{now_hour:02d}.{now_min:02d}"

        # Check join_time
        join_hour, join_min = map(int, join_time.split("."))
        if (now_hour, now_min) < (join_hour, join_min):
            await interaction.response.send_message(
                f"⏳ ยังไม่ถึงเวลา join โปรดรอ {join_time} เป็นต้นไป", ephemeral=True
            )
            return

        if not (self.selected_time and self.selected_ch and self.selected_boss and self.selected_count):
            await interaction.response.send_message("⚠️ ต้องเลือกครบ เวลา/CH/Boss/จำนวนคน ก่อน", ephemeral=True)
            return

        uid = self.user.id
        if uid in user_party:
            await interaction.response.send_message("⚠️ คุณอยู่ปาร์ตี้อื่นอยู่แล้ว ใช้ Leave ก่อน", ephemeral=True)
            return

        members = parties[self.selected_time][self.selected_ch][self.selected_boss]
        remaining_slots = 5 - len(members)

        if remaining_slots <= 0:
            await interaction.response.send_message("❌ ปาร์ตี้เต็มแล้ว", ephemeral=True)
            return

        if self.selected_count > remaining_slots:
            await interaction.response.send_message(
                f"⚠️ ไม่สามารถเข้าร่วมปาร์ตี้ได้ เนื่องจากเหลือ {remaining_slots} ที่ แต่คุณเลือก {self.selected_count} คน",
                ephemeral=True
            )
            return

        # ✅ เพิ่มสมาชิก
        members.extend([uid] * self.selected_count)
        user_party[uid] = (self.selected_time, self.selected_ch, self.selected_boss, self.selected_count)

        await interaction.response.send_message(
            f"✅ {self.user.display_name} เข้าปาร์ตี้ {self.selected_time} {self.selected_ch} {self.selected_boss} "
            f"({len(members)}/5 คน, ลงแทน {self.selected_count-1} คน)",
            ephemeral=True
        )

    async def leave_callback(self, interaction: discord.Interaction):
        uid = self.user.id
        if uid not in user_party:
            await interaction.response.send_message("⚠️ คุณไม่ได้อยู่ปาร์ตี้ใดๆ", ephemeral=True)
            return

        time, ch, boss, count = user_party[uid]
        members = parties[time][ch][boss]
        for _ in range(count):
            if uid in members:
                members.remove(uid)

        del user_party[uid]
        await interaction.response.send_message(
            f"↩️ {self.user.display_name} ออกจากปาร์ตี้ {time} {ch} {boss} (คืน {count} ที่นั่ง)",
            ephemeral=True
        )

# ------------------------------
# Modal สำหรับ delete (admin)
class DeleteModal(discord.ui.Modal, title="ลบสมาชิกจากปาร์ตี้ (admin)"):
    time_select = discord.ui.TextInput(label="เวลา (เช่น 16.00)")
    ch_select = discord.ui.TextInput(label="Channel (CH-1 หรือ CH-2)")
    boss_select = discord.ui.TextInput(label="Boss (Sylph, Undine, Gnome, Salamander)")
    count_select = discord.ui.TextInput(label="จำนวนคนที่จะลบ", placeholder="เช่น 2")
    password = discord.ui.TextInput(label="Password")

    async def on_submit(self, interaction: discord.Interaction):
        if self.password.value != ADMIN_PASSWORD:
            await interaction.response.send_message("❌ Password ไม่ถูกต้อง", ephemeral=True)
            return

        t = self.time_select.value
        ch = self.ch_select.value
        boss = self.boss_select.value

        if t not in parties or ch not in parties[t] or boss not in parties[t][ch]:
            await interaction.response.send_message("⚠️ ข้อมูลเวลา/Channel/Boss ไม่ถูกต้อง", ephemeral=True)
            return

        try:
            count = int(self.count_select.value)
            if count <= 0:
                raise ValueError
        except ValueError:
            await interaction.response.send_message("⚠️ จำนวนคนต้องเป็นตัวเลข > 0", ephemeral=True)
            return

        members = parties[t][ch][boss]
        if not members:
            await interaction.response.send_message(f"⚠️ ไม่มีสมาชิกในปาร์ตี้ {t} {ch} {boss}", ephemeral=True)
            return

        # ลบสมาชิกตามจำนวนที่กำหนด
        deleted = []
        for _ in range(count):
            if members:
                uid = members.pop(0)
                deleted.append(uid)
                if uid in user_party:
                    del user_party[uid]

        names = [interaction.guild.get_member(uid).display_name if interaction.guild.get_member(uid) else str(uid) for uid in deleted]

        await interaction.response.send_message(
            f"🗑️ ลบสมาชิกจากปาร์ตี้ {t} {ch} {boss}: {', '.join(names)}", ephemeral=True
        )

# ------------------------------
# Slash Commands
@bot.tree.command(name="join", description="เข้าปาร์ตี้แบบ UI เลือก เวลา/CH/Boss/จำนวนคน")
async def join(interaction: discord.Interaction):
    view = JoinView(interaction.user)
    await interaction.response.send_message("เลือก เวลา / Channel / Boss / จำนวนคน แล้วกด ✅ ยืนยัน หรือ Leave", view=view, ephemeral=True)

@bot.tree.command(name="list", description="ดูรายชื่อปาร์ตี้")
@app_commands.describe(time="ใส่เวลา เช่น 16.00 (ไม่ใส่เพื่อดูทั้งหมด)")
async def list_party(interaction: discord.Interaction, time: str = None):
    guild = interaction.guild
    if time:
        if time not in parties:
            await interaction.response.send_message("⚠️ เวลาไม่ถูกต้อง", ephemeral=True)
            return
        embed = discord.Embed(title=f"📋 รายชื่อปาร์ตี้เวลา {time}", color=discord.Color.blue())
        for ch in parties[time]:
            desc = ""
            for boss, members in parties[time][ch].items():
                names = [guild.get_member(uid).display_name if guild.get_member(uid) else str(uid) for uid in members]
                desc += f"**{boss}** ({len(members)}/5): {', '.join(names) if names else '-'}\n"
            embed.add_field(name=ch, value=desc, inline=False)
    else:
        embed = discord.Embed(title="📋 รายชื่อทุกเวลา", color=discord.Color.blue())
        for t in parties:
            for ch in parties[t]:
                desc = ""
                for boss, members in parties[t][ch].items():
                    names = [guild.get_member(uid).display_name if guild.get_member(uid) else str(uid) for uid in members]
                    desc += f"**{boss}** ({len(members)}/5): {', '.join(names) if names else '-'}\n"
                embed.add_field(name=f"{t} {ch}", value=desc, inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="clear", description="ล้างข้อมูลปาร์ตี้ทั้งหมด")
async def clear(interaction: discord.Interaction):
    for t in parties:
        for ch in parties[t]:
            for boss in parties[t][ch]:
                parties[t][ch][boss] = []
    user_party.clear()
    await interaction.response.send_message("🧹 ล้างข้อมูลปาร์ตี้ทั้งหมดแล้ว", ephemeral=True)

@bot.tree.command(name="helpme", description="วิธีใช้งานบอทปาร์ตี้")
async def helpme(interaction: discord.Interaction):
    msg = (
        "📖 **วิธีใช้งานบอทปาร์ตี้**\n"
        "`/join` → เลือก เวลา / Channel / Boss / จำนวนคน\n"
        "`/list [เวลา]` → ดูรายชื่อปาร์ตี้\n"
        "`/clear` → ล้างข้อมูลปาร์ตี้ทั้งหมด\n"
        "`/delete` → ลบสมาชิกจากปาร์ตี้ (admin ต้องใส่ password)\n"
    )
    await interaction.response.send_message(msg, ephemeral=True)

@bot.tree.command(name="settime", description="ตั้งเวลาเริ่ม join (admin ต้องใส่ password)")
@app_commands.describe(time="เวลาใหม่ เช่น 12.00")
async def settime(interaction: discord.Interaction, time: str, password: str):
    global join_time
    if password != ADMIN_PASSWORD:
        await interaction.response.send_message("❌ Password ไม่ถูกต้อง", ephemeral=True)
        return
    join_time = time
    await interaction.response.send_message(f"⏰ ตั้งเวลาเริ่ม join เป็น {join_time}", ephemeral=True)

@bot.tree.command(name="delete", description="ลบสมาชิกจากปาร์ตี้ (admin ต้องใส่ password)")
async def delete(interaction: discord.Interaction):
    modal = DeleteModal()
    await interaction.response.send_modal(modal)

# ------------------------------
# Run bot
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Bot Online as {bot.user}")

bot.run(os.environ["DISCORD_BOT_TOKEN"])
