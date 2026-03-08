# 🎂 Discord Birthday Bot

Discord ბოტი, რომელიც ავტომატურად ელოდება და ადღეგრძელებს სერვერის წევრებს დაბადების დღეზე.

---

## ⚙️ დაყენება

### 1. Python და dependency-ების ინსტალაცია

```bash
pip install -r requirements.txt
```

### 2. Discord Bot შექმნა

1. გადი [Discord Developer Portal](https://discord.com/developers/applications)
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

## 📁 ფაილები

- `bot.py` — მთავარი ბოტის კოდი
- `birthdays.json` — ავტომატურად იქმნება, ინახავს ბდღ-ებს
- `requirements.txt` — Python dependencies

---

## ⏰ საათის ზონა

ბოტი UTC-ს იყენებს. საქართველო = UTC+4:
- გინდა 09:00 🇬🇪? → `CHECK_HOUR = 5`
- გინდა 12:00 🇬🇪? → `CHECK_HOUR = 8`
