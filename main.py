import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

times = ["16.00", "18.00", "22.00"]
channels = ["CH-1", "CH-2"]
bosses = ["Sylph", "Undine", "Gnome", "Salamander"]

parties = {t: {c: {b: [] for b in bosses} for c in channels} for t in times}
user_party = {}

class TimeSelect(discord.ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label=t, description=f"เลือกเวลา {t}") for t in times]
        super().__init__(placeholder="เลือกเวลา", options=options)

    async def callback(self, interaction: discord.Interaction):
        time = self.values[0]
        await interaction.response.edit_message(content=f"⏰ คุณเลือกเวลา {time}\nเลือก Channel ต่อไป:", view=ChannelView(time))

class ChannelSelect(discord.ui.Select):
    def __init__(self, time):
        self.time = time
        options = [discord.SelectOption(label=c) for c in channels]
        super().__init__(placeholder="เลือก Channel", options=options)

    async def callback(self, interaction: discord.Interaction):
        ch = self.values[0]
        await interaction.response.edit_message(content=f"🛡️ คุณเลือก {self.time} {ch}\nเลือกบอสต่อไป:", view=BossView(self.time, ch))

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
            await interaction.response.send_message(f"⚠️ {uname} คุณ join ไปแล้ว ต้อง !leave ก่อน", ephemeral=True)
            return

        if len(parties[self.time][self.ch][boss]) >= 5:
            await interaction.response.send_message(f"❌ ปาร์ตี้ {self.time} {self.ch} {boss} เต็มแล้ว", ephemeral=True)
            return

        parties[self.time][self.ch][boss].append(uid)
        user_party[uid] = (self.time, self.ch, boss)
        await interaction.response.send_message(f"✅ {uname} เข้าปาร์ตี้ {self.time} {self.ch} {boss}", ephemeral=False)

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

@bot.command()
async def join(ctx):
    await ctx.send("โปรดเลือกเวลา:", view=TimeView())

bot.run("YOUR_TOKEN")
