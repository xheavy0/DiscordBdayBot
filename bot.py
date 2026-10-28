import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import calendar
import io
import os
import random
from datetime import date, datetime, timedelta
from typing import Optional
from event_cog import setup_event_commands
from birthday_messages import DEFAULT_MESSAGES, TITLES
from card import card_available, render_card
from storage import GEORGIA_TZ, now_ge, load_data as load_birthdays, save_data as save_birthdays

# ============================
# ᲙᲝᲜᲤᲘᲒᲣᲠᲐᲪᲘᲐ
# ============================
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# სურვილისამებრ: ნაგულისხმევი channel, სანამ /birthday_setchannel არ გაეშვება
_channel_env = os.environ.get("BIRTHDAY_CHANNEL_ID", "").strip()
DEFAULT_CHANNEL_ID = int(_channel_env) if _channel_env.isdigit() else None

CHECK_HOUR = 13    # საქართველოს დროით
CHECK_MINUTE = 0
WISHES_HOUR = 21   # ამ საათზე მიიღებს იუბილარი მილოცვების ბარათს

MAX_TEMPLATES = 25

MONTH_NAMES = ["იანვარი", "თებერვალი", "მარტი", "აპრილი", "მაისი", "ივნისი",
               "ივლისი", "აგვისტო", "სექტემბერი", "ოქტომბერი", "ნოემბერი", "დეკემბერი"]

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
def guild_birthdays(guild_data: dict) -> list:
    """მხოლოდ მომხმარებლების ჩანაწერები (user ID ციფრებია, პარამეტრები — არა)."""
    return [(uid, b) for uid, b in guild_data.items() if uid.isdigit() and isinstance(b, dict)]


def birthday_in_year(bday: dict, year: int) -> date:
    day, month = bday["day"], bday["month"]
    # 29 თებერვალი არანაკიან წელს 28-ში აღინიშნება
    if month == 2 and day == 29 and not calendar.isleap(year):
        day = 28
    return date(year, month, day)


def is_birthday_today(bday: dict, today: date) -> bool:
    """today შეიძლება იყოს date ან datetime."""
    return birthday_in_year(bday, today.year) == date(today.year, today.month, today.day)


def next_birthday(bday: dict, today: date) -> date:
    this_year = birthday_in_year(bday, today.year)
    return this_year if this_year >= today else birthday_in_year(bday, today.year + 1)


def days_until_text(days: int) -> str:
    if days == 0:
        return "🎉 **დღეს!**"
    if days == 1:
        return "ხვალ"
    return f"{days} დღეში"


def validate_date(day: int, month: int, year: Optional[int]) -> bool:
    if year is not None and not (1900 <= year <= now_ge().year):
        return False
    try:
        datetime(year or 2000, month, day)  # 2000 ნაკიანია, ასე 29 თებერვალიც გადის
        return True
    except ValueError:
        return False


def format_date(day: int, month: int, year: Optional[int]) -> str:
    year_str = f" {year}" if year else ""
    return f"{day} {MONTH_NAMES[month - 1]}{year_str}"


def save_birthday(guild_id: int, member: discord.abc.User, day: int, month: int, year: Optional[int]):
    """ინახავს თარიღს ისე, რომ პირადი მესიჯი და სხვა ველები არ დაიკარგოს."""
    data = load_birthdays()
    entry = data.setdefault(str(guild_id), {}).setdefault(str(member.id), {})
    if (entry.get("day"), entry.get("month")) != (day, month):
        entry.pop("announced_year", None)  # თარიღი შეიცვალა — თავიდან მივულოცოთ
    entry.update({"day": day, "month": month, "year": year, "username": member.display_name})
    save_birthdays(data)


def clean_text(text: str) -> str:
    """Slash command-ში ახალ ხაზს ვერ ჩაწერ, ამიტომ \\n-ს ახალ ხაზად ვაქცევთ."""
    return text.replace("\\n", "\n").strip()


def render(text: str, member: discord.abc.User) -> str:
    return text.replace("{mention}", member.mention).replace("{name}", member.display_name)


CARD_FILENAME = "birthday.jpg"


def build_birthday_embed(member: discord.abc.User, bday: dict, text: str, today: datetime,
                         with_card: bool = False) -> discord.Embed:
    description = render(text, member)
    # ბარათზე ფოტო და ასაკი ისედაც ჩანს, ამიტომ embed-ში აღარ ვიმეორებთ
    if bday.get("year") and not with_card:
        description += f"\n\n🔢 დღეს **{today.year - bday['year']}** წლის გახდა!"

    embed = discord.Embed(title=random.choice(TITLES), description=description, color=discord.Color.gold())
    if with_card:
        embed.set_image(url=f"attachment://{CARD_FILENAME}")
    else:
        embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text=f"🎈 {today.strftime('%d/%m/%Y')}")
    return embed


async def make_card_bytes(member: discord.abc.User, bday: dict, today: datetime) -> Optional[bytes]:
    """ხატავს ბარათს ავატარით და ფონით. ვერ დახატა — None (მაშინ ჩვეულებრივ embed-ს ვაგზავნით)."""
    if not card_available():
        return None
    try:
        avatar = await member.display_avatar.replace(size=256, format="png").read()
        age_line = f"დღეს {today.year - bday['year']} წლის გახდა" if bday.get("year") else ""
        buf = await asyncio.to_thread(
            render_card, avatar, member.display_name, "გილოცავ დაბადების დღეს!", age_line
        )
        return buf.getvalue()
    except Exception as e:
        print(f"⚠️ ბარათი ვერ დაიხატა ({member}): {e!r}")
        return None


