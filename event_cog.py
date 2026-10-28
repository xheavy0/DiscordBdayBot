import discord
from discord.ext import tasks
from discord import app_commands
from datetime import datetime, timedelta
from storage import GEORGIA_TZ, now_ge, load_data, save_data

# შეხსენებები ივენთამდე: (გასაღები, რამდენით ადრე, ტექსტი)
EVENT_REMINDERS = [
    ("24h", timedelta(hours=24), "📅 ივენთი ხვალ არის!"),
    ("1h", timedelta(hours=1), "⏰ 1 საათში ვიწყებთ!"),
]
# დაწყებიდან რამდენ ხანში დაიხუროს პოსტი (დრო ფოტოების გასაზიარებლად)
EVENT_ARCHIVE_AFTER = timedelta(hours=12)
MAX_EVENTS_SHOWN = 10


# ============================
# ივენთების შენახვა
# ============================

def get_events(guild_id: int) -> list:
    return load_data().get(str(guild_id), {}).get("events", [])


def add_event(guild_id: int, event: dict):
    data = load_data()
    data.setdefault(str(guild_id), {}).setdefault("events", []).append(event)
    save_data(data)


def remove_event(guild_id: int, thread_id: int):
    data = load_data()
    guild_data = data.get(str(guild_id), {})
    guild_data["events"] = [e for e in guild_data.get("events", []) if e["thread_id"] != thread_id]
    save_data(data)


def mark_event_reminder(guild_id: int, thread_id: int, key: str):
    data = load_data()
    for event in data.get(str(guild_id), {}).get("events", []):
        if event["thread_id"] == thread_id and key not in event["reminders_sent"]:
            event["reminders_sent"].append(key)
    save_data(data)


def event_start(event: dict) -> datetime:
    return datetime.fromisoformat(event["start"])


def event_url(guild_id: int, thread_id: int) -> str:
    return f"https://discord.com/channels/{guild_id}/{thread_id}"


async def fetch_thread(guild: discord.Guild, thread_id: int):
    """აბრუნებს thread-ს; None — თუ წაშლილია. დაარქივებულ thread-საც პოულობს."""
    thread = guild.get_thread(thread_id)
    if thread:
        return thread
    try:
        return await guild.fetch_channel(thread_id)
    except discord.NotFound:
        return None


async def fetch_poll(thread, poll_message_id: int):
    try:
        message = await thread.fetch_message(poll_message_id)
        return message.poll
    except discord.HTTPException:
        return None


async def going_voters(thread, poll_message_id: int) -> list:
    poll = await fetch_poll(thread, poll_message_id)
    if not poll or not poll.answers:
        return []
    try:
        return [u async for u in poll.answers[0].voters() if not u.bot]
    except discord.HTTPException:
        return []


def time_left_text(delta: timedelta) -> str:
    minutes = int(delta.total_seconds() // 60)
    if minutes < 0:
        return "🔴 მიმდინარეობს"
    if minutes < 60:
        return f"{minutes} წუთში"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} საათში"
    days = hours // 24
    return "ხვალ" if days == 1 else f"{days} დღეში"


# ============================
# შეხსენება და დახურვა
# ============================

async def process_event(guild: discord.Guild, event: dict, now: datetime):
    start = event_start(event)
    thread_id = event["thread_id"]

    # 1) დასრულებული ივენთის პოსტს ვხურავთ
    if now >= start + EVENT_ARCHIVE_AFTER:
        thread = await fetch_thread(guild, thread_id)
        if thread:
            try:
                name = thread.name if thread.name.startswith("✅") else f"✅ {thread.name}"[:100]
                await thread.edit(name=name, locked=True, archived=True)
            except discord.HTTPException as e:
                print(f"⚠️ {guild.name}: ივენთის დახურვა ვერ მოხერხდა ({event['name']}): {e}")
        remove_event(guild.id, thread_id)
        return

    # 2) შეხსენებები დაწყებამდე
    for key, before, text in EVENT_REMINDERS:
        if key in event["reminders_sent"] or now < start - before or now >= start:
            continue

        thread = await fetch_thread(guild, thread_id)
        if thread is None:
            remove_event(guild.id, thread_id)  # პოსტი ხელით წაიშალა
            return

        voters = await going_voters(thread, event["poll_message_id"])
        mentions = " ".join(u.mention for u in voters)
        content = f"{text} **{event['name']}** — ⏰ {start.strftime('%H:%M')}"
        if mentions:
            content += f"\n{mentions}"
        try:
            await thread.send(content[:2000])
        except discord.HTTPException as e:
            print(f"⚠️ {guild.name}: ივენთის შეხსენება ვერ გაიგზავნა: {e}")
        mark_event_reminder(guild.id, thread_id, key)
        break  # ერთ ჯერზე ერთი შეხსენება


