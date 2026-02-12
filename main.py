import discord
from discord.ext import commands
from discord.ui import View, Button, Select
from io import BytesIO
from threading import Thread
from flask import Flask
import os

# =========================
# CONFIG
# =========================
TOKEN = os.getenv("MTQ2ODY1NTQ1OTEzNjE4MDM5Ng.G5C0gR.4ucDISc4FLf9yTMfU3lvIOluRuwAyiQdYPlgh8")  # Token jetzt aus Environment Variable
PANEL_CHANNEL_ID = 1469076818559762543
LOG_CHANNEL_ID = 1468654128074068206
CREW_COLOR = 0x0d1b2a
CREW_LOGO = "https://cdn.discordapp.com/attachments/1468654128074068206/1471579091575504956/Featured-Image-Straw-Hat-Pirates-Cropped.jpg"

# =========================
# INTENTS & BOT
# =========================
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
ticket_counter = 0

# =========================
# DUMMY WEB-SERVER für Render Port
# =========================
PORT = int(os.environ.get("PORT", 10000))
app = Flask("")

@app.route("/")
def home():
    return "Bot läuft ✅"

def run_web():
    app.run(host="0.0.0.0", port=PORT)

Thread(target=run_web).start()

# =========================
# HTML TRANSCRIPT FUNCTION
# =========================
async def create_transcript(channel):
    messages_html = ""
    async for msg in channel.history(limit=None, oldest_first=True):
        timestamp = msg.created_at.strftime("%d.%m.%Y %H:%M")
        content = msg.content.replace("<", "&lt;").replace(">", "&gt;")
        messages_html += f"""
        <div class="message">
            <img src="{msg.author.display_avatar.url}" class="avatar">
            <div class="msgcontent">
                <div class="author">{msg.author}</div>
                <div class="time">{timestamp}</div>
                <div class="content">{content}</div>
            </div>
        </div>
        """
    html_content = f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <title>{channel.name} Transcript</title>
        <style>
            body {{
                background-color: #0d1b2a;
                color: white;
                font-family: Arial;
                padding: 20px;
            }}
            .message {{
                display: flex;
                background-color: #1b263b;
                padding: 10px;
                margin-bottom: 10px;
                border-radius: 10px;
            }}
            .avatar {{
                width: 40px;
                height: 40px;
                border-radius: 50%;
                margin-right: 10px;
            }}
            .author {{
                font-weight: bold;
                color: #00b4d8;
            }}
            .time {{
                font-size: 12px;
                color: #adb5bd;
            }}
            .content {{
                margin-top: 5px;
            }}
        </style>
    </head>
    <body>
        <h2>⚓ Crew Ticket Transcript</h2>
        <h3>Kanal: {channel.name}</h3>
        {messages_html}
    </body>
    </html>
    """
    return discord.File(
        BytesIO(html_content.encode("utf-8")),
        filename=f"{channel.name}-transcript.html"
    )

# =========================
# CLOSE / DELETE VIEW
# =========================
class CloseTicketView(View):
    def __init__(self, creator):
        super().__init__(timeout=None)
        self.creator = creator

    @discord.ui.button(label="🔒 Schließen", style=discord.ButtonStyle.red, custom_id="ticket_close")
    async def close_ticket(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("🔒 Ticket wurde geschlossen.", ephemeral=True)

    @discord.ui.button(label="🗑️ Löschen", style=discord.ButtonStyle.grey, custom_id="ticket_delete")
    async def delete_ticket(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        channel = interaction.channel
        transcript = await create_transcript(channel)
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        embed = discord.Embed(
            title="📁 Ticket gelöscht",
            description=f"Ticket von {self.creator.mention}",
            color=CREW_COLOR
        )
        embed.set_thumbnail(url=CREW_LOGO)
        embed.set_footer(text="⚓ Crew Support Logs")
        if log_channel:
            await log_channel.send(embed=embed, file=transcript)
        await channel.delete()

# =========================
# TICKET SELECT
# =========================
class TicketTypeSelect(Select):
    def __init__(self, user):
        options = [
            discord.SelectOption(label="Tryouts"),
            discord.SelectOption(label="War"),
            discord.SelectOption(label="Problem"),
            discord.SelectOption(label="Rank")
        ]
        super().__init__(
            placeholder="Wähle deinen Ticket-Typ",
            options=options,
            custom_id="ticket_type_select"
        )
        self.user = user

    async def callback(self, interaction: discord.Interaction):
        global ticket_counter
        await interaction.response.defer(ephemeral=True)
        ticket_counter += 1
        ticket_number = f"{ticket_counter:04d}"
        ticket_type = self.values[0]
        guild = interaction.guild
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }
        channel = await guild.create_text_channel(
            name=f"ticket-{ticket_type.lower()}-{ticket_number}",
            overwrites=overwrites
        )
        embed = discord.Embed(
            title=f"⚓ CREW SUPPORT TICKET #{ticket_number}",
            description=(
                f"**Mitglied:** {interaction.user.mention}\n"
                f"**Typ:** {ticket_type}\n\n"
                f"Unser Crew Team kümmert sich gleich darum."
            ),
            color=CREW_COLOR
        )
        embed.set_thumbnail(url=CREW_LOGO)
        embed.set_footer(text="⚓ Crew Support System")
        await channel.send(embed=embed, view=CloseTicketView(interaction.user))
        await interaction.followup.send(
            f"✅ Dein Ticket wurde erstellt: {channel.mention}",
            ephemeral=True
        )

class TicketTypeView(View):
    def __init__(self, user):
        super().__init__(timeout=None)
        self.add_item(TicketTypeSelect(user))

class TicketPanelView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="⚓ Crew Ticket öffnen",
        style=discord.ButtonStyle.green,
        custom_id="crew_ticket_open"
    )
    async def open_ticket(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message(
            "Wähle deinen Ticket-Typ:",
            view=TicketTypeView(interaction.user),
            ephemeral=True
        )

# =========================
# COMMAND PANEL
# =========================
@bot.command()
async def sendpanel(ctx):
    embed = discord.Embed(
        title="⚓ CREW SUPPORT PANEL",
        description="Drücke den Button um ein Ticket zu eröffnen.",
        color=CREW_COLOR
    )
    embed.set_thumbnail(url=CREW_LOGO)
    embed.set_footer(text="⚓ Crew Support System")
    await ctx.send(embed=embed, view=TicketPanelView())

# =========================
# ON READY
# =========================
@bot.event
async def on_ready():
    print(f"🤖 Online als {bot.user}")
    bot.add_view(TicketPanelView())
    bot.add_view(CloseTicketView(None))
    print("✅ Crew Ticket System mit HTML Transcript bereit.")

# =========================
# BOT START
# =========================
bot.run(TOKEN) 
