# 🎂 Discord Birthday Bot

Discord ბოტი, რომელიც ავტომატურად ულოცავს  სერვერის წევრებს დაბადების დღეს.

---

## ⚙️ დაყენება

### 1. Python და dependency-ების ინსტალაცია

```bash
pip install -r requirements.txt
```

### 2. Discord Bot შექმნა

1. გადადი [Discord Developer Portal](https://discord.com/developers/applications)
2. **New Application** → სახელი
3. **Bot** tab → **Add Bot**
4. **Reset Token** → დააკოპირე Token
5. **Privileged Gateway Intents** — ჩართე:
   - ✅ `SERVER MEMBERS INTENT`
   - ✅ `MESSAGE CONTENT INTENT`

### 3. ბოტის სერვერზე დამატება

**OAuth2** → **URL Generator**:
- Scopes: `bot`, `applications.commands`
- Permissions: `Send Messages`, `Embed Links`, `Read Message History`

გენერირებულ ლინკზე გადადი და სერვერს დაამატე ბოტი.

### 4. `bot.py` კონფიგურაცია

ბოტი ახლა იტვირთება `BOT_TOKEN` გარემოს ცვლადიდან — არ ინახავო токენს წვდომადი შინაარსში.

მხოლოდ შემდეგ ცვლადები უნდა განსაზღვრო:

```text
BIRTHDAY_CHANNEL_ID = 123456789  # Channel ID სადაც გამოაქვეყნოს
CHECK_HOUR = 9    # საათი UTC-ში (9 UTC = 13:00 საქართველო)
CHECK_MINUTE = 0
```

მოაწყე `BOT_TOKEN` გარემოს ცვლადი როგორც ქვემოთ:

- PowerShell (Windows, დროებითი სესიისთვის):

```powershell
$env:BOT_TOKEN = "შენი_ტოკენი_აქ"
python bot.py
```

- Linux / macOS (bash):

```bash
export BOT_TOKEN="შენი_ტოკენი_აქ"
python bot.py
```

თუ გსურს მუდმივად დაამატო სისტემურ გარემოს ცვლადებში, გამოიყენე სისტემის Settings ან `.env`-თან შესაბამისი ცვლა და ფრონტ-ტულები.

**Channel ID-ს მიღება:** Discord-ში Developer Mode ჩართე → channel-ზე მარჯვენა კლიკი → Copy ID

### 5. გაშვება

```bash
python bot.py
```

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

---

## 🐳 Docker-ით გაშვება (სურვილისამებრ)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "bot.py"]
```

```bash
docker build -t birthday-bot .
docker run -d --name birthday-bot birthday-bot
```

---

☁️ AWS EC2-ზე Hosting (უფასო 12 თვე) (ისედაც არ ჯდება ძვირი)
1. EC2 Instance შექმნა

AWS Console → EC2 → Launch Instance
სახელი: birthday-bot
OS: Ubuntu 22.04 LTS
Instance type: t2.micro (Free Tier)
Key pair → Create new key pair → გადმოწერე .pem ფაილი
Launch Instance

2. Security Group — პორტი გახსენი

EC2 → შენი Instance → Security tab
Security Group → Edit Inbound Rules
დაამატე: SSH → My IP

3. SSH დაკავშირება
bash# Windows (PowerShell) / Mac / Linux
ssh -i "key.pem" ubuntu@შენი_EC2_PUBLIC_IP
Windows-ზე თუ PEM-ის უფლება სჭირდება:
powershellicacls "key.pem" /inheritance:r /grant:r "%username%:R"

🔒 Security best practice-ი:
იუზერის შექმნა
sudo useradd -r -s /bin/false birthdaybot

# საქაღალდის უფლება
sudo chown -R birthdaybot:birthdaybot /root/DiscordBdayBot

# საქაღალდე გადაიტანე /opt-ში (უკეთესია)
sudo mv /სადაც ჰაქბს ფაილი/DiscordBdayBot /opt/DiscordBdayBot
sudo chown -R birthdaybot:birthdaybot /opt/DiscordBdayBot
4. სერვერის მომზადება
sudo apt update
sudo apt install python3 python3-pip git -y
pip3 install discord.py --break-system-packages
5. კოდის ჩამოტვირთვა GitHub-იდან
bashgit clone https://github.com/ᲨᲔᲜᲘ_USERNAME/birthday-bot.git
cd birthday-bot
6. Systemd Service შექმნა (24/7 გასაშვებად)
sudo vim /etc/systemd/system/birthday-bot.service
ჩასვი ეს:
[Unit]
Description=Birthday Bot
After=network.target

[Service]
User=birthdaybot
WorkingDirectory=/opt/DiscordBdayBot
Environment="BOT_TOKEN=შენი_ტოკენი"
ExecStart=/usr/bin/python3 bot.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target

Vim-ის საბაზისო კომანდები თუ დაგჭირდა:

i — რედაქტირების რეჟიმი
Esc — გამოსვლა რედაქტირებიდან
:wq — შენახვა და გასვლა
:q! — გასვლა შენახვის გარეშე

sudo systemctl daemon-reload
sudo systemctl enable birthday-bot
sudo systemctl start birthday-bot
7. სტატუსის შემოწმება
sudo systemctl status birthday-bot
🟢 Active: active (running) — მუშაობს!

🔄 კოდის განახლება
GitHub-ზე ცვლილების შემდეგ AWS-ზე:
cd /opt/birthday-bot
git pull
sudo systemctl restart birthday-bot

🛠️ სასარგებლო კომანდები

sudo systemctl status birthday-bot

# ლოგები
sudo journalctl -u birthday-bot -n 50

# გადატვირთვა
sudo systemctl restart birthday-bot

# გაჩერება
sudo systemctl stop birthday-bot


## 📁 ფაილები

- `bot.py` — მთავარი ბოტის კოდი
- `birthdays.json` — ავტომატურად იქმნება, ინახავს ბდღ-ებს
- `requirements.txt` — Python dependencies

---

## ⏰ საათის ზონა

ბოტი UTC-ს იყენებს. საქართველო = UTC+4:
- გინდა 09:00 🇬🇪? → `CHECK_HOUR = 5`
- გინდა 12:00 🇬🇪? → `CHECK_HOUR = 8`
