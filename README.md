# 🎂 Discord Birthday Bot

Discord ბოტი, რომელიც ავტომატურად ულოცავს სერვერის წევრებს დაბადების დღეს.

---

## 📋 Commands

| Command | აღწერა |
|---|---|
| `/birthday_add` | შენი დაბადების დღის დამატება |
| `/birthday_remove` | შენი ბდღ-ს წაშლა |
| `/birthday_list` | სერვერზე ყველას ბდღ-ების ნახვა |
| `/birthday_check` | ხელით შეამოწმე დღეს ვის ბდღ აქვს |
| `/birthday_admin_add` | [Admin] სხვისი ბდღ-ს დამატება |
| `/birthday_admin_remove` | [Admin] სხვისი ბდღ-ს წაშლა |
| `/birthday_setchannel` | [Admin] ბოტის channel-ის დაყენება |

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
   - Permissions: `Send Messages`, `Embed Links`, `Read Message History`
7. გენერირებული ლინკით ბოტი სერვერს დაამატე

---

## ☁️ AWS EC2-ზე Hosting (უფასო 12 თვე)

### 1. EC2 Instance შექმნა

1. [AWS Console](https://console.aws.amazon.com) → **EC2** → **Launch Instance**
2. სახელი: `birthday-bot`
3. OS: **Ubuntu 22.04 LTS**
4. Instance type: **t2.micro** (Free Tier)
5. Key pair → **Create new key pair** → გადმოწერე `.pem` ფაილი
6. **Launch Instance**

### 2. SSH შეერთება

```bash
ssh -i "key.pem" ubuntu@შენი_EC2_PUBLIC_IP
```

Windows-ზე PEM უფლება:
```powershell
icacls "key.pem" /inheritance:r /grant:r "%username%:R"
```

### 3. სერვერის მომზადება

```bash
sudo apt update
sudo apt install python3 python3-pip git -y
pip3 install discord.py --break-system-packages
```

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

იხილე `AWS_SECURITY.md` — სრული security გაიდი:
- Root SSH დაბლოკვა
- SSH Key-Only შესვლა
- UFW Firewall
- Fail2Ban
- Least Privilege იუზერი

---

## ⏰ საათის ზონა

ბოტი UTC-ს იყენებს. საქართველო = UTC+4:

| საქართველო | UTC (კოდში) |
|---|---|
| 09:00 🇬🇪 | `CHECK_HOUR = 5` |
| 12:00 🇬🇪 | `CHECK_HOUR = 8` |
| 13:00 🇬🇪 | `CHECK_HOUR = 9` |

---

## 📁 ფაილები

| ფაილი | აღწერა |
|---|---|
| `bot.py` | მთავარი ბოტის კოდი |
| `birthdays.json` | ავტომატურად იქმნება, ინახავს ბდღ-ებს |
| `requirements.txt` | Python dependencies |
| `Procfile` | Koyeb/Railway-სთვის |
| `AWS_SECURITY.md` | AWS Security გაიდი |
