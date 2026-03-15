import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import os
from datetime import datetime, timedelta

DATA_FILE = "birthdays.json"

def load_data() -> dict:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_data(data: dict):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def setup_event_commands(tree, bot):

    @tree.command(name="event_setchannel", description="[ADMIN] დააყენე Forum Channel სადაც ივენთები გამოჩნდება")
    @app_commands.checks.has_permissions(administrator=True)
    async def event_setchannel(interaction: discord.Interaction):
        # შევამოწმოთ Forum Thread-ია
        if not isinstance(interaction.channel, discord.Thread):
            await interaction.response.send_message(
                "❌ Forum Channel-ის **Post-ში** გაუშვი ეს command!",
                ephemeral=True
            )
            return

        # Forum Channel-ის ID ვიღებთ Thread-იდან
        forum_channel = interaction.channel.parent
        if not isinstance(forum_channel, discord.ForumChannel):
            await interaction.response.send_message(
                "❌ ეს Forum Channel არ არის!",
                ephemeral=True
            )
            return

        data = load_data()
        guild_id = str(interaction.guild_id)

        if guild_id not in data:
            data[guild_id] = {}

        data[guild_id]["event_channel_id"] = forum_channel.id
        save_data(data)

        await interaction.response.send_message(
            f"✅ ივენთები **{forum_channel.name}** channel-ში გამოჩნდება!",
            ephemeral=True
        )

    @tree.command(name="create_event", description="შექმენი ივენთი Forum-ში + Poll")
    @app_commands.describe(
        name="ივენთის სახელი",
        date="თარიღი (DD/MM/YYYY)",
        time="საათი (HH:MM)",
        description="ივენთის აღწერა (სურვილისამებრ)"
    )
    @app_commands.checks.has_permissions(manage_events=True)
    async def create_event(
        interaction: discord.Interaction,
        name: str,
        date: str,
        time: str,
        description: str = ""
    ):
        await interaction.response.defer(ephemeral=True)

        # თარიღის პარსინგი
        try:
            event_dt = datetime.strptime(f"{date} {time}", "%d/%m/%Y %H:%M")
        except ValueError:
            await interaction.followup.send(
                "❌ **არასწორი თარიღი/საათი!**\nფორმატი: თარიღი `DD/MM/YYYY`, საათი `HH:MM`",
                ephemeral=True
            )
            return

        if event_dt < datetime.now():
            await interaction.followup.send(
                "❌ **გასული თარიღი!** მომავალი თარიღი შეიყვანე.",
                ephemeral=True
            )
            return

        # Forum Channel-ის პოვნა
        data = load_data()
        guild_id = str(interaction.guild_id)
        event_channel_id = data.get(guild_id, {}).get("event_channel_id")

        if not event_channel_id:
            await interaction.followup.send(
                "❌ Forum Channel არ არის დაყენებული! გაუშვი `/event_setchannel` Forum-ის ნებისმიერ Post-ში.",
                ephemeral=True
            )
            return

        forum_channel = interaction.guild.get_channel(event_channel_id)

        if not forum_channel or not isinstance(forum_channel, discord.ForumChannel):
            await interaction.followup.send(
                "❌ Forum Channel ვერ მოიძებნა! ხელახლა გაუშვი `/event_setchannel`.",
                ephemeral=True
            )
            return

        # @მოქეიფე როლის პოვნა
        mokeife_role = discord.utils.get(interaction.guild.roles, name="მოქეიფე")
        role_mention = mokeife_role.mention if mokeife_role else "@everyone"

        # Embed
        embed = discord.Embed(
            title=f"🎉 {name}",
            description=description if description else "",
            color=discord.Color.blurple()
        )
        embed.add_field(name="📅 თარიღი", value=date, inline=True)
        embed.add_field(name="⏰ საათი", value=time, inline=True)
        embed.add_field(name="👤 შექმნა", value=interaction.user.mention, inline=True)
        embed.set_footer(text="⏳ Poll 24 საათში დაიხურება")

        # Poll
        poll = discord.Poll(
            question=discord.PollMedia(text=f"მოხვალ?"),
            duration=timedelta(hours=24),
            multiple=False
        )
        poll.add_answer(text="მოვდივარ! 🟢", emoji="✅")
        poll.add_answer(text="არ მოვდივარ", emoji="❌")

        # Forum Post შექმნა
        try:
            thread, message = await forum_channel.create_thread(
                name=f"🎉 {name} — {date}",
                content=f"{role_mention} ახალი ივენთი! 🎊",
                embed=embed,
                poll=poll
            )
        except Exception as e:
            await interaction.followup.send(f"❌ Post შექმნა ვერ მოხერხდა: {e}", ephemeral=True)
            return

        await interaction.followup.send(
            f"✅ ივენთი შეიქმნა! {thread.jump_url}",
            ephemeral=True
        )
