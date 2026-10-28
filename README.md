# 🎂 Discord Birthday Bot

Discord ბოტი, რომელიც ავტომატურად ულოცავს სერვერის წევრებს დაბადების დღეს.

---

## 📋 Commands

| Command | აღწერა |
|---|---|
| `/birthday_add` | შენი დაბადების დღის დამატება |
| `/birthday_remove` | შენი ბდღ-ს წაშლა |
| `/birthday_list` | სერვერზე ყველას ბდღ-ების ნახვა |
| `/birthday_next` | უახლოესი დაბადების დღეები და რამდენი დღეა დარჩენილი |
| `/birthday_check` | ხელით შეამოწმე დღეს ვის ბდღ აქვს |
| `/birthday_setchannel` | [Admin] ბდღ channel-ის დაყენება |
| `/birthday_role` | [Admin] როლი, რომელსაც იუბილარი თავის დღეს მიიღებს (როლის გარეშე ბოტი ახალს შექმნის) |
| `/birthday_role_off` | [Admin] Birthday როლის გამორთვა |
| `/birthday_reminder` | [Admin] შეხსენება ბდღ-მდე 1–14 დღით ადრე, არხში ან ადმინებს DM-ში |
| `/birthday_admin_add` | [Admin] სხვისი ბდღ-ს დამატება |
| `/birthday_admin_remove` | [Admin] სხვისი ბდღ-ს წაშლა |
| `/birthday_message` | [Admin] პირადი მილოცვა კონკრეტული ადამიანისთვის (ერთჯერადი ან ყოველწლიური, სურვილისამებრ DM-შიც) |
| `/birthday_message_remove` | [Admin] პირადი მილოცვის წაშლა |
| `/birthday_template_add` | [Admin] სერვერის მილოცვის შაბლონის დამატება |
| `/birthday_template_list` | [Admin] შაბლონების სია |
| `/birthday_template_remove` | [Admin] შაბლონის წაშლა ნომრით |
| `/create_event` | ახალი ივენთის შექმნა + Poll (დრო საქართველოს დროით) |
| `/events` | მომავალი ივენთების სია, ბმულებით და „მოდის“ ხმების რაოდენობით |
| `/delete_event` | [Admin] ივენთის წაშლა Forum-იდან |
| `/event_setchannel` | [Admin] ივენთების Forum Channel-ის დაყენება |
| `/help` | ბოტის ყველა command-ის სია |

---

## ⚙️ Discord Bot შექმნა

