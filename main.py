import os
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta, timezone
from keep_alive import keep_alive  # <-- เรียกจากไฟล์ keep_alive.py

# ------------------------------
# Discord Bot Setup
# ------------------------------
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ------------------------------
# โครงสร้างปาร์ตี้
# ------------------------------
parties = {
    t: {
        ch: {
            boss: []
            for boss in ["Sylph", "Undine", "Gnome", "Salamander"]
        }
        for ch in ["CH-1", "CH-2"]
    }
    for t in ["16.00", "18.00", "22.00"]
}

user_party = {}  # user_id -> (time, ch, boss, count)

join_start_time = "12.00"  # default join start time
admin_password = "osysadmin"


# ------------------------------
# UI Join View
# ------------------------------
class JoinView(discord.ui.View):

    def __init__(self, user):
        super().__init__(timeout=180)
        self.user = user
        self.selected_time = None
        self.selected_ch = None
        self.selected_boss = None
        self.selected_count = 1

        # Time select
        self.time_select = discord.ui.Select(
            placeholder="เลือกเวลา",
            options=[discord.SelectOption(label=t) for t in parties.keys()])
        self.time_select.callback = self.time_callback
        self.add_item(self.time_select)

        # Channel select
        self.ch_select = discord.ui.Select(
            placeholder="เลือก Channel",
            options=[
                discord.SelectOption(label="CH-1"),
                discord.SelectOption(label="CH-2")
            ])
        self.ch_select.callback = self.ch_callback
        self.add_item(self.ch_select)

        # Boss select
        self.boss_select = discord.ui.Select(
            placeholder="เลือก Boss",
            options=[
                discord.SelectOption(label=boss)
                for boss in ["Sylph", "Undine", "Gnome", "Salamander"]
            ])
        self.boss_select.callback = self.boss_callback
        self.add_item(self.boss_select)

        # Count select
        self.count_select = discord.ui.Select(
            placeholder="เลือกจำนวนคน (1–5)",
            options=[discord.SelectOption(label=str(i)) for i in range(1, 6)])
        self.count_select.callback = self.count_callback
        self.add_item(self.count_select)

        # Confirm button
        self.confirm_button = discord.ui.Button(
            label="✅ ยืนยันเข้าปาร์ตี้", style=discord.ButtonStyle.green)
        self.confirm_button.callback = self.confirm_callback
        self.add_item(self.confirm_button)

        # Leave button
        self.leave_button = discord.ui.Button(label="↩️ ออกจากปาร์ตี้",
                                              style=discord.ButtonStyle.red)
        self.leave_button.callback = self.leave_callback
        self.add_item(self.leave_button)

    async def interaction_check(self,
                                interaction: discord.Interaction) -> bool:
        if interaction.user != self.user:
            await interaction.response.send_message(
                "❌ คุณไม่สามารถกด UI ของคนอื่นได้", ephemeral=True)
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
        now = datetime.now(timezone(timedelta(hours=7)))  # UTC+7
        join_hour, join_minute = map(int, join_start_time.split("."))
        join_dt = now.replace(hour=join_hour,
                              minute=join_minute,
                              second=0,
                              microsecond=0)
        if now < join_dt:
            await interaction.response.send_message(
                f"⏳ ยังไม่ถึงเวลาที่กำหนด โปรดรอ {join_start_time} เป็นต้นไป",
                ephemeral=True)
            return

        if not (self.selected_time and self.selected_ch and self.selected_boss
                and self.selected_count):
            await interaction.response.send_message(
                "⚠️ ต้องเลือกครบ เวลา/CH/Boss/จำนวนคน ก่อน", ephemeral=True)
            return

        uid = interaction.user.id
        if uid in user_party:
            await interaction.response.send_message(
                "⚠️ คุณอยู่ปาร์ตี้อื่นอยู่แล้ว ใช้ Leave ก่อน", ephemeral=True)
            return

        members = parties[self.selected_time][self.selected_ch][
            self.selected_boss]
        remaining_slots = 5 - len(members)

        if remaining_slots <= 0:
            # แสดงบอสอื่นที่ยังเหลือ slot
            available_bosses = []
            for boss, boss_members in parties[self.selected_time][self.selected_ch].items():
                slots_left = 5 - len(boss_members)
                if slots_left > 0:
                    available_bosses.append(f"{boss}: {slots_left} ที่")
            extra_msg = ""
            if available_bosses:
                extra_msg = "\n🎯 บอสอื่นที่ยังมีที่ว่าง:\n" + "\n".join(available_bosses)
            await interaction.response.send_message(
                f"❌ ปาร์ตี้เต็มแล้ว{extra_msg}",
                ephemeral=True)
            return

        if self.selected_count > remaining_slots:
            await interaction.response.send_message(
                f"⚠️ ไม่สามารถเข้าร่วมปาร์ตี้ได้เนื่องจาก ปาร์ตี้เหลือ {remaining_slots} ที่ แต่คุณเลือก {self.selected_count} คน กรุณาลงใหม่",
                ephemeral=True)
            return

        members.extend([uid] * self.selected_count)
        user_party[uid] = (self.selected_time, self.selected_ch,
                           self.selected_boss, self.selected_count)

        await interaction.response.send_message(
            f"✅ {interaction.user.display_name} เข้าปาร์ตี้ {self.selected_time} {self.selected_ch} {self.selected_boss} "
            f"({len(members)}/5 คน, ลงแทน {self.selected_count-1} คน)",
            ephemeral=True)

    async def leave_callback(self, interaction: discord.Interaction):
        uid = self.user.id
        if uid not in user_party:
            await interaction.response.send_message(
                "⚠️ คุณไม่ได้อยู่ปาร์ตี้ใดๆ", ephemeral=True)
            return

        time, ch, boss, count = user_party[uid]
        members = parties[time][ch][boss]
        for _ in range(count):
            if uid in members:
                members.remove(uid)

        del user_party[uid]
        await interaction.response.send_message(
            f"↩️ {self.user.display_name} ออกจากปาร์ตี้ {time} {ch} {boss} (คืน {count} ที่นั่ง)",
            ephemeral=True)


