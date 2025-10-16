#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Skrypt do uruchamiania Telegram Bota z zmiennymi środowiskowymi
"""

import os
import sys
from telegram_bot import EmailPlanningBot

def load_env_file():
    """Ładuje zmienne środowiskowe z pliku .env"""
    env_file = '.env'
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
        print("✅ Załadowano zmienne środowiskowe z .env")
    else:
        print("⚠️ Plik .env nie istnieje. Używam zmiennych systemowych.")

def main():
    """Główna funkcja"""
    print("🚀 Uruchamianie Telegram Bota...")
    
    # Załaduj zmienne środowiskowe
    load_env_file()
    
    # Sprawdź wymagane zmienne
    required_vars = ['TELEGRAM_TOKEN', 'OPENAI_API_KEY', 'DEFAULT_RECIPIENT']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Brakuje wymaganych zmiennych środowiskowych: {', '.join(missing_vars)}")
        print("📝 Utwórz plik .env z wymaganymi zmiennymi lub ustaw je w systemie.")
        sys.exit(1)
    
    try:
        # Inicjalizuj i uruchom bota
        bot = EmailPlanningBot()
        print("✅ Bot zainicjalizowany pomyślnie!")
        print("🤖 Uruchamianie bota...")
        bot.run_bot()
    except KeyboardInterrupt:
        print("\n👋 Bot zatrzymany przez użytkownika")
    except Exception as e:
        print(f"❌ Błąd uruchamiania bota: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
