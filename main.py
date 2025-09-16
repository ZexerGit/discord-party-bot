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
            # ✅ หา slot ว่างจากทุก CH ของเวลาเดียวกัน
            available = []
            for ch, bosses in parties[self.selected_time].items():
                for boss, boss_members in bosses.items():
                    slots_left = 5 - len(boss_members)
                    if slots_left > 0:
                        available.append(f"{ch} - {boss}: {slots_left} ที่")

            extra_msg = ""
            if available:
                extra_msg = "\n🎯 ที่ว่างในเวลาเดียวกัน:\n" + "\n".join(
                    available)

            await interaction.response.send_message(
                f"❌ ปาร์ตี้เต็มแล้ว{extra_msg}", ephemeral=True)
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

    boss_icons = {
        "Sylph": "<:wind:1417135422269689928>",
        "Undine": "<:water:1417135449172082698>",
        "Gnome": "<:earth:1417135502867300372>",
        "Salamander": "<:fire:1417135359799726160>"
    }

    times_to_show = [time] if time and time in parties else parties.keys()
    embeds = []

    for t in times_to_show:
        embed = discord.Embed(title=f"📋 เวลา {t}", color=0x9400D3)

        for ch, bosses in parties[t].items():
            value_lines = []
            for boss_group in [["Sylph", "Undine"], ["Gnome", "Salamander"]]:
                for boss in boss_group:
                    if boss in bosses:
                        value_lines.append(
                            f"{boss_icons[boss]} {boss}\n{format_members_vertical_numbered(bosses[boss])}"
                        )
            embed.add_field(name=f"{ch}",
                            value="\n\n".join(value_lines),
                            inline=True)

        embed.set_footer(text="Party System | By XeZer 😎")
        embeds.append(embed)

    await interaction.response.send_message(embeds=embeds, ephemeral=True)


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


# ------------------------------
# Reaction Roles with Emoji Buttons + Modal + Admin Approval
# ------------------------------
reaction_roles = {
    "<:ln2:1406935643665207337>": {
        "role_name": "ln2",
        "color": 0x1abc9c,
        "desc": "Game Lineage2M"
    },
    "<:roo:1406935556956356739>": {
        "role_name": "roo",
        "color": 0xe67e22,
        "desc": "Game Ragnarok Origin"
    },
    "<:rom:1406935703685824611>": {
        "role_name": "rom",
        "color": 0x9b59b6,
        "desc": "Game Ragnarok Eternal Love"
    }
}
ADMIN_CHANNEL_ID = 1417463299423076373  # Admin approval channel


@bot.tree.command(name="setup_roles",
                  description="Request roles with admin approval")
async def setup_roles(interaction: discord.Interaction):
    """Post main message with emoji buttons for users to request roles."""

    class RoleView(discord.ui.View):

        def __init__(self):
            super().__init__(timeout=None)
            for emoji_str, info in reaction_roles.items():
                emoji_obj = discord.PartialEmoji.from_str(emoji_str)
                button = discord.ui.Button(style=discord.ButtonStyle.secondary,
                                           emoji=emoji_obj)
                button.callback = self.make_callback(info)
                self.add_item(button)

        def make_callback(self, info):
            role_name = info["role_name"]
            role_color = info["color"]

            async def callback(interact: discord.Interaction):

                class InfoModal(discord.ui.Modal,
                                title=f"{role_name} Request"):
                    character_name = discord.ui.TextInput(
                        label="Character Name",
                        placeholder="Enter your character name",
                        max_length=50)
                    contact = discord.ui.TextInput(
                        label="Contract / Referral",
                        placeholder="Who referred you or contract info",
                        max_length=50)

                    async def on_submit(
                            self, modal_interaction: discord.Interaction):
                        member = modal_interaction.user
                        guild = modal_interaction.guild

                        # Respond to user with ephemeral Embed
                        await modal_interaction.response.send_message(
                            embed=discord.Embed(
                                title="✅ Role Request Submitted!",
                                description=(
                                    f"You have requested the role: **{role_name}**\n"
                                    f"Character Name: `{self.character_name.value}`\n"
                                    f"Contract / Referral: `{self.contact.value}`\n\n"
                                    "Please wait for admin approval."
                                ),
                                color=role_color),
                            ephemeral=True)

                        # Send to admin channel with Confirm/Reject buttons
                        admin_channel = guild.get_channel(ADMIN_CHANNEL_ID)
                        if not admin_channel:
                            return

                        class AdminView(discord.ui.View):

                            def __init__(self):
                                super().__init__(timeout=None)

                                confirm_button = discord.ui.Button(
                                    label="✅ Confirm",
                                    style=discord.ButtonStyle.green)
                                reject_button = discord.ui.Button(
                                    label="❌ Reject",
                                    style=discord.ButtonStyle.red)

                                async def confirm_callback(
                                        btn_interact: discord.Interaction):
                                    role_obj = discord.utils.get(
                                        guild.roles, name=role_name)
                                    if role_obj and guild.me.top_role > role_obj:
                                        await member.add_roles(role_obj)
                                        await btn_interact.response.send_message(
                                            f"✅ {member.display_name} has been granted the role **{role_name}**!",
                                            ephemeral=True)
                                        await btn_interact.message.edit(view=None)
                                        try:
                                            await member.send(
                                                f"🎉 Your role request **{role_name}** has been approved by admin!"
                                            )
                                        except:
                                            pass
                                    else:
                                        await btn_interact.response.send_message(
                                            "❌ Bot does not have permission to add this role",
                                            ephemeral=True)

                                async def reject_callback(
                                        btn_interact: discord.Interaction):
                                    await btn_interact.response.send_message(
                                        f"❌ Role request of {member.display_name} has been rejected",
                                        ephemeral=True)
                                    await btn_interact.message.edit(view=None)
                                    try:
                                        await member.send(
                                            f"❌ Your role request **{role_name}** was rejected by admin."
                                        )
                                    except:
                                        pass

                                confirm_button.callback = confirm_callback
                                reject_button.callback = reject_callback
                                self.add_item(confirm_button)
                                self.add_item(reject_button)

                        admin_embed = discord.Embed(
                            title=f"📩 Role Request: {role_name}",
                            color=role_color)
                        admin_embed.add_field(name="User",
                                              value=member.mention,
                                              inline=False)
                        admin_embed.add_field(name="Character Name",
                                              value=self.character_name.value,
                                              inline=False)
                        admin_embed.add_field(name="Contract / Referral",
                                              value=self.contact.value,
                                              inline=False)
                        admin_embed.set_footer(text="Admin Panel | Approve or Reject")
                        await admin_channel.send(embed=admin_embed,
                                                 view=AdminView())

                await interact.response.send_modal(InfoModal())

            return callback

    # Main embed message
    main_embed = discord.Embed(
        title="👋 Request Your Role Here!",
        description="Click the emoji buttons below to request your game role:\n\n",
        color=0x7289DA)

    for emoji_str, info in reaction_roles.items():
        main_embed.add_field(name=f"{emoji_str} {info['role_name'].upper()}",
                             value=info['desc'],
                             inline=False)

    main_embed.set_footer(
        text="Role Request System | Fill all required information")

    view = RoleView()
    await interaction.response.send_message(embed=main_embed,
                                            view=view,
                                            ephemeral=False)



# เรียก keep_alive ก่อนรันบอท
keep_alive()
bot.run(os.environ["DISCORD_BOT_TOKEN"])
