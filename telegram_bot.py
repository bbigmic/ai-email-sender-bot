#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Bot z AI do planowania wysyłki emaili
Bot analizuje wiadomości tekstowe i głosowe, planuje emaile
"""

import os
import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import tempfile

# Telegram Bot API
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# OpenAI API
import openai

# Nasz system emaili
from email_scheduler import EmailScheduler

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('telegram_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class EmailPlanningBot:
    """Bot Telegram do planowania wysyłki emaili z AI"""
    
    def __init__(self, config_file: str = "bot_config.json"):
        """
        Inicjalizacja bota
        
        Args:
            config_file: Ścieżka do pliku konfiguracyjnego
        """
        self.config_file = config_file
        self.config = self.load_config()
        
        # Inicjalizacja komponentów
        self.email_scheduler = EmailScheduler("email_config.json")
        self.openai_client = openai.OpenAI(api_key=self.config.get("openai_api_key"))
        
        # Pamięć konwersacji - przechowuje kontekst dla każdego użytkownika
        self.conversation_memory: Dict[int, Dict] = {}
        
        # Stan planowania emaila dla każdego użytkownika
        self.email_planning_state: Dict[int, Dict] = {}
        
        logger.info("Bot EmailPlanningBot zainicjalizowany")
    
    def load_config(self) -> Dict:
        """Ładuje konfigurację ze zmiennych środowiskowych i pliku JSON"""
        try:
            # Najpierw spróbuj załadować z pliku JSON (dla kompatybilności wstecznej)
            config = {}
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                logger.info(f"✅ Załadowano konfigurację z {self.config_file}")
            
            # Nadpisz wartościami ze zmiennych środowiskowych (priorytet)
            config = self.load_from_env(config)
            
            # Konwertuj wszystkie wartości string na UTF-8
            config = self.ensure_utf8_config(config)
            
            return config
        except Exception as e:
            logger.error(f"❌ Błąd ładowania konfiguracji: {e}")
            return self.get_default_config()
    
    def load_from_env(self, config: Dict) -> Dict:
        """Ładuje konfigurację ze zmiennych środowiskowych"""
        # Telegram Bot
        if os.getenv('TELEGRAM_TOKEN'):
            config['telegram_token'] = os.getenv('TELEGRAM_TOKEN')
        
        # OpenAI API
        if os.getenv('OPENAI_API_KEY'):
            config['openai_api_key'] = os.getenv('OPENAI_API_KEY')
        
        # Email settings
        if os.getenv('DEFAULT_RECIPIENT'):
            config['default_recipient'] = os.getenv('DEFAULT_RECIPIENT')
        
        # OpenAI model settings
        if os.getenv('OPENAI_MODEL'):
            config['openai_model'] = os.getenv('OPENAI_MODEL')
        
        if os.getenv('MAX_TOKENS'):
            try:
                config['max_tokens'] = int(os.getenv('MAX_TOKENS'))
            except ValueError:
                pass
        
        if os.getenv('TEMPERATURE'):
            try:
                config['temperature'] = float(os.getenv('TEMPERATURE'))
            except ValueError:
                pass
        
        if os.getenv('MAX_CONVERSATION_HISTORY'):
            try:
                config['max_conversation_history'] = int(os.getenv('MAX_CONVERSATION_HISTORY'))
            except ValueError:
                pass
        
        logger.info("✅ Załadowano konfigurację ze zmiennych środowiskowych")
        return config
    
    def ensure_utf8_config(self, config: Dict) -> Dict:
        """Zapewnia poprawne kodowanie UTF-8 dla konfiguracji"""
        def convert_to_utf8(obj):
            if isinstance(obj, str):
                return obj.encode('utf-8').decode('utf-8')
            elif isinstance(obj, dict):
                return {k: convert_to_utf8(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_to_utf8(item) for item in obj]
            else:
                return obj
        
        return convert_to_utf8(config)
    
    def get_default_config(self) -> Dict:
        """Zwraca domyślną konfigurację"""
        return {
            "telegram_token": "",
            "openai_api_key": "",
            "default_recipient": "borysm32@gmail.com",
            "bot_instructions": "Jestes pomocnym botem do planowania wysylki emaili. Analizuj wiadomosci uzytkownikow i pomagaj im zaplanowac emaile.",
            "max_conversation_history": 10
        }
    
    def save_config(self):
        """Zapisuje konfigurację"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            logger.info("Konfiguracja bota zapisana")
        except Exception as e:
            logger.error(f"Błąd podczas zapisywania konfiguracji: {e}")
    
    def get_user_memory(self, user_id: int) -> Dict:
        """Pobiera pamięć konwersacji użytkownika"""
        if user_id not in self.conversation_memory:
            self.conversation_memory[user_id] = {
                "messages": [],
                "current_email_plan": {},
                "waiting_for": None  # Co bot czeka od użytkownika
            }
        return self.conversation_memory[user_id]
    
    def add_to_memory(self, user_id: int, role: str, content: str):
        """Dodaje wiadomość do pamięci użytkownika"""
        if not content or content is None:
            content = ""
        
        memory = self.get_user_memory(user_id)
        memory["messages"].append({"role": role, "content": content})
        
        # Ogranicz historię konwersacji
        max_history = self.config.get("max_conversation_history", 10)
        if len(memory["messages"]) > max_history:
            memory["messages"] = memory["messages"][-max_history:]
    
    def get_conversation_context(self, user_id: int) -> List[Dict]:
        """Zwraca kontekst konwersacji dla OpenAI"""
        memory = self.get_user_memory(user_id)
        
        # Podstawowe instrukcje
        context = [
            {
                "role": "system",
                "content": f"""Jestes pomocnym botem do planowania wysylki emaili. 

INSTRUKCJE:
1. Analizuj wiadomosci uzytkownikow i wyciagaj informacje o planowanym emailu
2. Zawsze wysylaj emaile na adres: {self.config.get('default_recipient')}
3. Sam decyduj jaki ma byc temat i tresc emaila na podstawie widoamosci od uzytkownika.
4. Daty podawaj w formacie: DD.MM.RRRR HH:MM lub "za X minut/godzin/dni"
5. Jesli uzytkownik wspomni o zalaczniku, popros o przeslanie pliku


FORMAT ODPOWIEDZI:
- Jesli masz wszystkie dane: "GOTOWE: temat|tresc|data_wysylki"
- Jesli potrzebujesz zalacznika: "ZALACZNIK: opisz co potrzebujesz"

Przyklad kompletnych danych:
GOTOWE: Przypomnienie o spotkaniu|Spotkanie za 15 minut w sali konferencyjnej|za 2 godziny"""
            }
        ]
        
        # Dodaj historię konwersacji
        context.extend(memory["messages"])
        return context
    
    async def transcribe_voice(self, voice_file_path: str) -> str:
        """Transkrybuje plik głosowy na tekst"""
        try:
            with open(voice_file_path, "rb") as audio_file:
                transcript = self.openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )
            return transcript.text
        except Exception as e:
            logger.error(f"Błąd transkrypcji głosu: {e}")
            return ""
    
    async def analyze_message_with_ai(self, user_id: int, message_text: str) -> str:
        """Analizuje wiadomość użytkownika za pomocą AI"""
        try:
            # Sprawdź czy wiadomość nie jest pusta
            if not message_text or message_text.strip() == "":
                return "Nie otrzymalem zadnej wiadomosci. Napisz cos lub nagraj wiadomosc glosowa."
            
            # Dodaj wiadomość użytkownika do pamięci
            self.add_to_memory(user_id, "user", message_text)
            
            # Pobierz kontekst konwersacji
            context = self.get_conversation_context(user_id)
            
            # Wyczyść kontekst z null/None wartości
            clean_context = []
            for msg in context:
                if msg.get("content") is not None and msg.get("content") != "":
                    clean_context.append(msg)
            
            if not clean_context:
                return "Nie moge przetworzyc tej wiadomosci. Sprobuj ponownie."
            
            # Wyślij do OpenAI
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=clean_context,
                max_tokens=500,
                temperature=0.7
            )
            
            ai_response = response.choices[0].message.content
            if ai_response:
                self.add_to_memory(user_id, "assistant", ai_response)
                return ai_response
            else:
                return "Nie otrzymalem odpowiedzi od AI. Sprobuj ponownie."
            
        except Exception as e:
            logger.error(f"Blad analizy AI: {str(e)}")
            return "Przepraszam, wystapil blad podczas analizy wiadomosci. Sprobuj ponownie."
    
    def parse_ai_response(self, response: str) -> Tuple[str, Optional[Dict]]:
        """
        Parsuje odpowiedź AI i zwraca typ akcji oraz dane
        
        Returns:
            Tuple[typ_akcji, dane_emaila]
        """
        response = response.strip()
        
        if response.startswith("GOTOWE:"):
            # AI ma wszystkie dane - parsuj je
            data_part = response.replace("GOTOWE:", "").strip()
            parts = data_part.split("|")
            
            if len(parts) >= 3:
                subject = parts[0].strip()
                body = parts[1].strip()
                send_time = parts[2].strip()
                
                return "schedule_email", {
                    "subject": subject,
                    "body": body,
                    "send_time": send_time
                }
        
        elif response.startswith("ZAŁĄCZNIK:"):
            # AI potrzebuje załącznika
            attachment_info = response.replace("ZAŁĄCZNIK:", "").strip()
            return "request_attachment", {"info": attachment_info}
        
        else:
            # Zwykła odpowiedź tekstowa
            return "text_response", {"message": response}
    
    def parse_send_time(self, time_str: str) -> datetime:
        """Parsuje czas wysyłki w różnych formatach"""
        time_str = time_str.strip().lower()
        now = datetime.now()
        
        try:
            # Format: "za X minut/godzin/dni"
            if time_str.startswith("za "):
                parts = time_str.split()
                if len(parts) >= 3:
                    amount = int(parts[1])
                    unit = parts[2]
                    
                    if "minut" in unit:
                        return now + timedelta(minutes=amount)
                    elif "godzin" in unit:
                        return now + timedelta(hours=amount)
                    elif "dni" in unit:
                        return now + timedelta(days=amount)
            
            # Format: "DD.MM.RRRR HH:MM"
            elif "." in time_str and ":" in time_str:
                date_part, time_part = time_str.split()
                day, month, year = map(int, date_part.split("."))
                hour, minute = map(int, time_part.split(":"))
                return datetime(year, month, day, hour, minute)
            
            # Format: "HH:MM" (dzisiaj)
            elif len(time_str) == 5 and ":" in time_str:
                hour, minute = map(int, time_str.split(":"))
                target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                if target_time <= now:
                    target_time += timedelta(days=1)
                return target_time
            
        except (ValueError, IndexError):
            pass
        
        # Domyślnie za godzinę
        return now + timedelta(hours=1)
    
    async def start_scheduler_background(self):
        """Uruchamia scheduler w tle"""
        try:
            import threading
            import time
            
            def run_scheduler():
                logger.info("🚀 Uruchamianie schedulera w tle...")
                try:
                    self.email_scheduler.run_scheduler()
                except SystemExit:
                    logger.info("✅ Scheduler zakończony po wysłaniu emaila")
                except Exception as e:
                    logger.error(f"❌ Błąd schedulera: {e}")
            
            # Uruchom scheduler w osobnym wątku
            scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
            scheduler_thread.start()
            logger.info("✅ Scheduler uruchomiony w tle")
            
        except Exception as e:
            logger.error(f"❌ Błąd uruchamiania schedulera: {e}")
    
    async def schedule_email_from_ai(self, user_id: int, email_data: Dict, attachment_path: Optional[str] = None):
        """Planuje email na podstawie danych z AI"""
        try:
            send_datetime = self.parse_send_time(email_data["send_time"])
            
            # Log szczegółów emaila przed planowaniem
            logger.info(f"📧 PLANOWANIE EMAILA:")
            logger.info(f"   👤 Użytkownik: {user_id}")
            logger.info(f"   📧 Odbiorca: {self.config.get('default_recipient')}")
            logger.info(f"   📝 Temat: {email_data['subject']}")
            logger.info(f"   📅 Data wysyłki: {send_datetime.strftime('%d.%m.%Y %H:%M')}")
            logger.info(f"   📄 Treść: {email_data['body'][:200]}{'...' if len(email_data['body']) > 200 else ''}")
            if attachment_path:
                logger.info(f"   📎 Załącznik: {attachment_path}")
            
            # Zaplanuj email
            self.email_scheduler.schedule_email_datetime(
                to_email=self.config.get("default_recipient"),
                subject=email_data["subject"],
                body=email_data["body"],
                send_datetime=send_datetime,
                attachments=[attachment_path] if attachment_path else None
            )
            
            # Log potwierdzenia planowania
            logger.info(f"✅ EMAIL ZAPLANOWANY POMYŚLNIE!")
            logger.info(f"   📧 Temat: {email_data['subject']}")
            logger.info(f"   📅 Wysyłka: {send_datetime.strftime('%d.%m.%Y %H:%M')}")
            logger.info(f"   👤 Użytkownik: {user_id}")
            
            # Uruchom scheduler w tle
            await self.start_scheduler_background()
            
            # Wyczyść stan planowania
            if user_id in self.email_planning_state:
                del self.email_planning_state[user_id]
            
            return f"✅ Email zaplanowany pomyślnie!\n\n📧 Temat: {email_data['subject']}\n📅 Data wysyłki: {send_datetime.strftime('%d.%m.%Y %H:%M')}\n📝 Treść: {email_data['body'][:100]}{'...' if len(email_data['body']) > 100 else ''}"
            
        except Exception as e:
            logger.error(f"❌ BŁĄD PLANOWANIA EMAILA:")
            logger.error(f"   👤 Użytkownik: {user_id}")
            logger.error(f"   📧 Temat: {email_data.get('subject', 'BRAK')}")
            logger.error(f"   ⚠️  Błąd: {e}")
            return f"❌ Błąd podczas planowania emaila: {e}"
    
    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Obsługuje wiadomości tekstowe"""
        user_id = update.effective_user.id
        message_text = update.message.text
        
        logger.info(f"Wiadomosc tekstowa od {user_id}: {message_text}")
        
        # Sprawdź czy wiadomość nie jest pusta
        if not message_text or message_text.strip() == "":
            await update.message.reply_text("Nie otrzymalem zadnej wiadomosci. Napisz cos lub nagraj wiadomosc glosowa.")
            return
        
        # Analizuj wiadomość za pomocą AI
        ai_response = await self.analyze_message_with_ai(user_id, message_text)
        
        # Parsuj odpowiedź AI
        action_type, data = self.parse_ai_response(ai_response)
        
        if action_type == "schedule_email":
            # AI ma wszystkie dane - zaplanuj email
            logger.info(f"🤖 AI zdecydował: PLANOWANIE EMAILA")
            logger.info(f"   👤 Użytkownik: {user_id}")
            logger.info(f"   📝 Temat: {data.get('subject', 'BRAK')}")
            logger.info(f"   📅 Czas: {data.get('send_time', 'BRAK')}")
            
            result_message = await self.schedule_email_from_ai(user_id, data)
            await update.message.reply_text(result_message)
            
        elif action_type == "request_attachment":
            # AI potrzebuje załącznika
            logger.info(f"🤖 AI zdecydował: PROŚBA O ZAŁĄCZNIK")
            logger.info(f"   👤 Użytkownik: {user_id}")
            logger.info(f"   📎 Info: {data.get('info', 'BRAK')}")
            
            self.email_planning_state[user_id] = data
            await update.message.reply_text(f"📎 {data['info']}\n\nWyslij zalacznik jako plik.")
            
        else:
            # Zwykła odpowiedź tekstowa
            logger.info(f"🤖 AI zdecydował: ODPOWIEDŹ TEKSTOWA")
            logger.info(f"   👤 Użytkownik: {user_id}")
            logger.info(f"   💬 Odpowiedź: {ai_response[:100]}{'...' if len(ai_response) > 100 else ''}")
            
            await update.message.reply_text(ai_response)
    
    async def handle_voice_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Obsługuje wiadomości głosowe"""
        user_id = update.effective_user.id
        
        logger.info(f"Wiadomość głosowa od {user_id}")
        
        try:
            # Pobierz plik głosowy
            voice = update.message.voice
            file = await context.bot.get_file(voice.file_id)
            
            # Zapisz do pliku tymczasowego
            with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as temp_file:
                await file.download_to_drive(temp_file.name)
                temp_file_path = temp_file.name
            
            # Transkrybuj na tekst
            transcribed_text = await self.transcribe_voice(temp_file_path)
            
            # Usuń plik tymczasowy
            os.unlink(temp_file_path)
            
            if transcribed_text and transcribed_text.strip():
                await update.message.reply_text(f"🎤 Transkrypcja: {transcribed_text}")
                
                # Przetwórz transkrypcję bezpośrednio
                await self.process_transcribed_message(user_id, transcribed_text, update, context)
            else:
                await update.message.reply_text("❌ Nie udalo sie przetworzyc wiadomosci glosowej.")
                
        except Exception as e:
            logger.error(f"Błąd przetwarzania wiadomości głosowej: {e}")
            await update.message.reply_text("❌ Błąd podczas przetwarzania wiadomości głosowej.")
    
    async def process_transcribed_message(self, user_id: int, transcribed_text: str, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Przetwarza transkrypcję wiadomości głosowej"""
        try:
            logger.info(f"Przetwarzanie transkrypcji od {user_id}: {transcribed_text}")
            
            # Analizuj transkrypcję za pomocą AI
            ai_response = await self.analyze_message_with_ai(user_id, transcribed_text)
            
            # Parsuj odpowiedź AI
            action_type, data = self.parse_ai_response(ai_response)
            
            if action_type == "schedule_email":
                # AI ma wszystkie dane - zaplanuj email
                logger.info(f"🤖 AI zdecydował (GŁOS): PLANOWANIE EMAILA")
                logger.info(f"   👤 Użytkownik: {user_id}")
                logger.info(f"   📝 Temat: {data.get('subject', 'BRAK')}")
                logger.info(f"   📅 Czas: {data.get('send_time', 'BRAK')}")
                
                result_message = await self.schedule_email_from_ai(user_id, data)
                await update.message.reply_text(result_message)
                
            elif action_type == "request_attachment":
                # AI potrzebuje załącznika
                logger.info(f"🤖 AI zdecydował (GŁOS): PROŚBA O ZAŁĄCZNIK")
                logger.info(f"   👤 Użytkownik: {user_id}")
                logger.info(f"   📎 Info: {data.get('info', 'BRAK')}")
                
                self.email_planning_state[user_id] = data
                await update.message.reply_text(f"📎 {data['info']}\n\nWyslij zalacznik jako plik.")
                
            else:
                # Zwykła odpowiedź tekstowa
                logger.info(f"🤖 AI zdecydował (GŁOS): ODPOWIEDŹ TEKSTOWA")
                logger.info(f"   👤 Użytkownik: {user_id}")
                logger.info(f"   💬 Odpowiedź: {ai_response[:100]}{'...' if len(ai_response) > 100 else ''}")
                
                await update.message.reply_text(ai_response)
                
        except Exception as e:
            logger.error(f"Błąd przetwarzania transkrypcji: {e}")
            await update.message.reply_text("❌ Błąd podczas przetwarzania transkrypcji.")
    
    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Obsługuje załączniki"""
        user_id = update.effective_user.id
        
        logger.info(f"📎 ZAŁĄCZNIK OTRZYMANY:")
        logger.info(f"   👤 Użytkownik: {user_id}")
        logger.info(f"   📄 Nazwa pliku: {update.message.document.file_name}")
        logger.info(f"   📏 Rozmiar: {update.message.document.file_size} bajtów")
        
        if user_id not in self.email_planning_state:
            logger.warning(f"⚠️  Użytkownik {user_id} wysłał załącznik bez oczekiwania")
            await update.message.reply_text("❌ Nie oczekuję żadnego załącznika. Najpierw opisz email, który chcesz zaplanować.")
            return
        
        try:
            # Pobierz plik
            document = update.message.document
            file = await context.bot.get_file(document.file_id)
            
            # Zapisz załącznik
            attachment_filename = f"attachment_{user_id}_{datetime.now().timestamp()}_{document.file_name}"
            attachment_path = os.path.join("attachments", attachment_filename)
            
            # Utwórz folder attachments jeśli nie istnieje
            os.makedirs("attachments", exist_ok=True)
            
            await file.download_to_drive(attachment_path)
            
            # Pobierz dane emaila z pamięci
            memory = self.get_user_memory(user_id)
            last_assistant_message = None
            for msg in reversed(memory["messages"]):
                if msg["role"] == "assistant":
                    last_assistant_message = msg["content"]
                    break
            
            if last_assistant_message and last_assistant_message.startswith("GOTOWE:"):
                # Parsuj dane emaila
                _, email_data = self.parse_ai_response(last_assistant_message)
                
                # Zaplanuj email z załącznikiem
                result_message = await self.schedule_email_from_ai(user_id, email_data, attachment_path)
                await update.message.reply_text(result_message)
            else:
                await update.message.reply_text("✅ Załącznik otrzymany. Teraz opisz szczegóły emaila.")
            
        except Exception as e:
            logger.error(f"Błąd przetwarzania załącznika: {e}")
            await update.message.reply_text("❌ Błąd podczas przetwarzania załącznika.")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Obsługuje komendę /start"""
        welcome_message = """🤖 **Bot do planowania emaili**

Cześć! Jestem botem AI, który pomoże Ci zaplanować wysyłkę emaili.

**Jak używać:**
• Napisz lub nagraj wiadomość opisującą email, który chcesz zaplanować
• Bot przeanalizuje wiadomość i zapyta o brakujące szczegóły
• Jeśli wspomnisz o załączniku, bot poprosi o przesłanie pliku
• Bot automatycznie zaplanuje wysyłkę na określony czas

**Przykłady:**
• "Wyślij przypomnienie o spotkaniu jutro o 9:00"
• "Zaplanuj email z raportem za 2 godziny"
• "Wyślij życzenia urodzinowe 25.12.2024 10:00"

**Komendy:**
/start - pokaż tę wiadomość
/help - pomoc
/status - status bota

Zacznij od opisania emaila, który chcesz zaplanować! 📧"""
        
        await update.message.reply_text(welcome_message, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Obsługuje komendę /help"""
        help_message = """📚 **Pomoc - Bot do planowania emaili**

**Funkcje:**
✅ Analiza wiadomości tekstowych i głosowych
✅ Automatyczne planowanie wysyłki emaili
✅ Obsługa załączników
✅ Pamięć konwersacji
✅ Inteligentne pytania o brakujące dane

**Formaty dat i godzin:**
• "za 30 minut" - za 30 minut
• "za 2 godziny" - za 2 godziny
• "jutro 09:00" - jutro o 9:00
• "25.12.2024 15:30" - 25 grudnia o 15:30
• "14:30" - dzisiaj o 14:30

**Przykłady użycia:**
• "Wyślij przypomnienie o spotkaniu za godzinę"
• "Zaplanuj email z raportem jutro o 8:00"
• "Wyślij życzenia urodzinowe z załącznikiem 25.12.2024 10:00"

**Wsparcie:**
Jeśli masz problemy, napisz wiadomość opisującą co chcesz zrobić, a bot pomoże! 🤖"""
        
        await update.message.reply_text(help_message, parse_mode='Markdown')
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Obsługuje komendę /status"""
        status_message = f"""📊 **Status bota**

✅ Bot aktywny
✅ Email scheduler: {self.config.get('default_recipient')}
✅ OpenAI API: {'Połączone' if self.config.get('openai_api_key') else 'Nie skonfigurowane'}
✅ Aktywne konwersacje: {len(self.conversation_memory)}

**Ostatnie aktywności:**
Sprawdź logi w pliku `telegram_bot.log`"""
        
        await update.message.reply_text(status_message, parse_mode='Markdown')
    
    def setup_handlers(self, application: Application):
        """Konfiguruje handlery bota"""
        # Komendy
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("status", self.status_command))
        
        # Wiadomości
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text_message))
        application.add_handler(MessageHandler(filters.VOICE, self.handle_voice_message))
        application.add_handler(MessageHandler(filters.Document.ALL, self.handle_document))
    
    def run_bot(self):
        """Uruchamia bota"""
        if not self.config.get("telegram_token"):
            logger.error("Brak tokenu Telegram w konfiguracji!")
            return
        
        # Utwórz aplikację
        application = Application.builder().token(self.config["telegram_token"]).build()
        
        # Skonfiguruj handlery
        self.setup_handlers(application)
        
        logger.info("Bot uruchamiany...")
        
        # Uruchom bota
        application.run_polling()


def main():
    """Funkcja główna"""
    bot = EmailPlanningBot()
    bot.run_bot()


if __name__ == "__main__":
    main()