# ------------------------------
# UI Delete View (Admin)
# ------------------------------
class DeleteView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=180)
        self.time_select = discord.ui.Select(
            placeholder="เลือกเวลา",
            options=[discord.SelectOption(label=t) for t in parties.keys()])
        self.time_select.callback = self.time_callback
        self.add_item(self.time_select)

        self.ch_select = discord.ui.Select(
            placeholder="เลือก Channel",
            options=[
                discord.SelectOption(label="CH-1"),
                discord.SelectOption(label="CH-2")
            ])
        self.ch_select.callback = self.ch_callback
        self.add_item(self.ch_select)

        self.boss_select = discord.ui.Select(
            placeholder="เลือก Boss",
            options=[
                discord.SelectOption(label=boss)
                for boss in ["Sylph", "Undine", "Gnome", "Salamander"]
            ])
        self.boss_select.callback = self.boss_callback
        self.add_item(self.boss_select)

        self.confirm_button = discord.ui.Button(label="✅ ลบคนออกทั้งหมด",
                                                style=discord.ButtonStyle.red)
        self.confirm_button.callback = self.confirm_callback
        self.add_item(self.confirm_button)

        self.selected_time = None
        self.selected_ch = None
        self.selected_boss = None

    async def time_callback(self, interaction: discord.Interaction):
        self.selected_time = self.time_select.values[0]
        await interaction.response.defer(ephemeral=True)

    async def ch_callback(self, interaction: discord.Interaction):
        self.selected_ch = self.ch_select.values[0]
        await interaction.response.defer(ephemeral=True)

    async def boss_callback(self, interaction: discord.Interaction):
        self.selected_boss = self.boss_select.values[0]
        await interaction.response.defer(ephemeral=True)

    async def confirm_callback(self, interaction: discord.Interaction):
        if not (self.selected_time and self.selected_ch
                and self.selected_boss):
            await interaction.response.send_message(
                "⚠️ ต้องเลือกครบ เวลา/CH/Boss ก่อน", ephemeral=True)
            return

        members = parties[self.selected_time][self.selected_ch][
            self.selected_boss]
        for uid in members[:]:
            if uid in user_party:
                del user_party[uid]
        parties[self.selected_time][self.selected_ch][self.selected_boss] = []

        await interaction.response.send_message(
            f"🧹 ลบผู้เล่นทั้งหมดใน {self.selected_time} {self.selected_ch} {self.selected_boss} แล้ว",
            ephemeral=True)


# ------------------------------
# Slash Commands
# ------------------------------
@bot.tree.command(name="mhjoin",
                  description="เข้าปาร์ตี้แบบ UI เลือก เวลา/CH/Boss/จำนวนคน")