1. გადი [Discord Developer Portal](https://discord.com/developers/applications)
2. **New Application** → სახელი
3. **Bot** tab → **Add Bot**
4. **Reset Token** → დააკოპირე Token
5. **Privileged Gateway Intents** — ჩართე:
   - ✅ `SERVER MEMBERS INTENT`
   - ✅ `MESSAGE CONTENT INTENT`
6. **OAuth2 → URL Generator**:
   - Scopes: `bot`, `applications.commands`
   - Permissions: `Send Messages`, `Embed Links`, `Attach Files`, `Read Message History`, `Manage Roles` (Birthday როლისთვის), `Manage Threads` (ივენთების დახურვისთვის)
7. გენერირებული ლინკით ბოტი სერვერს დაამატე

---



### 3. სერვერის მომზადება

```bash
sudo apt update
sudo apt install python3 python3-pip git fonts-noto-core -y
pip3 install -U "discord.py>=2.4.0" Pillow --break-system-packages
```

`fonts-noto-core` ბარათზე ქართული ტექსტისთვისაა. ფონტის გარეშე ბოტი ბარათს არ დახატავს და ჩვეულებრივ მილოცვას გააგზავნის.

### 4. კოდის ჩამოტვირთვა

```bash
git clone https://github.com/ᲨᲔᲜᲘ_USERNAME/birthday-bot.git
cd birthday-bot
```

### 5. ბოტის იუზერის შექმნა (Security Best Practice)

```bash
# სერვის იუზერის შექმნა
sudo useradd -r -s /bin/false birthdaybot

# საქაღალდის გადატანა და უფლებების მინიჭება
sudo mv ~/birthday-bot /opt/DiscordBdayBot
sudo chown -R birthdaybot:birthdaybot /opt/DiscordBdayBot
chmod 750 /opt/DiscordBdayBot
```

### 6. Systemd Service შექმნა

```bash
sudo vim /etc/systemd/system/birthday-bot.service
```

ჩასვი:
```ini
[Unit]
Description=Birthday Bot
After=network.target

[Service]
User=birthdaybot
Group=birthdaybot
WorkingDirectory=/opt/DiscordBdayBot
Environment="BOT_TOKEN=შენი_ტოკენი_აქ"
ExecStart=/usr/bin/python3 bot.py
Restart=always
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

შეინახე `:wq`

```bash
sudo systemctl daemon-reload
sudo systemctl enable birthday-bot
sudo systemctl start birthday-bot
sudo systemctl status birthday-bot
```

🟢 `Active: active (running)` — მუშაობს!

---

## 🔄 კოდის განახლება

GitHub-ზე ცვლილების შემდეგ AWS-ზე:

```bash
cd /opt/DiscordBdayBot
sudo -u birthdaybot git pull
sudo systemctl restart birthday-bot
```

---

## 🛠️ სასარგებლო კომანდები

```bash
# სტატუსი
sudo systemctl status birthday-bot

# ლოგები
sudo journalctl -u birthday-bot -n 50

# გადატვირთვა
sudo systemctl restart birthday-bot

# გაჩერება
sudo systemctl stop birthday-bot
```

---

## 🔒 Security

იხილე `AWS_SECURITY` — სრული security გაიდი:
- Root SSH დაბლოკვა
- SSH Key-Only შესვლა
- UFW Firewall
- Fail2Ban
- Least Privilege იუზერი

---

## ⏰ საათის ზონა

ბოტი საქართველოს დროს იყენებს (UTC+4). მილოცვის საათი `bot.py`-შია:

```python
CHECK_HOUR = 13    # საქართველოს დროით
CHECK_MINUTE = 0
```

თუ ბოტი ამ დროს გათიშული იყო, ჩართვისთანავე მიულოცავს. ერთ ადამიანს წელიწადში მხოლოდ ერთხელ ულოცავს.

## 💌 მილოცვის ტექსტები

ნაგულისხმევი მილოცვები `birthday_messages.py`-შია, ბოტი შემთხვევით ირჩევს ერთ-ერთს.
ტექსტში შეგიძლია გამოიყენო `{mention}` (მონიშვნა) და `{name}` (სახელი), slash command-ში ახალი ხაზისთვის კი `\n`.
თუ სერვერზე `/birthday_template_add`-ით დაამატებ შაბლონებს, ნაგულისხმევის ნაცვლად ისინი გამოიყენება.
`/birthday_message`-ით დაყენებული პირადი მილოცვა ყოველთვის შაბლონზე წინ დგას.

## 🖼️ ბარათი

მილოცვას თან ახლავს სურათი: იუბილარის მრგვალი ფოტო, სახელი და ასაკი.
ფონი: `assets/birthday_bg.png` (ან `.jpg`), საუკეთესო ზომა 1000×400. თუ ფაილი არ არის, ბოტი სადა ფონს იყენებს.

## 💌 მილოცვების ბარათი

მილოცვის ქვეშ არის ღილაკი „✍️ მილოცვის დაწერა“. ყველა წერს თავის მილოცვას, 21:00-ზე (`WISHES_HOUR`)
ბოტი ყველაფერს ერთად უგზავნის იუბილარს პირადში. თუ DM დახურული აქვს, ბარათი ბდღ channel-ში გამოჩნდება.

## 🎉 ივენთები

- შეხსენება ივენთამდე 24 საათით და 1 საათით ადრე, Post-ში. ბოტი მონიშნავს ყველას, ვინც „მოვდივარ“ აირჩია.
- დაწყებიდან 12 საათში Post ავტომატურად იხურება (✅ + lock).
- ეს მუშაობს ამ განახლების შემდეგ შექმნილ ივენთებზე.

---

## 📁 ფაილები

| ფაილი | აღწერა |
|---|---|
| `bot.py` | მთავარი ბოტის კოდი |
| `birthday_messages.py` | ნაგულისხმევი მილოცვის ტექსტები |
| `card.py` | ბარათის სურათის დახატვა |
| `storage.py` | საერთო: საქართველოს დრო და `birthdays.json` |
| `assets/birthday_bg.png` | ბარათის ფონი (სურვილისამებრ) |
| `event_cog.py` | ივენთების ბრძანებები |
| `birthdays.json` | ავტომატურად იქმნება, ინახავს ბდღ-ებს |
| `requirements.txt` | Python dependencies |
| `Procfile` | Koyeb/Railway-სთვის |
| `AWS_SECURITY.md` | AWS Security გაიდი |
