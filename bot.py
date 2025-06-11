import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.messages = True

bot = commands.Bot(command_prefix="!", intents=intents)
bot_loop = None

# Runtime language state
current_lang = "ar"

# Messages in both languages
MESSAGES = {
    "ar": {
        "title": "🛒 طلب جديد من المتجر",
        "description": "✅ تم تقديم طلب جديد من <@{user_id}>",
        "items": "**🧾 محتويات السلة:**\n{items}",
        "total": "**💰 الإجمالي:** {total}$",
        "footer": "Qotb STORE | تمت العملية",
        "delivered": "✅ تم تسليم الطلب بنجاح!",
        "cancelled": "❌ تم إلغاء الطلب.",
        "buttons": ["تم التسليم ✅", "إلغاء ❌"],
    },
    "en": {
        "title": "🛒 New Store Order",
        "description": "✅ A new order has been placed by <@{user_id}>",
        "items": "**🧾 Cart Items:**\n{items}",
        "total": "**💰 Total:** {total}$",
        "footer": "Qotb STORE | Order Processed",
        "delivered": "✅ Order marked as delivered!",
        "cancelled": "❌ Order has been cancelled.",
        "buttons": ["Mark Delivered ✅", "Cancel ❌"],
    }
}

class OrderView(discord.ui.View):
    def __init__(self, channel, manager_id, lang):
        super().__init__(timeout=None)
        self.channel = channel
        self.manager_id = int(manager_id)
        self.lang = lang

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.manager_id:
            await interaction.response.send_message("🚫 You don't have permission.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="تم التسليم ✅", style=discord.ButtonStyle.success, custom_id="deliver")
    async def deliver(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(MESSAGES[self.lang]['delivered'], ephemeral=True)
        await self.channel.set_permissions(interaction.guild.default_role, read_messages=False)
        for overwrite in self.channel.overwrites:
            if isinstance(overwrite, discord.Member):
                await self.channel.set_permissions(overwrite, send_messages=False)

    @discord.ui.button(label="إلغاء ❌", style=discord.ButtonStyle.danger, custom_id="cancel")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(MESSAGES[self.lang]['cancelled'], ephemeral=True)
        await self.channel.delete()

@bot.event
async def on_ready():
    print(f"✅ Bot is ready as {bot.user}")

async def handle_checkout(username, user_id, cart, total):
    try:
        guild = discord.utils.get(bot.guilds, id=int(os.getenv("GUILD_ID")))
        if not guild:
            print("[ERROR] Guild not found")
            return

        category_name = f"✴|〔 {os.getenv('CATEGORY_NAME')} 〕|✴"
        category = discord.utils.get(guild.categories, name=category_name)
        if not category:
            category = await guild.create_category(category_name)

        buyer = guild.get_member(int(user_id))
        manager = guild.get_member(int(os.getenv("STORE_MANAGER_ID")))

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
        }
        if buyer:
            overwrites[buyer] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        if manager:
            overwrites[manager] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        channel = await guild.create_text_channel(
            name=f"order-{username}",
            category=category,
            overwrites=overwrites
        )

        # Localized messages
        msg = MESSAGES[current_lang]
        items_str = "\n".join([f"- {item}" for item in cart]) if cart else "لا توجد عناصر" if current_lang == "ar" else "No items"

        embed = discord.Embed(
            title=msg["title"],
            description=msg["description"].format(user_id=user_id),
            color=0x00B2FF,
            timestamp=datetime.utcnow()
        )
        embed.add_field(name=msg["items"].format(items=items_str), value="\u200b", inline=False)
        embed.add_field(name=msg["total"].format(total=total), value="\u200b", inline=False)
        embed.set_thumbnail(url="https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExZmIwZTE2dGRyYmNsZnRiaTYyMGRna2Z2ZTFzZmE0dDJhajF6cHF6ZCZlcD12MV9naWZzX3NlYXJjaCZjdD1n/3o7TKWGE1ZKs1mXFW4/giphy.gif")
        embed.set_footer(text=msg["footer"])

        view = OrderView(channel, manager.id, current_lang)
        await channel.send(content=f"<@{user_id}> <@{manager.id}>", embed=embed, view=view)

    except Exception as e:
        print(f"[ERROR] Exception in handle_checkout: {e}")

async def main():
    global bot_loop
    bot_loop = asyncio.get_running_loop()
    await bot.start(os.getenv("DISCORD_TOKEN"))
