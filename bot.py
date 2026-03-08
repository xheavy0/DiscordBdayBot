import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import os
from datetime import datetime
import asyncio

# ============================
# ᲙᲝᲜᲤᲘᲒᲣᲠᲐᲪᲘᲐ
# ============================
BOT_TOKEN = "შენი თოკენი" #შეცვალე შენი ტოკენით
BIRTHDAY_CHANNEL_ID = 1480188020123766794  # default channel, /birthday_setchannel-ით შეცვლა შეიძლება
CHECK_HOUR = 9
CHECK_MINUTE = 0

DATA_FILE = "birthdays.json"

# ============================
# ᲑᲝᲢᲘᲡ ინიციალიზაცია
# ============================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree


# ============================
# მონაცემების მართვა
# ============================
def load_birthdays() -> dict:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_birthdays(data: dict):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ============================
# SLASH COMMANDS
# ============================

@tree.command(name="birthday_add", description="დაამატე შენი დაბადების დღე")
@app_commands.describe(
    day="დღე (1-31)",
    month="თვე (1-12)",
    year="წელი (სურვილისამებრ, მაგ: 1995)"
)
async def birthday_add(interaction: discord.Interaction, day: int, month: int, year: int = None):
    try:
        if year:
            test_date = datetime(year, month, day)
        else:
            test_date = datetime(2000, month, day)
    except ValueError:
        await interaction.response.send_message(
            "❌ **არასწორი თარიღი!** გთხოვ შეამოწმე დღე და თვე.",
            ephemeral=True
        )
        return

    data = load_birthdays()
    guild_id = str(interaction.guild_id)
    user_id = str(interaction.user.id)

    if guild_id not in data:
        data[guild_id] = {}

    data[guild_id][user_id] = {
        "day": day,
        "month": month,
        "year": year,
        "username": interaction.user.display_name
    }

    save_birthdays(data)

    month_names = ["იანვარი", "თებერვალი", "მარტი", "აპრილი", "მაისი", "ივნისი",
                   "ივლისი", "აგვისტო", "სექტემბერი", "ოქტომბერი", "ნოემბერი", "დეკემბერი"]

    year_str = f" {year}" if year else ""
    await interaction.response.send_message(
        f"✅ **დაბადების დღე დამახსოვრებულია!**\n"
        f"📅 {day} {month_names[month-1]}{year_str}\n"
        f"🎂 გილოცავ დაბადების დღეს! 🎉",
        ephemeral=True
    )


@tree.command(name="birthday_remove", description="წაშალე შენი დაბადების დღე")
async def birthday_remove(interaction: discord.Interaction):
    data = load_birthdays()
    guild_id = str(interaction.guild_id)
    user_id = str(interaction.user.id)

    if guild_id in data and user_id in data[guild_id]:
        del data[guild_id][user_id]
        save_birthdays(data)
        await interaction.response.send_message("🗑️ შენი დაბადების დღე წაიშალა.", ephemeral=True)
    else:
        await interaction.response.send_message("❌ შენი დაბადების დღე არარის შენახული.", ephemeral=True)


@tree.command(name="birthday_list", description="ნახე ყველას დაბადების დღე სერვერზე")
async def birthday_list(interaction: discord.Interaction):
    data = load_birthdays()
    guild_id = str(interaction.guild_id)

    if guild_id not in data or not data[guild_id]:
        await interaction.response.send_message("📭 ჯერ არავის დაუმატებია დაბადების დღე.", ephemeral=False)
        return

    month_names = ["იანვარი", "თებერვალი", "მარტი", "აპრილი", "მაისი", "ივნისი",
                   "ივლისი", "აგვისტო", "სექტემბერი", "ოქტომბერი", "ნოემბერი", "დეკემბერი"]

    sorted_birthdays = sorted(
        [(k, v) for k, v in data[guild_id].items() if k != "channel_id"],
        key=lambda x: (x[1]["month"], x[1]["day"])
    )

    embed = discord.Embed(
        title="🎂 სერვერის დაბადების დღეები",
        color=discord.Color.pink()
    )

    today = datetime.now()
    lines = []

    for user_id, bday in sorted_birthdays:
        member = interaction.guild.get_member(int(user_id))
        name = member.display_name if member else bday.get("username", f"User {user_id}")
        year_str = f" {bday['year']}" if bday.get("year") else ""

        is_today = bday["day"] == today.day and bday["month"] == today.month
        birthday_emoji = "🎉 **დღეს!**" if is_today else ""

        lines.append(
            f"**{name}** — {bday['day']} {month_names[bday['month']-1]}{year_str} {birthday_emoji}"
        )

    embed.description = "\n".join(lines) if lines else "სია ცარიელია"
    embed.set_footer(text=f"სულ: {len(sorted_birthdays)} ადამიანი")

    await interaction.response.send_message(embed=embed)


