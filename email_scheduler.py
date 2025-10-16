#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Skrypt do zaplanowanej wysyłki maili przez SMTP
Autor: Assistant
Data: 2024
"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, timedelta
import time
import schedule
import logging
import json
import os
from typing import List, Dict, Optional
import argparse

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('email_scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class EmailScheduler:
    """Klasa do zarządzania zaplanowaną wysyłką maili"""
    
    def __init__(self, config_file: str = "email_config.json"):
        """
        Inicjalizacja schedulera emaili
        
        Args:
            config_file: Ścieżka do pliku konfiguracyjnego
        """
        self.config_file = config_file
        self.config = self.load_config()
        self.smtp_server = None
        self.smtp_port = None
        self.sender_email = None
        self.sender_password = None
        
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
            
            return config
        except Exception as e:
            logger.error(f"❌ Błąd ładowania konfiguracji: {e}")
            return self.get_default_config()
    
    def load_from_env(self, config: Dict) -> Dict:
        """Ładuje konfigurację ze zmiennych środowiskowych"""
        # SMTP settings
        if os.getenv('SMTP_SERVER'):
            config['smtp_server'] = os.getenv('SMTP_SERVER')
        
        if os.getenv('SMTP_PORT'):
            try:
                config['smtp_port'] = int(os.getenv('SMTP_PORT'))
            except ValueError:
                pass
        
        if os.getenv('SENDER_EMAIL'):
            config['sender_email'] = os.getenv('SENDER_EMAIL')
        
        if os.getenv('SENDER_PASSWORD'):
            config['sender_password'] = os.getenv('SENDER_PASSWORD')
        
        if os.getenv('USE_TLS'):
            config['use_tls'] = os.getenv('USE_TLS').lower() in ['true', '1', 'yes']
        
        if os.getenv('DEFAULT_RECIPIENT'):
            config['recipients'] = [os.getenv('DEFAULT_RECIPIENT')]
        
        if os.getenv('DEFAULT_SUBJECT'):
            config['default_subject'] = os.getenv('DEFAULT_SUBJECT')
        
        if os.getenv('DEFAULT_BODY'):
            config['default_body'] = os.getenv('DEFAULT_BODY')
        
        logger.info("✅ Załadowano konfigurację SMTP ze zmiennych środowiskowych")
        return config
    
    def get_default_config(self) -> Dict:
        """Zwraca domyślną konfigurację"""
        return {
            "smtp_server": "s134.cyber-folks.pl",
            "smtp_port": 465,
            "sender_email": "",
            "sender_password": "",
            "use_tls": True,
            "recipients": [],
            "default_subject": "Zaplanowany email",
            "default_body": "To jest zaplanowany email wysłany automatycznie."
        }
    
    def save_config(self):
        """Zapisuje konfigurację do pliku"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            logger.info("Konfiguracja została zapisana")
        except Exception as e:
            logger.error(f"Błąd podczas zapisywania konfiguracji: {e}")
    
    def setup_smtp(self):
        """Konfiguruje połączenie SMTP"""
        self.smtp_server = self.config.get("smtp_server")
        self.smtp_port = self.config.get("smtp_port")
        self.sender_email = self.config.get("sender_email")
        self.sender_password = self.config.get("sender_password")
        
        if not self.sender_email or not self.sender_password:
            raise ValueError("Email nadawcy i hasło muszą być skonfigurowane")
    
    def create_email(self, to_email: str, subject: str, body: str, 
                    html_body: Optional[str] = None, attachments: Optional[List[str]] = None) -> MIMEMultipart:
        """
        Tworzy wiadomość email
        
        Args:
            to_email: Adres email odbiorcy
            subject: Temat wiadomości
            body: Treść wiadomości (tekst)
            html_body: Treść wiadomości (HTML)
            attachments: Lista ścieżek do załączników
            
        Returns:
            Obiekt MIMEMultipart z wiadomością
        """
        msg = MIMEMultipart('alternative')
        msg['From'] = self.sender_email
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Dodaj treść tekstową
        text_part = MIMEText(body, 'plain', 'utf-8')
        msg.attach(text_part)
        
        # Dodaj treść HTML jeśli podana
        if html_body:
            html_part = MIMEText(html_body, 'html', 'utf-8')
            msg.attach(html_part)
        
        # Dodaj załączniki
        if attachments:
            for attachment_path in attachments:
                if os.path.exists(attachment_path):
                    with open(attachment_path, "rb") as attachment:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(attachment.read())
                        encoders.encode_base64(part)
                        part.add_header(
                            'Content-Disposition',
                            f'attachment; filename= {os.path.basename(attachment_path)}'
                        )
                        msg.attach(part)
                else:
                    logger.warning(f"Załącznik {attachment_path} nie istnieje")
        
        return msg
    
    def send_email(self, to_email: str, subject: str, body: str, 
                  html_body: Optional[str] = None, attachments: Optional[List[str]] = None) -> bool:
        """
        Wysyła pojedynczy email
        
        Args:
            to_email: Adres email odbiorcy
            subject: Temat wiadomości
            body: Treść wiadomości
            html_body: Treść HTML
            attachments: Lista załączników
            
        Returns:
            True jeśli email został wysłany pomyślnie
        """
        try:
            self.setup_smtp()
            
            # Utwórz wiadomość
            msg = self.create_email(to_email, subject, body, html_body, attachments)
            
            # Połącz z serwerem SMTP
            context = ssl.create_default_context()
            
            # Port 465 wymaga SSL, port 587 wymaga TLS
            if self.smtp_port == 465:
                # SSL connection
                with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, context=context) as server:
                    server.login(self.sender_email, self.sender_password)
                    
                    # Wyślij email
                    text = msg.as_string()
                    server.sendmail(self.sender_email, to_email, text)
            else:
                # TLS connection
                with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                    if self.config.get("use_tls", True):
                        server.starttls(context=context)
                    server.login(self.sender_email, self.sender_password)
                    
                    # Wyślij email
                    text = msg.as_string()
                    server.sendmail(self.sender_email, to_email, text)
                
            logger.info(f"✅ EMAIL WYSŁANY POMYŚLNIE!")
            logger.info(f"   📧 Odbiorca: {to_email}")
            logger.info(f"   📝 Temat: {subject}")
            logger.info(f"   📄 Treść: {body[:100]}{'...' if len(body) > 100 else ''}")
            if attachments:
                logger.info(f"   📎 Załączniki: {len(attachments)} plików")
            logger.info(f"   ⏰ Czas wysyłki: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
            return True
            
        except Exception as e:
            logger.error(f"Błąd podczas wysyłania emaila do {to_email}: {e}")
            return False
    
    def send_scheduled_email(self, to_email: str, subject: str, body: str, 
                           html_body: Optional[str] = None, attachments: Optional[List[str]] = None):
        """
        Wysyła zaplanowany email (używane przez scheduler)
        """
        logger.info(f"Wysyłanie zaplanowanego emaila do: {to_email}")
        success = self.send_email(to_email, subject, body, html_body, attachments)
        
        if success:
            logger.info(f"Zaplanowany email do {to_email} został wysłany pomyślnie")
        else:
            logger.error(f"Nie udało się wysłać zaplanowanego emaila do {to_email}")
    
    def send_scheduled_email_once(self, to_email: str, subject: str, body: str, 
                               html_body: Optional[str] = None, attachments: Optional[List[str]] = None):
        """
        Wysyła zaplanowany email JEDNORAZOWO i zatrzymuje scheduler
        """
        logger.info(f"Wysyłanie jednorazowego zaplanowanego emaila do: {to_email}")
        success = self.send_email(to_email, subject, body, html_body, attachments)
        
        if success:
            logger.info(f"✅ Zaplanowany email do {to_email} został wysłany pomyślnie")
            logger.info("🛑 Scheduler zostanie zatrzymany po wysłaniu emaila")
        else:
            logger.error(f"❌ Nie udało się wysłać zaplanowanego emaila do {to_email}")
        
        # Usuń wszystkie zadania z tagiem zawierającym ten email
        schedule.clear(f"once_{to_email}")
        
        # Zatrzymaj scheduler poprzez rzucenie wyjątku
        raise SystemExit("Email wysłany - scheduler zatrzymany")
    
    def schedule_email(self, to_email: str, subject: str, body: str, 
                      send_time: str, html_body: Optional[str] = None, 
                      attachments: Optional[List[str]] = None):
        """
        Planuje wysyłkę emaila na określoną godzinę
        
        Args:
            to_email: Adres email odbiorcy
            subject: Temat wiadomości
            body: Treść wiadomości
            send_time: Czas wysyłki w formacie "HH:MM" (24h)
            html_body: Treść HTML
            attachments: Lista załączników
        """
        try:
            # Sprawdź format czasu
            datetime.strptime(send_time, "%H:%M")
            
            # Zaplanuj wysyłkę
            schedule.every().day.at(send_time).do(
                self.send_scheduled_email, 
                to_email, subject, body, html_body, attachments
            )
            
            logger.info(f"Email zaplanowany na {send_time} dla {to_email}")
            
        except ValueError:
            logger.error(f"Nieprawidłowy format czasu: {send_time}. Użyj formatu HH:MM")
        except Exception as e:
            logger.error(f"Błąd podczas planowania emaila: {e}")
    
    def schedule_email_datetime(self, to_email: str, subject: str, body: str, 
                               send_datetime: datetime, html_body: Optional[str] = None, 
                               attachments: Optional[List[str]] = None):
        """
        Planuje wysyłkę emaila na określoną datę i godzinę
        
        Args:
            to_email: Adres email odbiorcy
            subject: Temat wiadomości
            body: Treść wiadomości
            send_datetime: Data i godzina wysyłki
            html_body: Treść HTML
            attachments: Lista załączników
        """
        now = datetime.now()
        if send_datetime <= now:
            logger.error("Data wysyłki musi być w przyszłości")
            return
        
        # Oblicz opóźnienie w sekundach
        delay_seconds = (send_datetime - now).total_seconds()
        
        # Zaplanuj wysyłkę JEDNORAZOWĄ
        schedule.every(delay_seconds).seconds.do(
            self.send_scheduled_email_once, 
            to_email, subject, body, html_body, attachments
        ).tag(f"once_{to_email}_{send_datetime.timestamp()}")
        
        logger.info(f"Email zaplanowany na {send_datetime} dla {to_email}")
    
    def run_scheduler(self):
        """Uruchamia scheduler w pętli"""
        logger.info("Scheduler emaili uruchomiony")
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Sprawdzaj co minutę
        except SystemExit as e:
            logger.info(f"🛑 Scheduler zatrzymany: {e}")
            raise
    
    def get_scheduled_jobs(self):
        """Zwraca listę zaplanowanych zadań"""
        return schedule.get_jobs()


def main():
    """Funkcja główna"""
    parser = argparse.ArgumentParser(description="Scheduler do zaplanowanej wysyłki emaili")
    parser.add_argument("--config", default="email_config.json", help="Plik konfiguracyjny")
    parser.add_argument("--setup", action="store_true", help="Uruchom konfigurację")
    parser.add_argument("--send-now", help="Wyślij email teraz (format: to_email,subject,body)")
    parser.add_argument("--schedule", help="Zaplanuj email (format: to_email,subject,body,HH:MM)")
    parser.add_argument("--run", action="store_true", help="Uruchom scheduler")
    
    args = parser.parse_args()
    
    scheduler = EmailScheduler(args.config)
    
    if args.setup:
        # Interaktywna konfiguracja
        print("=== Konfiguracja Email Scheduler ===")
        smtp_server = input(f"Serwer SMTP [{scheduler.config['smtp_server']}]: ") or scheduler.config['smtp_server']
        smtp_port = input(f"Port SMTP [{scheduler.config['smtp_port']}]: ") or scheduler.config['smtp_port']
        sender_email = input(f"Email nadawcy: ")
        sender_password = input(f"Hasło: ")
        
        scheduler.config.update({
            'smtp_server': smtp_server,
            'smtp_port': int(smtp_port),
            'sender_email': sender_email,
            'sender_password': sender_password
        })
        
        scheduler.save_config()
        print("Konfiguracja zapisana!")
        
    elif args.send_now:
        # Wyślij email teraz
        parts = args.send_now.split(',', 2)
        if len(parts) >= 3:
            to_email, subject, body = parts
            success = scheduler.send_email(to_email.strip(), subject.strip(), body.strip())
            print(f"Email {'wysłany' if success else 'nie został wysłany'}")
        else:
            print("Nieprawidłowy format. Użyj: to_email,subject,body")
            
    elif args.schedule:
        # Zaplanuj email
        parts = args.schedule.split(',', 3)
        if len(parts) >= 4:
            to_email, subject, body, send_time = parts
            scheduler.schedule_email(to_email.strip(), subject.strip(), body.strip(), send_time.strip())
            print(f"Email zaplanowany na {send_time}")
        else:
            print("Nieprawidłowy format. Użyj: to_email,subject,body,HH:MM")
            
    elif args.run:
        # Uruchom scheduler
        scheduler.run_scheduler()
        
    else:
        print("Użyj --help aby zobaczyć dostępne opcje")


if __name__ == "__main__":
    main()