def card_file(card: Optional[bytes]):
    return discord.File(io.BytesIO(card), filename=CARD_FILENAME) if card else None


async def send_ephemeral(interaction: discord.Interaction, content: str = None, **kwargs):
    if interaction.response.is_done():
        await interaction.followup.send(content, ephemeral=True, **kwargs)
    else:
        await interaction.response.send_message(content, ephemeral=True, **kwargs)


# ============================
# SLASH COMMANDS — დაბადების დღეები
# ============================

@tree.command(name="birthday_add", description="დაამატე შენი დაბადების დღე")
@app_commands.describe(day="დღე (1-31)", month="თვე (1-12)", year="წელი (სურვილისამებრ, მაგ: 1995)")
async def birthday_add(interaction: discord.Interaction, day: int, month: int, year: int = None):
    await interaction.response.defer(ephemeral=True)
    if not validate_date(day, month, year):
        await interaction.followup.send("❌ **არასწორი თარიღი!** გთხოვ შეამოწმე დღე, თვე და წელი.", ephemeral=True)
        return

    save_birthday(interaction.guild_id, interaction.user, day, month, year)
    await interaction.followup.send(
        f"✅ **დაბადების დღე დამახსოვრებულია!**\n"
        f"📅 {format_date(day, month, year)}\n"
        f"🎂 მიირთვი ტორტი მაშინ! 🎉",
        ephemeral=True
    )