@tree.command(name="birthday_check", description="შეამოწმე ვის აქვს დაბადების დღე")
async def birthday_check(interaction: discord.Interaction):
    await interaction.response.defer()
    result = await check_and_announce(interaction.guild, force=True)
    if not result:
        await interaction.followup.send("😔 დღეს არავის აქვს დაბადების დღე.")


@tree.command(name="birthday_admin_add", description="[ADMIN] სხვა მომხმარებლის დაბადების დღის დამატება")
@app_commands.describe(member="მომხმარებელი", day="დღე", month="თვე", year="წელი (სურვილისამებრ)")
@app_commands.checks.has_permissions(administrator=True)
async def birthday_admin_add(interaction: discord.Interaction, member: discord.Member, day: int, month: int, year: int = None):
    try:
        if year:
            datetime(year, month, day)
        else:
            datetime(2000, month, day)
    except ValueError:
        await interaction.response.send_message("❌ არასწორი თარიღი!", ephemeral=True)
        return

    data = load_birthdays()
    guild_id = str(interaction.guild_id)
    user_id = str(member.id)

    if guild_id not in data:
        data[guild_id] = {}

    data[guild_id][user_id] = {
        "day": day,
        "month": month,
        "year": year,
        "username": member.display_name
    }
    save_birthdays(data)

    month_names = ["იანვარი", "თებერვალი", "მარტი", "აპრილი", "მაისი", "ივნისი",
                   "ივლისი", "აგვისტო", "სექტემბერი", "ოქტომბერი", "ნოემბერი", "დეკემბერი"]
    year_str = f" {year}" if year else ""
    await interaction.response.send_message(
        f"✅ **{member.display_name}**-ის დაბადების დღე დაემატა: {day} {month_names[month-1]}{year_str}",
        ephemeral=True
    )


@tree.command(name="birthday_setchannel", description="[ADMIN] დააყენე სად დაწეროს ბოტმა")
@app_commands.checks.has_permissions(administrator=True)
async def birthday_setchannel(interaction: discord.Interaction):
    data = load_birthdays()
    guild_id = str(interaction.guild_id)

    if guild_id not in data:
        data[guild_id] = {}

    data[guild_id]["channel_id"] = interaction.channel_id
    save_birthdays(data)

    await interaction.response.send_message(
        f"✅ ბოტი ახლა ამ channel-ში დაწერს დაბადების დღეებს! 🎂",
        ephemeral=True
    )


# ============================
# ავტომატური შემოწმება
# ============================

async def check_and_announce(guild: discord.Guild, force: bool = False) -> bool:
    data = load_birthdays()
    guild_id = str(guild.id)

    if guild_id not in data:
        return False

    today = datetime.now()
    found = False

    channel_id = data.get(guild_id, {}).get("channel_id", BIRTHDAY_CHANNEL_ID)
    channel = guild.get_channel(channel_id)
    if not channel:
        channel = next((c for c in guild.text_channels if c.permissions_for(guild.me).send_messages), None)

    if not channel:
        return False

    for user_id, bday in data[guild_id].items():
        if user_id == "channel_id":
            continue
        if bday["day"] == today.day and bday["month"] == today.month:
            member = guild.get_member(int(user_id))
            if member:
                age_str = ""
                if bday.get("year"):
                    age = today.year - bday["year"]
                    age_str = f"\n🔢 დღეს **{age}** წლის გახდა!"

                embed = discord.Embed(
                    title="🎂 დაბადების დღე! 🎉",
                    description=(
                        f"გილოცავ დაბადების დღეს, {member.mention}! 🥳🎊\n"
                        f"{age_str}\n✨\n"
                        f"მივულოცოთ ყველამ ერთად! ❤️"
                    ),
                    color=discord.Color.gold()
                )
                embed.set_thumbnail(url=member.display_avatar.url)
                embed.set_footer(text=f"🎈 {today.strftime('%d/%m/%Y')}")

                await channel.send(embed=embed)
                found = True

    return found


@tasks.loop(minutes=1)
async def birthday_task():
    now = datetime.utcnow()
    if now.hour == CHECK_HOUR and now.minute == CHECK_MINUTE:
        for guild in bot.guilds:
            await check_and_announce(guild)


# ============================
# ბოტის ივენთები
# ============================

@bot.event
async def on_ready():
    print(f"✅ ბოტი გაეშვა: {bot.user}")
    print(f"📡 სერვერები: {len(bot.guilds)}")

    try:
        synced = await tree.sync()
        print(f"🔄 Slash commands სინქრონიზებულია: {len(synced)}")
    except Exception as e:
        print(f"❌ Sync error: {e}")

    birthday_task.start()
    print(f"⏰ Birthday checker გაეშვა (ყოველ {CHECK_HOUR:02d}:{CHECK_MINUTE:02d} UTC)")


@birthday_task.before_loop
async def before_birthday_task():
    await bot.wait_until_ready()


# ============================
# გაშვება
# ============================
if __name__ == "__main__":
    bot.run(BOT_TOKEN)
