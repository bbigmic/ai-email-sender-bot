#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prosty skrypt do uruchamiania Telegram Bota
"""

import asyncio
import sys
import os
from telegram_bot import EmailPlanningBot

def main():
    """Funkcja główna"""
    print("🤖 Uruchamianie Telegram Bota...")
    print("=" * 40)
    
    # Sprawdź konfigurację
    config_file = "bot_config.json"
    if not os.path.exists(config_file):
        print("❌ Brak pliku konfiguracyjnego!")
        print("Uruchom: python setup_bot.py")
        return
    
    try:
        bot = EmailPlanningBot(config_file)
        print("✅ Bot zainicjalizowany")
        print("🚀 Uruchamianie...")
        print("⏹️  Naciśnij Ctrl+C aby zatrzymać")
        print("=" * 40)
        
        # Uruchom bota
        bot.run_bot()
        
    except KeyboardInterrupt:
        print("\n⏹️  Bot zatrzymany przez użytkownika")
    except Exception as e:
        print(f"\n❌ Błąd bota: {e}")
        print("Sprawdź konfigurację w bot_config.json")

if __name__ == "__main__":
    main()