async def mhjoin(interaction: discord.Interaction):
    view = JoinView(interaction.user)
    await interaction.response.send_message(
        "เลือก เวลา / Channel / Boss / จำนวนคน แล้วกด ✅ ยืนยัน หรือ Leave",
        view=view,
        ephemeral=True)


@bot.tree.command(name="list", description="ดูรายชื่อปาร์ตี้")
@app_commands.describe(time="ใส่เวลา เช่น 16.00 (ไม่ใส่เพื่อดูทั้งหมด)")
async def list_party(interaction: discord.Interaction, time: str = None):
    guild = interaction.guild

    member_numbers = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]

    def format_members_vertical_numbered(members):
        names = [
            guild.get_member(uid).display_name
            if guild.get_member(uid) else str(uid) for uid in members
        ]
        while len(names) < 5:
            names.append("-")
        return "\n".join(f"{member_numbers[i]} {name[:12]}"
                         for i, name in enumerate(names[:5]))

    boss_icons = {"Sylph": "🐉", "Undine": "💧", "Gnome": "🌱", "Salamander": "🔥"}

    times_to_show = [time] if time and time in parties else parties.keys()
    embed = discord.Embed(title="📋 รายชื่อปาร์ตี้",
                          color=0x9400D3)  # สีหลักของ Embed

    for t in times_to_show:
        lines = [f"⏰ เวลา {t}"]
        for ch in parties[t]:
            lines.append(f"__**{ch}**__")
            for boss, members in parties[t][ch].items():
                icon = boss_icons.get(boss, "🛡️")
                lines.append(f"{icon} **{boss}**")
                lines.append(format_members_vertical_numbered(members))
        embed.add_field(name="\u200b", value="\n".join(lines), inline=False)

    embed.set_footer(text="Party System | By XeZer 😎")
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="clear", description="ล้างข้อมูลปาร์ตี้ทั้งหมด")
async def clear(interaction: discord.Interaction):
    for t in parties:
        for ch in parties[t]:
            for boss in parties[t][ch]:
                parties[t][ch][boss] = []
    user_party.clear()
    await interaction.response.send_message("🧹 ล้างข้อมูลปาร์ตี้ทั้งหมดแล้ว",
                                            ephemeral=True)


@bot.tree.command(name="helpme", description="วิธีใช้งานบอทปาร์ตี้")
async def helpme(interaction: discord.Interaction):
    msg = (
        "📖 **วิธีใช้งานบอทปาร์ตี้**\n"
        "`/mhjoin` → เลือก เวลา / Channel / Boss / จำนวนคน\n"
        "`/list [เวลา]` → ดูรายชื่อปาร์ตี้ (ใส่เวลา เช่น 16.00 หรือไม่ใส่เพื่อดูทั้งหมด)\n"
        "`/clear` → ล้างข้อมูลปาร์ตี้ทั้งหมด\n"
        "`/settime time:<เวลา> password:<รหัส>` → ตั้งเวลาเริ่ม join (default 12.00)\n"
        "`/delete password:<รหัส>` → ลบคนในปาร์ตี้ด้วยปุ่มเลือก เวลา/CH/Boss")
    await interaction.response.send_message(msg, ephemeral=True)


@bot.tree.command(name="settime", description="ตั้งเวลาเริ่ม join")
@app_commands.describe(time="ใส่เวลา เช่น 12.00", password="รหัส admin")
async def settime(interaction: discord.Interaction, time: str, password: str):
    global join_start_time
    if password != admin_password:
        await interaction.response.send_message("❌ รหัสไม่ถูกต้อง",
                                                ephemeral=True)
        return
    join_start_time = time
    await interaction.response.send_message(
        f"⏰ ตั้งเวลาเริ่ม join เป็น {time} เรียบร้อย", ephemeral=True)


@bot.tree.command(name="delete",
                  description="ลบคนในปาร์ตี้ด้วยปุ่มเลือก (Admin)")
@app_commands.describe(password="รหัส admin")
async def delete(interaction: discord.Interaction, password: str):
    if password != admin_password:
        await interaction.response.send_message("❌ รหัสไม่ถูกต้อง",
                                                ephemeral=True)
        return
    view = DeleteView()
    await interaction.response.send_message(
        "เลือก เวลา / Channel / Boss แล้วกด ✅ เพื่อลบผู้เล่นทั้งหมด",
        view=view,
        ephemeral=True)


# ------------------------------
# Run bot
# ------------------------------
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Bot Online as {bot.user}")


# เรียก keep_alive ก่อนรันบอท
keep_alive()
bot.run(os.environ["DISCORD_BOT_TOKEN"])