def setup_event_commands(tree, bot):

    @tasks.loop(minutes=1)
    async def event_task():
        now = now_ge()
        for guild in bot.guilds:
            for event in get_events(guild.id):
                try:
                    await process_event(guild, event, now)
                except Exception as e:
                    print(f"❌ Event task error ({guild.name}, {event.get('name')}): {e!r}")

    if not event_task.is_running():
        event_task.start()

    @tree.command(name="event_setchannel", description="[ADMIN] დააყენე Forum Channel სადაც ივენთები გამოჩნდება")
    @app_commands.checks.has_permissions(administrator=True)
    async def event_setchannel(interaction: discord.Interaction):
        if not isinstance(interaction.channel, discord.Thread):
            await interaction.response.send_message(
                "❌ Forum Channel-ის **Post-ში** გაუშვი ეს command!",
                ephemeral=True
            )
            return

        forum_channel = interaction.channel.parent
        if not isinstance(forum_channel, discord.ForumChannel):
            await interaction.response.send_message(
                "❌ ეს Forum Channel არ არის!",
                ephemeral=True
            )
            return

        data = load_data()
        data.setdefault(str(interaction.guild_id), {})["event_channel_id"] = forum_channel.id
        save_data(data)

        await interaction.response.send_message(
            f"✅ ივენთები **{forum_channel.name}** channel-ში გამოჩნდება!",
            ephemeral=True
        )

    @tree.command(name="create_event", description="შექმენი ივენთი Forum-ში + Poll")
    @app_commands.describe(
        name="ივენთის სახელი",
        date="თარიღი (DD/MM/YYYY)",
        time="საათი (HH:MM, საქართველოს დროით)",
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

        try:
            # დრო საქართველოს დროით აღიქმება, სერვერის დროის მიუხედავად
            event_dt = datetime.strptime(f"{date} {time}", "%d/%m/%Y %H:%M").replace(tzinfo=GEORGIA_TZ)
        except ValueError:
            await interaction.followup.send(
                "❌ **არასწორი თარიღი/საათი!**\nფორმატი: თარიღი `DD/MM/YYYY`, საათი `HH:MM`",
                ephemeral=True
            )
            return

        now = now_ge()
        if event_dt <= now:
            await interaction.followup.send(
                "❌ **გასული თარიღი!** მომავალი თარიღი შეიყვანე.",
                ephemeral=True
            )
            return

        event_channel_id = load_data().get(str(interaction.guild_id), {}).get("event_channel_id")

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

        mokeife_role = discord.utils.get(interaction.guild.roles, name="მოქეიფე")
        role_mention = mokeife_role.mention if mokeife_role else "@everyone"

        embed = discord.Embed(
            title=f"🎉 {name}",
            description=description if description else "",
            color=discord.Color.blurple()
        )
        embed.add_field(name="📅 თარიღი", value=date, inline=True)
        embed.add_field(name="⏰ საათი", value=time, inline=True)
        embed.add_field(name="👤 შექმნა", value=interaction.user.mention, inline=True)
        embed.set_footer(text="⏳ Poll 24 საათში დაიხურება · შეხსენება მოვა დაწყებამდე")

        poll = discord.Poll(
            question=discord.PollMedia(text="მოხვალ?"),
            duration=timedelta(hours=24),
            multiple=False
        )
        poll.add_answer(text="მოვდივარ! 🟢", emoji="✅")
        poll.add_answer(text="არ მოვდივარ", emoji="❌")

        try:
            thread, message = await forum_channel.create_thread(
                name=f"🎉 {name} — {date}"[:100],
                content=f"{role_mention} ახალი ივენთი! 🎊",
                embed=embed
            )
            poll_message = await thread.send(poll=poll)
        except Exception as e:
            await interaction.followup.send(f"❌ Post შექმნა ვერ მოხერხდა: {e}", ephemeral=True)
            return

        # შეხსენებები, რომელთა დროც უკვე გავიდა, აღარ გაიგზავნება
        add_event(interaction.guild_id, {
            "thread_id": thread.id,
            "poll_message_id": poll_message.id,
            "name": name,
            "start": event_dt.isoformat(),
            "created_by": interaction.user.id,
            "reminders_sent": [key for key, before, _ in EVENT_REMINDERS if event_dt - before <= now],
        })

        await interaction.followup.send(
            f"✅ ივენთი შეიქმნა! {thread.jump_url}",
            ephemeral=True
        )

    @tree.command(name="events", description="მომავალი ივენთების სია")
    async def events(interaction: discord.Interaction):
        await interaction.response.defer()
        now = now_ge()
        upcoming = sorted(get_events(interaction.guild_id), key=event_start)[:MAX_EVENTS_SHOWN]

        if not upcoming:
            await interaction.followup.send("📭 მომავალი ივენთები არ არის. შექმენი `/create_event`-ით!")
            return

        lines = []
        for event in upcoming:
            start = event_start(event)
            going = ""
            thread = await fetch_thread(interaction.guild, event["thread_id"])
            if thread:
                poll = await fetch_poll(thread, event["poll_message_id"])
                if poll and poll.answers:
                    going = f" · ✅ {poll.answers[0].vote_count} მოდის"
            lines.append(
                f"**[{event['name']}]({event_url(interaction.guild_id, event['thread_id'])})**\n"
                f"📅 {start.strftime('%d/%m/%Y')} ⏰ {start.strftime('%H:%M')} · {time_left_text(start - now)}{going}"
            )

        embed = discord.Embed(title="🎉 მომავალი ივენთები", description="\n\n".join(lines),
                              color=discord.Color.blurple())
        await interaction.followup.send(embed=embed)

    @tree.command(name="delete_event", description="[ADMIN] წაშალე ივენთი Forum-იდან")
    @app_commands.describe(event_name="ივენთის სახელი (ან მისი ნაწილი)")
    @app_commands.checks.has_permissions(administrator=True)
    async def delete_event(interaction: discord.Interaction, event_name: str):
        await interaction.response.defer(ephemeral=True)

        event_channel_id = load_data().get(str(interaction.guild_id), {}).get("event_channel_id")

        if not event_channel_id:
            await interaction.followup.send(
                "❌ Forum Channel არ არის დაყენებული!",
                ephemeral=True
            )
            return

        forum_channel = interaction.guild.get_channel(event_channel_id)

        if not forum_channel or not isinstance(forum_channel, discord.ForumChannel):
            await interaction.followup.send(
                "❌ Forum Channel ვერ მოიძებნა!",
                ephemeral=True
            )
            return

        # ვეძებთ thread-ს სახელით
        found_thread = None
        for thread in forum_channel.threads:
            if event_name.lower() in thread.name.lower():
                found_thread = thread
                break

        if not found_thread:
            # Archived threads-ებშიც ვეძებთ
            async for thread in forum_channel.archived_threads():
                if event_name.lower() in thread.name.lower():
                    found_thread = thread
                    break

        if not found_thread:
            await interaction.followup.send(
                f"❌ ივენთი **{event_name}** ვერ მოიძებნა!",
                ephemeral=True
            )
            return

        thread_name = found_thread.name
        await found_thread.delete()
        remove_event(interaction.guild_id, found_thread.id)

        await interaction.followup.send(
            f"🗑️ ივენთი **{thread_name}** წაიშალა!",
            ephemeral=True
        )
