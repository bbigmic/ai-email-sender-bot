# Email Scheduler - Zaplanowana wysyłka maili przez SMTP

Skrypt Python do zaplanowanej wysyłki maili przez protokół SMTP. Pozwala na planowanie wysyłki emaili na konkretną godzinę lub datę.

## Funkcje

- ✅ Planowanie wysyłki emaili na określoną godzinę
- ✅ Planowanie wysyłki na konkretną datę i godzinę
- ✅ Wysyłka emaili z załącznikami
- ✅ Obsługa treści HTML i tekstowej
- ✅ Konfiguracja przez plik JSON
- ✅ Logowanie wszystkich operacji
- ✅ Interfejs wiersza poleceń
- ✅ Obsługa różnych serwerów SMTP (Gmail, Outlook, itp.)

## Instalacja

1. Sklonuj lub pobierz projekt:
```bash
git clone <repository-url>
cd python-sender-email-later
```

2. Zainstaluj zależności:
```bash
pip install -r requirements.txt
```

## Konfiguracja

### 🔒 Bezpieczna konfiguracja przez zmienne środowiskowe

**Zalecane:** Użyj zmiennych środowiskowych dla wrażliwych danych:

1. **Skopiuj plik przykładowy:**
```bash
cp .env.example .env
```

2. **Edytuj `.env` z prawdziwymi danymi:**
```bash
# Telegram Bot
TELEGRAM_TOKEN=your_telegram_bot_token_here
OPENAI_API_KEY=your_openai_api_key_here
DEFAULT_RECIPIENT=your_email@example.com

# SMTP Email
SMTP_SERVER=s134.cyber-folks.pl
SMTP_PORT=465
SENDER_EMAIL=your_sender@example.com
SENDER_PASSWORD=your_password_here
USE_TLS=false
```

3. **Załaduj zmienne środowiskowe:**
```bash
# Linux/Mac
source .env

# Windows
# Ustaw zmienne w systemie lub użyj python-dotenv
```

### 📁 Alternatywnie: Pliki JSON (niezalecane dla produkcji)

Uruchom interaktywną konfigurację:
```bash
python email_scheduler.py --setup
```

Lub edytuj plik `email_config.json` ręcznie:

```json
{
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "sender_email": "twoj_email@gmail.com",
    "sender_password": "twoje_haslo_aplikacji",
    "use_tls": true,
    "recipients": [
        "odbiorca1@example.com",
        "odbiorca2@example.com"
    ],
    "default_subject": "Zaplanowany email",
    "default_body": "To jest zaplanowany email wysłany automatycznie."
}
```

### 2. Konfiguracja Gmail

Dla Gmail musisz użyć hasła aplikacji:

1. Włącz 2FA w swoim koncie Google
2. Wygeneruj hasło aplikacji: [Google Account Settings](https://myaccount.google.com/apppasswords)
3. Użyj tego hasła w konfiguracji

### 3. Inne serwery SMTP

- **Outlook/Hotmail**: `smtp-mail.outlook.com`, port 587
- **Yahoo**: `smtp.mail.yahoo.com`, port 587
- **Własny serwer**: Skonfiguruj odpowiedni serwer i port

## Użycie

### Interfejs wiersza poleceń

#### 1. Konfiguracja
```bash
python email_scheduler.py --setup
```

#### 2. Wysyłka natychmiastowa
```bash
python email_scheduler.py --send-now "odbiorca@example.com,Temat,Treść wiadomości"
```

#### 3. Planowanie na godzinę
```bash
python email_scheduler.py --schedule "odbiorca@example.com,Temat,Treść,14:30"
```

#### 4. Uruchomienie schedulera
```bash
python email_scheduler.py --run
```

### Użycie programistyczne

```python
from email_scheduler import EmailScheduler
from datetime import datetime, timedelta

# Inicjalizacja
scheduler = EmailScheduler("email_config.json")

# Wysyłka natychmiastowa
scheduler.send_email(
    to_email="odbiorca@example.com",
    subject="Temat wiadomości",
    body="Treść wiadomości",
    html_body="<h1>HTML treść</h1>",
    attachments=["plik1.pdf", "obraz.jpg"]
)

# Planowanie na godzinę (codziennie)
scheduler.schedule_email(
    to_email="odbiorca@example.com",
    subject="Codzienny raport",
    body="Treść raportu",
    send_time="09:00"
)

# Planowanie na konkretną datę i godzinę
future_time = datetime.now() + timedelta(hours=2)
scheduler.schedule_email_datetime(
    to_email="odbiorca@example.com",
    subject="Przypomnienie",
    body="To jest przypomnienie",
    send_datetime=future_time
)

# Uruchomienie schedulera
scheduler.run_scheduler()
```

## Przykłady użycia

### Codzienny raport o 8:00
```bash
python email_scheduler.py --schedule "szef@firma.com,Dzienny raport,Raport z wczoraj,08:00"
```

### Przypomnienie za 2 godziny
```python
from email_scheduler import EmailScheduler
from datetime import datetime, timedelta

scheduler = EmailScheduler()
future_time = datetime.now() + timedelta(hours=2)
scheduler.schedule_email_datetime(
    to_email="ja@example.com",
    subject="Przypomnienie o spotkaniu",
    body="Spotkanie za 15 minut!",
    send_datetime=future_time
)
scheduler.run_scheduler()
```

### Email z załącznikiem
```python
scheduler.send_email(
    to_email="odbiorca@example.com",
    subject="Dokumenty",
    body="W załączniku znajdziesz dokumenty",
    attachments=["dokument.pdf", "prezentacja.pptx"]
)
```

## Logi

Wszystkie operacje są logowane do pliku `email_scheduler.log` oraz wyświetlane w konsoli.

## Bezpieczeństwo

- Nigdy nie commituj pliku `email_config.json` z prawdziwymi danymi
- Używaj haseł aplikacji zamiast głównego hasła
- Rozważ użycie zmiennych środowiskowych dla wrażliwych danych

## Rozwiązywanie problemów

### Błąd uwierzytelniania
- Sprawdź czy email i hasło są poprawne
- Dla Gmail użyj hasła aplikacji
- Sprawdź czy 2FA jest włączone

### Błąd połączenia SMTP
- Sprawdź adres serwera i port
- Sprawdź połączenie internetowe
- Sprawdź ustawienia firewall

### Email nie został wysłany
- Sprawdź logi w pliku `email_scheduler.log`
- Sprawdź czy scheduler jest uruchomiony
- Sprawdź czy czas wysyłki jest w przyszłości

## Licencja

MIT License

## 🤖 Telegram Bot z AI

### Nowa funkcja: Inteligentny Bot Telegram

Bot analizuje wiadomości tekstowe i głosowe, automatycznie planuje emaile!

#### Funkcje Bota:
- ✅ **Analiza wiadomości tekstowych i głosowych** - używa OpenAI Whisper
- ✅ **Inteligentne planowanie** - AI analizuje i wyciąga szczegóły emaila
- ✅ **Pamięć konwersacji** - bot pamięta poprzednie wiadomości
- ✅ **Obsługa załączników** - automatyczne wykrywanie potrzeby załączników
- ✅ **Pytania o brakujące dane** - bot dopyta o szczegóły jeśli czegoś brakuje
- ✅ **Integracja z systemem emaili** - używa istniejącego EmailScheduler

#### Instalacja Bota:

1. **Zainstaluj zależności:**
```bash
pip install -r requirements.txt
```

2. **Skonfiguruj zmienne środowiskowe:**
```bash
cp .env.example .env
# Edytuj .env z prawdziwymi danymi
```

3. **Uruchom bota:**
```bash
python start_bot.py
```

#### Konfiguracja:

**Wymagane zmienne środowiskowe:**

1. **TELEGRAM_TOKEN:**
   - Napisz do @BotFather na Telegram
   - Wyślij `/newbot`
   - Podaj nazwę i username bota
   - Skopiuj token

2. **OPENAI_API_KEY:**
   - Idź na https://platform.openai.com/api-keys
   - Utwórz nowy klucz API
   - Skopiuj klucz

3. **DEFAULT_RECIPIENT:**
   - Email na który bot będzie wysyłał wiadomości

#### Użycie Bota:

**Komendy:**
- `/start` - rozpocznij pracę z botem
- `/help` - pomoc
- `/status` - status bota

**Przykłady wiadomości:**
- "Wyślij przypomnienie o spotkaniu jutro o 9:00"
- "Zaplanuj email z raportem za 2 godziny"
- "Wyślij życzenia urodzinowe z załącznikiem 25.12.2024 10:00"

**Formaty dat:**
- "za 30 minut" - za 30 minut
- "za 2 godziny" - za 2 godziny  
- "jutro 09:00" - jutro o 9:00
- "25.12.2024 15:30" - 25 grudnia o 15:30
- "14:30" - dzisiaj o 14:30

#### Jak działa Bot:

1. **Analiza:** Bot analizuje wiadomość za pomocą OpenAI GPT
2. **Wyciąganie danych:** AI wyciąga temat, treść, datę wysyłki
3. **Pytania:** Jeśli brakuje danych, bot pyta o szczegóły
4. **Załączniki:** Jeśli wspomnisz o załączniku, bot poprosi o plik
5. **Planowanie:** Bot automatycznie planuje wysyłkę emaila
6. **Potwierdzenie:** Bot potwierdza zaplanowanie z szczegółami

#### Pliki Bota:
- `telegram_bot.py` - główny kod bota
- `start_bot.py` - uruchamianie bota
- `email_scheduler.py` - system wysyłki emaili
- `.env.example` - przykładowa konfiguracja
- `attachments/` - folder na załączniki

#### Wdrożenie na Render:

1. **Wybierz "Background Workers"** na Render
2. **Ustaw zmienne środowiskowe** w panelu Render
3. **Build Command:** `pip install -r requirements.txt`
4. **Start Command:** `python start_bot.py`

## Autor

Assistant - 2024