@tree.command(name="birthday_remove", description="წაშალე შენი დაბადების დღე")
async def birthday_remove(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    data = load_birthdays()
    guild_id = str(interaction.guild_id)
    user_id = str(interaction.user.id)

    if guild_id in data and user_id in data[guild_id]:
        del data[guild_id][user_id]
        save_birthdays(data)
        await interaction.followup.send("🗑️ შენი დაბადების დღე წაიშალა.", ephemeral=True)
    else:
        await interaction.followup.send("❌ შენი დაბადების დღე არ არის შენახული.", ephemeral=True)


@tree.command(name="birthday_list", description="ნახე ყველას დაბადების დღე სერვერზე")
async def birthday_list(interaction: discord.Interaction):
    await interaction.response.defer()
    guild_data = load_birthdays().get(str(interaction.guild_id), {})
    birthdays = sorted(guild_birthdays(guild_data), key=lambda x: (x[1]["month"], x[1]["day"]))

    if not birthdays:
        await interaction.followup.send("📭 ჯერ არავის დაუმატებია დაბადების დღე.")
        return

    today = now_ge()
    lines = []
    for user_id, bday in birthdays:
        member = interaction.guild.get_member(int(user_id))
        name = member.display_name if member else bday.get("username", f"User {user_id}")
        today_mark = " 🎉 **დღეს!**" if is_birthday_today(bday, today) else ""
        lines.append(f"**{name}** — {format_date(bday['day'], bday['month'], bday.get('year'))}{today_mark}")

    embed = discord.Embed(title="🎂 სერვერის დაბადების დღეები", color=discord.Color.pink())
    embed.description = "\n".join(lines)
    embed.set_footer(text=f"სულ: {len(birthdays)} ადამიანი")
    await interaction.followup.send(embed=embed)


@tree.command(name="birthday_next", description="უახლოესი დაბადების დღეები")
@app_commands.describe(count="რამდენი ადამიანი ვაჩვენო (1-15)")
async def birthday_next(interaction: discord.Interaction, count: app_commands.Range[int, 1, 15] = 5):
    await interaction.response.defer()
    guild_data = load_birthdays().get(str(interaction.guild_id), {})
    today = now_ge().date()

    upcoming = []
    for uid, bday in guild_birthdays(guild_data):
        member = interaction.guild.get_member(int(uid))
        if not member:
            continue  # სერვერიდან წასულებს არ ვაჩვენებთ
        nxt = next_birthday(bday, today)
        upcoming.append(((nxt - today).days, member.display_name, bday, nxt))

    if not upcoming:
        await interaction.followup.send("📭 ჯერ არავის დაუმატებია დაბადების დღე.")
        return

    upcoming.sort(key=lambda x: (x[0], x[1].lower()))
    lines = []
    for days, name, bday, nxt in upcoming[:count]:
        verb = "გახდა" if days == 0 else "გახდება"
        age = f" · {verb} **{nxt.year - bday['year']}**" if bday.get("year") else ""
        lines.append(f"**{name}** — {nxt.day} {MONTH_NAMES[nxt.month - 1]} · {days_until_text(days)}{age}")

    embed = discord.Embed(title="📅 უახლოესი დაბადების დღეები", description="\n".join(lines),
                          color=discord.Color.pink())
    await interaction.followup.send(embed=embed)


@tree.command(name="birthday_check", description="შეამოწმე ვის ბდღ აქვს დღეს")
async def birthday_check(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    announced = await announce_birthdays(interaction.guild)

    today = now_ge()
    guild_data = load_birthdays().get(str(interaction.guild_id), {})
    todays = []
    for uid, bday in guild_birthdays(guild_data):
        if is_birthday_today(bday, today):
            member = interaction.guild.get_member(int(uid))
            todays.append(member.display_name if member else bday.get("username", uid))

    if announced:
        names = ", ".join(m.display_name for m in announced)
        await interaction.followup.send(f"✅ მივულოცე: **{names}** 🎉", ephemeral=True)
    elif todays:
        await interaction.followup.send(
            f"🎂 დღეს დაბადების დღეა: **{', '.join(todays)}**. უკვე მივულოცეთ! ✅", ephemeral=True
        )
    else:
        await interaction.followup.send("😔 დღეს არავის აქვს დაბადების დღე.", ephemeral=True)


@tree.command(name="birthday_admin_add", description="[ADMIN] სხვა მომხმარებლის ბდღ დამატება")
@app_commands.describe(member="მომხმარებელი", day="დღე", month="თვე", year="წელი (სურვილისამებრ)")
@app_commands.checks.has_permissions(administrator=True)
async def birthday_admin_add(interaction: discord.Interaction, member: discord.Member, day: int, month: int, year: int = None):
    await interaction.response.defer(ephemeral=True)
    if not validate_date(day, month, year):
        await interaction.followup.send("❌ არასწორი თარიღი!", ephemeral=True)
        return

    save_birthday(interaction.guild_id, member, day, month, year)
    await interaction.followup.send(
        f"✅ **{member.display_name}**-ის დაბადების დღე დაემატა: {format_date(day, month, year)}",
        ephemeral=True
    )


@tree.command(name="birthday_admin_remove", description="[ADMIN] სხვა მომხმარებლის ბდღ წაშლა")
@app_commands.describe(member="მომხმარებელი")
@app_commands.checks.has_permissions(administrator=True)
async def birthday_admin_remove(interaction: discord.Interaction, member: discord.Member):
    await interaction.response.defer(ephemeral=True)
    data = load_birthdays()
    guild_id = str(interaction.guild_id)
    user_id = str(member.id)

    if guild_id in data and user_id in data[guild_id]:
        del data[guild_id][user_id]
        save_birthdays(data)
        await interaction.followup.send(f"🗑️ **{member.display_name}**-ის დაბადების დღე წაიშალა.", ephemeral=True)
    else:
        await interaction.followup.send(f"❌ **{member.display_name}**-ის დაბადების დღე არ არის შენახული.", ephemeral=True)


@tree.command(name="birthday_setchannel", description="[ADMIN] დააყენე სად დაწეროს ბოტმა")
@app_commands.checks.has_permissions(administrator=True)
async def birthday_setchannel(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    data = load_birthdays()
    data.setdefault(str(interaction.guild_id), {})["channel_id"] = interaction.channel_id
    save_birthdays(data)
    await interaction.followup.send("✅ ბოტი ახლა ამ channel-ში დაწერს დაბადების დღეებს! 🎂", ephemeral=True)


# ============================
# SLASH COMMANDS — Birthday როლი
# ============================

@tree.command(name="birthday_role", description="[ADMIN] როლი, რომელსაც იუბილარი თავის დღეს მიიღებს")
@app_commands.describe(role="არსებული როლი (თუ არ მიუთითებ, ბოტი ახალ „🎂 იუბილარი“ როლს შექმნის)")
@app_commands.checks.has_permissions(administrator=True)
async def birthday_role(interaction: discord.Interaction, role: Optional[discord.Role] = None):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    me = guild.me

    if not me.guild_permissions.manage_roles:
        await interaction.followup.send(
            "❌ ბოტს **Manage Roles** უფლება სჭირდება. მიეცი Server Settings → Roles-ში.", ephemeral=True
        )
        return

    if role is None:
        try:
            role = await guild.create_role(
                name="🎂 იუბილარი", colour=discord.Colour.gold(), hoist=True,
                reason="Birthday bot: იუბილარის როლი"
            )
        except discord.HTTPException as e:
            await interaction.followup.send(f"❌ როლის შექმნა ვერ მოხერხდა: {e}", ephemeral=True)
            return
    elif role.is_default() or role.managed:
        await interaction.followup.send("❌ ეს როლი არ გამოდგება, სხვა აირჩიე.", ephemeral=True)
        return
    elif role >= me.top_role:
        await interaction.followup.send(
            f"❌ {role.mention} ბოტის როლზე მაღლაა, ამიტომ ბოტი მას ვერ გასცემს.\n"
            f"Server Settings → Roles-ში ბოტის როლი ამ როლზე მაღლა გადაიტანე.",
            ephemeral=True
        )
        return

    data = load_birthdays()
    data.setdefault(str(guild.id), {})["role_id"] = role.id
    save_birthdays(data)
    await sync_birthday_role(guild, now_ge())

    await interaction.followup.send(
        f"✅ იუბილარი თავის დღეს მიიღებს {role.mention} როლს, მეორე დღეს კი მოეხსნება.\n"
        f"💡 რომ როლი სიაში ცალკე და თავისი ფერით გამოჩნდეს, Server Settings → Roles-ში "
        f"რაც შეიძლება მაღლა აწიე (ოღონდ ბოტის როლის ქვემოთ).",
        ephemeral=True
    )


@tree.command(name="birthday_role_off", description="[ADMIN] Birthday როლის გამორთვა")
@app_commands.checks.has_permissions(administrator=True)
async def birthday_role_off(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    data = load_birthdays()
    role_id = data.get(str(interaction.guild_id), {}).pop("role_id", None)
    if not role_id:
        await interaction.followup.send("ℹ️ Birthday როლი ისედაც გამორთულია.", ephemeral=True)
        return
    save_birthdays(data)

    role = interaction.guild.get_role(role_id)
    if role:
        for member in list(role.members):
            try:
                await member.remove_roles(role, reason="Birthday bot: როლი გამოირთო")
            except discord.HTTPException:
                pass
    await interaction.followup.send("✅ Birthday როლი გამოირთო. თავად როლი სერვერზე დარჩა.", ephemeral=True)


# ============================
# SLASH COMMANDS — შეხსენება
# ============================

@tree.command(name="birthday_reminder", description="[ADMIN] შეხსენება დაბადების დღემდე რამდენიმე დღით ადრე")
@app_commands.describe(where="სად გაიგზავნოს შეხსენება", days="რამდენი დღით ადრე (1-14)")
@app_commands.choices(where=[
    app_commands.Choice(name="არხში (ბდღ channel-ში)", value="channel"),
    app_commands.Choice(name="ადმინებს პირადში (DM)", value="dm"),
    app_commands.Choice(name="გამორთვა", value="off"),
])
@app_commands.checks.has_permissions(administrator=True)
async def birthday_reminder(
    interaction: discord.Interaction,
    where: app_commands.Choice[str],
    days: app_commands.Range[int, 1, 14] = 1
):
    await interaction.response.defer(ephemeral=True)
    data = load_birthdays()
    guild_data = data.setdefault(str(interaction.guild_id), {})

    if where.value == "off":
        guild_data.pop("reminder", None)
        save_birthdays(data)
        await interaction.followup.send("🔕 შეხსენება გამოირთო.", ephemeral=True)
        return

    guild_data["reminder"] = {"mode": where.value, "days": days}
    save_birthdays(data)
    if where.value == "channel":
        target, note = "ბდღ channel-ში", ""
    else:
        target, note = "ადმინებს პირადში", "\nℹ️ თუ იუბილარი თავად ადმინია, საკუთარ შეხსენებას არ მიიღებს."
    await interaction.followup.send(
        f"🔔 შეხსენება ჩაირთო: დაბადების დღემდე {days} დღით ადრე, {target}, "
        f"{CHECK_HOUR:02d}:{CHECK_MINUTE:02d}-ზე.{note}",
        ephemeral=True
    )


# ============================
# SLASH COMMANDS — პირადი მილოცვა
# ============================

@tree.command(name="birthday_message", description="[ADMIN] პირადი მილოცვა კონკრეტული ადამიანისთვის")
@app_commands.describe(
    member="ვისთვის არის მილოცვა",
    message="ტექსტი. {mention} — მონიშვნა, {name} — სახელი, \\n — ახალი ხაზი",
    once="მხოლოდ ერთხელ გაიგზავნოს? (ნაგულისხმევად: ყოველ წელს)",
    dm="პირადშიც (DM) გაეგზავნოს?"
)
@app_commands.checks.has_permissions(administrator=True)
async def birthday_message(
    interaction: discord.Interaction,
    member: discord.Member,
    message: app_commands.Range[str, 1, 1500],
    once: bool = False,
    dm: bool = False
):
    await interaction.response.defer(ephemeral=True)
    data = load_birthdays()
    bday = data.get(str(interaction.guild_id), {}).get(str(member.id))
    if not bday:
        await interaction.followup.send(
            f"❌ **{member.display_name}**-ის დაბადების დღე არ არის შენახული. "
            f"ჯერ დაამატე `/birthday_admin_add`-ით.",
            ephemeral=True
        )
        return

    bday["message"] = clean_text(message)
    bday["message_once"] = once
    bday["message_dm"] = dm
    save_birthdays(data)

    extras = []
    extras.append("ერთჯერადი" if once else "ყოველ წელს")
    if dm:
        extras.append("+ DM-ში")
    preview = build_birthday_embed(member, bday, bday["message"], now_ge())
    await interaction.followup.send(
        f"✅ პირადი მილოცვა შენახულია **{member.display_name}**-ისთვის ({', '.join(extras)}).\n"
        f"🤫 მას ეს მესიჯი წინასწარ არ უჩანს. ასე გამოჩნდება:",
        embed=preview,
        ephemeral=True
    )


@tree.command(name="birthday_message_remove", description="[ADMIN] პირადი მილოცვის წაშლა")
@app_commands.describe(member="მომხმარებელი")
@app_commands.checks.has_permissions(administrator=True)
async def birthday_message_remove(interaction: discord.Interaction, member: discord.Member):
    await interaction.response.defer(ephemeral=True)
    data = load_birthdays()
    bday = data.get(str(interaction.guild_id), {}).get(str(member.id))
    if not bday or not bday.get("message"):
        await interaction.followup.send(f"❌ **{member.display_name}**-ს პირადი მილოცვა არ აქვს.", ephemeral=True)
        return

    for key in ("message", "message_once", "message_dm"):
        bday.pop(key, None)
    save_birthdays(data)
    await interaction.followup.send(
        f"🗑️ **{member.display_name}**-ის პირადი მილოცვა წაიშალა. ჩვეულებრივ შაბლონს მიიღებს.", ephemeral=True
    )


# ============================
# SLASH COMMANDS — მილოცვის შაბლონები
# ============================

@tree.command(name="birthday_template_add", description="[ADMIN] ახალი მილოცვის შაბლონის დამატება")
@app_commands.describe(text="ტექსტი. {mention} — მონიშვნა, {name} — სახელი, \\n — ახალი ხაზი")
@app_commands.checks.has_permissions(administrator=True)
async def birthday_template_add(interaction: discord.Interaction, text: app_commands.Range[str, 1, 1000]):
    await interaction.response.defer(ephemeral=True)
    data = load_birthdays()
    templates = data.setdefault(str(interaction.guild_id), {}).setdefault("templates", [])
    if len(templates) >= MAX_TEMPLATES:
        await interaction.followup.send(f"❌ მაქსიმუმ {MAX_TEMPLATES} შაბლონი შეიძლება. ჯერ წაშალე რომელიმე.", ephemeral=True)
        return

    templates.append(clean_text(text))
    save_birthdays(data)

    note = ""
    if len(templates) == 1:
        note = "\nℹ️ ახლა ამ სერვერზე მხოლოდ შენი შაბლონები გამოიყენება (ნაგულისხმევის ნაცვლად)."
    preview = build_birthday_embed(interaction.user, {}, templates[-1], now_ge())
    await interaction.followup.send(
        f"✅ შაბლონი #{len(templates)} დაემატა.{note}\nმაგალითი:", embed=preview, ephemeral=True
    )


@tree.command(name="birthday_template_list", description="[ADMIN] მილოცვის შაბლონების სია")
@app_commands.checks.has_permissions(administrator=True)
async def birthday_template_list(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    custom = load_birthdays().get(str(interaction.guild_id), {}).get("templates", [])

    if custom:
        title = "📝 სერვერის შაბლონები"
        footer = "წაშლა: /birthday_template_remove <ნომერი>"
        templates = custom
    else:
        title = "📝 ნაგულისხმევი შაბლონები"
        footer = "საკუთარი ჯერ არ დაგიმატებია. დამატება: /birthday_template_add"
        templates = DEFAULT_MESSAGES

    lines = []
    for i, t in enumerate(templates, 1):
        short = t if len(t) <= 150 else t[:147] + "..."
        lines.append(f"**{i}.** {short}")

    embed = discord.Embed(title=title, description="\n".join(lines), color=discord.Color.blurple())
    embed.set_footer(text=footer)
    await interaction.followup.send(embed=embed, ephemeral=True)


@tree.command(name="birthday_template_remove", description="[ADMIN] შაბლონის წაშლა ნომრით")
@app_commands.describe(number="შაბლონის ნომერი (/birthday_template_list-დან)")
@app_commands.checks.has_permissions(administrator=True)
async def birthday_template_remove(interaction: discord.Interaction, number: int):
    await interaction.response.defer(ephemeral=True)
    data = load_birthdays()
    templates = data.get(str(interaction.guild_id), {}).get("templates", [])
    if not 1 <= number <= len(templates):
        await interaction.followup.send("❌ ასეთი ნომრით სერვერის შაბლონი არ არსებობს.", ephemeral=True)
        return

    templates.pop(number - 1)
    save_birthdays(data)
    note = "\nℹ️ საკუთარი შაბლონი აღარ დარჩა, ისევ ნაგულისხმევი გამოიყენება." if not templates else ""
    await interaction.followup.send(f"🗑️ შაბლონი #{number} წაიშალა.{note}", ephemeral=True)


# ============================
# HELP
# ============================

@tree.command(name="help", description="ბოტის ყველა command-ის სია")
async def help_command(interaction: discord.Interaction):
    await interaction.response.defer()
    embed = discord.Embed(title="🤖 ბოტის Commands", color=discord.Color.blurple())

    embed.add_field(
        name="🎂 დაბადების დღეები",
        value=(
            "`/birthday_add` — შენი დაბადების დღის დამატება\n"
            "`/birthday_remove` — შენი ბდღ-ს წაშლა\n"
            "`/birthday_list` — სერვერზე ყველას ბდღ-ების სია\n"
            "`/birthday_next` — უახლოესი დაბადების დღეები\n"
            "`/birthday_check` — დღეს ვის ბდღ აქვს\n"
            "`/birthday_setchannel` — [Admin] ბდღ channel-ის დაყენება\n"
            "`/birthday_role` / `_role_off` — [Admin] იუბილარის როლი\n"
            "`/birthday_reminder` — [Admin] შეხსენება ბდღ-მდე\n"
            "`/birthday_admin_add` — [Admin] სხვისი ბდღ დამატება\n"
            "`/birthday_admin_remove` — [Admin] სხვისი ბდღ წაშლა"
        ),
        inline=False
    )

    embed.add_field(
        name="💌 მილოცვები",
        value=(
            "`/birthday_message` — [Admin] პირადი მილოცვა კონკრეტული ადამიანისთვის\n"
            "`/birthday_message_remove` — [Admin] პირადი მილოცვის წაშლა\n"
            "`/birthday_template_add` — [Admin] ახალი შაბლონი\n"
            "`/birthday_template_list` — [Admin] შაბლონების სია\n"
            "`/birthday_template_remove` — [Admin] შაბლონის წაშლა"
        ),
        inline=False
    )

    embed.add_field(
        name="🎉 ივენთები",
        value=(
            "`/create_event` — ახალი ივენთის შექმნა + Poll\n"
            "`/events` — მომავალი ივენთების სია\n"
            "`/delete_event` — [Admin] ივენთის წაშლა\n"
            "`/event_setchannel` — [Admin] ივენთების Forum Channel-ის დაყენება"
        ),
        inline=False
    )

    embed.add_field(name="ℹ️ სხვა", value="`/help` — ეს სია", inline=False)
    embed.set_footer(text="[Admin] — მხოლოდ ადმინისტრატორებისთვის")
    await interaction.followup.send(embed=embed)


@tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        message = "⛔ ამ ბრძანებისთვის საჭირო უფლება არ გაქვს."
    else:
        print(f"❌ Command error ({interaction.command and interaction.command.name}): {error!r}")
        message = "❌ რაღაც შეცდომა მოხდა. სცადე თავიდან."
    try:
        await send_ephemeral(interaction, message)
    except discord.HTTPException:
        pass


# ============================
# ავტომატური მილოცვა
# ============================

def get_birthday_channel(guild: discord.Guild, guild_data: dict):
    channel_id = guild_data.get("channel_id") or DEFAULT_CHANNEL_ID
    channel = guild.get_channel(channel_id) if channel_id else None
    if channel is None or not channel.permissions_for(guild.me).send_messages:
        channel = next((c for c in guild.text_channels if c.permissions_for(guild.me).send_messages), None)
    return channel


def mark_announced(guild_id: int, user_id: str, year: int):
    # ფაილს თავიდან ვკითხულობთ, რომ გაგზავნის დროს შეტანილი ცვლილებები არ დაიკარგოს
    data = load_birthdays()
    bday = data.get(str(guild_id), {}).get(user_id)
    if not bday:
        return
    bday["announced_year"] = year
    if bday.get("message_once"):
        for key in ("message", "message_once", "message_dm"):
            bday.pop(key, None)
    save_birthdays(data)


async def announce_birthdays(guild: discord.Guild) -> list:
    """ულოცავს ყველას, ვისაც დღეს აქვს ბდღ და წელს ჯერ არ მიგვილოცავს."""
    today = now_ge()
    guild_data = load_birthdays().get(str(guild.id), {})
    pending = [
        (uid, bday) for uid, bday in guild_birthdays(guild_data)
        if is_birthday_today(bday, today) and bday.get("announced_year") != today.year
    ]
    if not pending:
        return []

    channel = get_birthday_channel(guild, guild_data)
    if not channel:
        print(f"⚠️ {guild.name}: მილოცვისთვის channel ვერ მოიძებნა")
        return []

    templates = guild_data.get("templates") or DEFAULT_MESSAGES
    announced = []

    for uid, bday in pending:
        member = guild.get_member(int(uid))
        if not member:
            continue

        text = bday.get("message") or random.choice(templates)
        card = await make_card_bytes(member, bday, today)
        embed = build_birthday_embed(member, bday, text, today, with_card=card is not None)
        try:
            # mention embed-ის გარეთ, რომ ადამიანს ნოტიფიკაცია მოუვიდეს
            await channel.send(content=member.mention, embed=embed, file=card_file(card),
                               view=wish_view(uid, today.year))
        except discord.HTTPException as e:
            print(f"❌ {guild.name}: მილოცვა ვერ გაიგზავნა ({member}): {e}")
            continue

        mark_announced(guild.id, uid, today.year)
        announced.append(member)

        if bday.get("message") and bday.get("message_dm"):
            try:
                await member.send(embed=embed, file=card_file(card))
            except discord.HTTPException:
                print(f"⚠️ {member}-ს DM დახურული აქვს")

    return announced


# ============================
# მილოცვების ბარათი
# ============================
# მილოცვის ქვეშ არის ღილაკი. ყველა წერს თავის მილოცვას,
# WISHES_HOUR-ზე კი ბოტი ყველაფერს ერთ ბარათად უგზავნის იუბილარს პირადში.

WISH_PREFIX = "wish:"
WISHES_PER_MESSAGE = 10


def wish_view(uid: str, year: int, count: int = 0) -> discord.ui.View:
    view = discord.ui.View(timeout=None)
    label = "✍️ მილოცვის დაწერა" + (f" ({count})" if count else "")
    view.add_item(discord.ui.Button(
        label=label, style=discord.ButtonStyle.primary, custom_id=f"{WISH_PREFIX}{uid}:{year}"
    ))
    return view


def can_collect_wishes(bday: dict, year: int) -> bool:
    today = now_ge()
    return (
        year == today.year
        and is_birthday_today(bday, today)
        and bday.get("wishes_sent_year") != year
    )


class WishModal(discord.ui.Modal):
    def __init__(self, uid: str, year: int, birthday_name: str, existing: str = None):
        super().__init__(title=f"მილოცვა: {birthday_name}"[:45])
        self.uid = uid
        self.year = year
        self.birthday_name = birthday_name
        self.text = discord.ui.TextInput(
            label="შენი მილოცვა",
            style=discord.TextStyle.paragraph,
            placeholder="დაწერე რამე თბილი... 🎂",
            default=existing,
            max_length=500,
        )
        self.add_item(self.text)

    async def on_submit(self, interaction: discord.Interaction):
        data = load_birthdays()
        bday = data.get(str(interaction.guild_id), {}).get(self.uid)
        if not bday or not can_collect_wishes(bday, self.year):
            await interaction.response.send_message("⏰ ბარათი უკვე გაიგზავნა. მიულოცე პირადად! 🎉", ephemeral=True)
            return

        if bday.get("wishes_year") != self.year:
            bday["wishes"] = {}
            bday["wishes_year"] = self.year
        wishes = bday.setdefault("wishes", {})
        edited = str(interaction.user.id) in wishes
        wishes[str(interaction.user.id)] = {"name": interaction.user.display_name, "text": self.text.value.strip()}
        save_birthdays(data)

        verb = "განახლდა" if edited else "ჩაიწერა ბარათში"
        await interaction.response.send_message(
            f"💌 შენი მილოცვა {verb}! **{self.birthday_name}** მას {WISHES_HOUR:02d}:00-ზე მიიღებს.",
            ephemeral=True
        )
        # ღილაკზე მილოცვების რაოდენობას ვაჩვენებთ
        if interaction.message:
            try:
                await interaction.message.edit(view=wish_view(self.uid, self.year, len(wishes)))
            except discord.HTTPException:
                pass


@bot.listen("on_interaction")
async def on_wish_button(interaction: discord.Interaction):
    if interaction.type != discord.InteractionType.component:
        return
    custom_id = (interaction.data or {}).get("custom_id", "")
    if not custom_id.startswith(WISH_PREFIX):
        return

    uid, year = custom_id[len(WISH_PREFIX):].split(":")
    year = int(year)
    bday = load_birthdays().get(str(interaction.guild_id), {}).get(uid)

    if not bday or not can_collect_wishes(bday, year):
        await interaction.response.send_message(
            "⏰ ეს დაბადების დღე უკვე დასრულდა ან ბარათი გაიგზავნა. მიულოცე პირადად! 🎉", ephemeral=True
        )
        return
    if interaction.user.id == int(uid):
        await interaction.response.send_message(
            f"😄 ეს ღილაკი სხვებისთვისაა! შენი ბარათი {WISHES_HOUR:02d}:00-ზე მოგივა პირადში. 💌", ephemeral=True
        )
        return

    member = interaction.guild.get_member(int(uid))
    name = member.display_name if member else bday.get("username", "იუბილარი")
    existing = bday.get("wishes", {}).get(str(interaction.user.id), {}).get("text") \
        if bday.get("wishes_year") == year else None
    await interaction.response.send_modal(WishModal(uid, year, name, existing))


def build_wish_embeds(member: discord.Member, guild: discord.Guild, wishes: dict) -> list:
    items = list(wishes.values())
    embeds = []
    for i in range(0, len(items), WISHES_PER_MESSAGE):
        chunk = items[i:i + WISHES_PER_MESSAGE]
        embed = discord.Embed(color=discord.Color.pink())
        if i == 0:
            embed.title = "💌 შენი მილოცვების ბარათი"
            embed.description = f"**{guild.name}**-ის წევრებმა დაგიწერეს: 🎂"
            embed.set_thumbnail(url=member.display_avatar.url)
        for wish in chunk:
            embed.add_field(name=f"✍️ {wish['name']}", value=wish["text"][:1024], inline=False)
        embed.set_footer(text=f"სულ {len(items)} მილოცვა · გილოცავ დაბადების დღეს! 🎉")
        embeds.append(embed)
    return embeds


def mark_wishes_sent(guild_id: int, uid: str, year: int):
    data = load_birthdays()
    bday = data.get(str(guild_id), {}).get(uid)
    if bday:
        bday.pop("wishes", None)
        bday["wishes_sent_year"] = year
        save_birthdays(data)


async def deliver_wish_cards(guild: discord.Guild, now: datetime):
    guild_data = load_birthdays().get(str(guild.id), {})
    for uid, bday in guild_birthdays(guild_data):
        wishes, year = bday.get("wishes"), bday.get("wishes_year")
        if not wishes or not year or bday.get("wishes_sent_year") == year:
            continue
        # ვაგზავნით დაბადების დღის WISHES_HOUR-ზე (ან მოგვიანებით, თუ ბოტი გათიშული იყო)
        due_date = birthday_in_year(bday, year)
        if now.date() < due_date or (now.date() == due_date and now.hour < WISHES_HOUR):
            continue

        member = guild.get_member(int(uid))
        if not member:
            mark_wishes_sent(guild.id, uid, year)
            continue

        embeds = build_wish_embeds(member, guild, wishes)
        try:
            for embed in embeds:
                await member.send(embed=embed)
        except discord.HTTPException:
            # DM დახურულია — ბარათს ბდღ channel-ში ვდებთ, რომ მილოცვები არ დაიკარგოს
            channel = get_birthday_channel(guild, guild_data)
            if not channel:
                continue
            try:
                await channel.send(
                    f"{member.mention}, პირადი მესიჯები დახურული გაქვს, ამიტომ შენი ბარათი აქ არის 💌",
                    embed=embeds[0]
                )
                for embed in embeds[1:]:
                    await channel.send(embed=embed)
            except discord.HTTPException as e:
                print(f"❌ {guild.name}: ბარათი ვერ გაიგზავნა ({member}): {e}")
                continue

        mark_wishes_sent(guild.id, uid, year)


# ============================
# Birthday როლი, შეხსენება, ციკლი
# ============================

_role_warned = set()


async def sync_birthday_role(guild: discord.Guild, today: date):
    """იუბილარს როლს ვაძლევთ მთელი დღით, დანარჩენებს ვაცლით."""
    guild_data = load_birthdays().get(str(guild.id), {})
    role = guild.get_role(guild_data.get("role_id") or 0)
    if not role:
        return

    should_have = {int(uid) for uid, bday in guild_birthdays(guild_data) if is_birthday_today(bday, today)}
    changes = [(m, False) for m in role.members if m.id not in should_have]
    for uid in should_have:
        member = guild.get_member(uid)
        if member and role not in member.roles:
            changes.append((member, True))

    for member, add in changes:
        try:
            if add:
                await member.add_roles(role, reason="Birthday bot: დაბადების დღე 🎂")
            else:
                await member.remove_roles(role, reason="Birthday bot: დაბადების დღე დასრულდა")
        except discord.HTTPException as e:
            # ყოველ წუთს რომ არ გავავსოთ ლოგი, დღეში ერთხელ ვწერთ
            key = (guild.id, date(today.year, today.month, today.day))
            if key not in _role_warned:
                _role_warned.add(key)
                print(f"⚠️ {guild.name}: Birthday როლის შეცვლა ვერ მოხერხდა: {e}")


def mark_reminded(guild_id: int, user_ids: list, target_key: str):
    data = load_birthdays()
    guild_data = data.get(str(guild_id), {})
    for uid in user_ids:
        if uid in guild_data:
            guild_data[uid]["reminded_for"] = target_key
    save_birthdays(data)


async def send_reminders(guild: discord.Guild, today: date):
    guild_data = load_birthdays().get(str(guild.id), {})
    config = guild_data.get("reminder")
    if not config:
        return

    days = config.get("days", 1)
    target = date(today.year, today.month, today.day) + timedelta(days=days)
    target_key = target.isoformat()

    due = []
    for uid, bday in guild_birthdays(guild_data):
        if is_birthday_today(bday, target) and bday.get("reminded_for") != target_key:
            member = guild.get_member(int(uid))
            if member:
                due.append((uid, bday, member))
    if not due:
        return

    title = f"🔔 {days_until_text(days)} დაბადების დღეა!"

    def make_embed(people):
        lines = []
        for _, bday, member in people:
            age = f" · გახდება **{target.year - bday['year']}**" if bday.get("year") else ""
            lines.append(f"🎂 **{member.display_name}** — {target.day} {MONTH_NAMES[target.month - 1]}{age}")
        embed = discord.Embed(title=title, description="\n".join(lines), color=discord.Color.orange())
        embed.set_footer(text=guild.name)
        return embed

    if config.get("mode") == "dm":
        admins = [m for m in guild.members if not m.bot and m.guild_permissions.administrator]
        for admin in admins:
            people = [p for p in due if p[2].id != admin.id]  # საკუთარ ბდღ-ზე სიურპრიზს არ ვაფუჭებთ
            if not people:
                continue
            try:
                await admin.send(embed=make_embed(people))
            except discord.HTTPException:
                print(f"⚠️ {admin}-ს DM დახურული აქვს, შეხსენება ვერ მივიდა")
    else:
        channel = get_birthday_channel(guild, guild_data)
        if not channel:
            return
        await channel.send(embed=make_embed(due))

    mark_reminded(guild.id, [uid for uid, _, _ in due], target_key)


@tasks.loop(minutes=1)
async def birthday_task():
    now = now_ge()
    after_check_time = (now.hour, now.minute) >= (CHECK_HOUR, CHECK_MINUTE)
    for guild in bot.guilds:
        try:
            # როლი მთელი დღე უნდა ჰქონდეს, ამიტომ ამას ყოველ წუთს ვამოწმებთ
            await sync_birthday_role(guild, now)
            # დღის განმავლობაში ყოველ წუთს ვამოწმებთ, ასე გადატვირთვის შემდეგაც არავინ გამოგვრჩება.
            # announced_year / reminded_for-ის გამო არაფერი არ გაორდება.
            if after_check_time:
                await announce_birthdays(guild)
                await send_reminders(guild, now)
            await deliver_wish_cards(guild, now)
        except Exception as e:
            print(f"❌ Birthday task error ({guild.name}): {e!r}")


@birthday_task.before_loop
async def before_birthday_task():
    await bot.wait_until_ready()


# ============================
# ბოტის ივენთები
# ============================

_started = False


@bot.event
async def on_ready():
    global _started
    print(f"✅ ბოტი გაეშვა: {bot.user}")
    print(f"📡 სერვერები: {len(bot.guilds)}")

    # on_ready ხელახალი დაკავშირებისას თავიდან ეშვება, setup მხოლოდ ერთხელ გვჭირდება
    if _started:
        return
    _started = True

    setup_event_commands(tree, bot)

    try:
        synced = await tree.sync()
        print(f"🔄 Slash commands სინქრონიზებულია: {len(synced)}")
    except Exception as e:
        print(f"❌ Sync error: {e}")

    if not birthday_task.is_running():
        birthday_task.start()
    print(f"⏰ Birthday checker გაეშვა (ყოველდღე {CHECK_HOUR:02d}:{CHECK_MINUTE:02d} საქართველოს დროით)")


# ============================
# გაშვება
# ============================
if __name__ == "__main__":
    bot.run(BOT_TOKEN)
