#!/usr/bin/env python3
"""Instagram Bot - Canlı İzleme ve Kontrol Scripti"""
import os
import time
import sys

def check_bot_status():
    """Bot durumunu kontrol et"""
    print("=" * 50)
    print("INSTAGRAM BOT - CANLI DURUM")
    print("=" * 50)

    # PID kontrolü
    pid_dir = 'pids'
    running_bots = []

    for bot_num in [1, 2, 3, 4]:
        pid_file = os.path.join(pid_dir, f'bot{bot_num}.pid')
        if os.path.exists(pid_file):
            try:
                with open(pid_file, 'r') as f:
                    pid = int(f.read().strip())
                try:
                    os.kill(pid, 0)
                    running_bots.append(bot_num)
                except:
                    pass
            except:
                pass

    if running_bots:
        print(f"✅ Çalışan botlar: {running_bots}")
    else:
        print("❌ Hiç bot çalışmıyor")

    # Log dosyaları
    print("\n📋 Son log kayıtları:")
    for bot_num in [1, 2, 3, 4]:
        log_file = os.path.join(pid_dir, f'bot{bot_num}.log')
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    if lines:
                        last_lines = lines[-5:]
                        print(f"\n  Bot {bot_num} (son 5 satır):")
                        for line in last_lines:
                            print(f"    {line.strip()}")
            except:
                pass

def watch_bot(bot_num, lines=20):
    """Belirli bir botun logunu canlı izle"""
    log_file = f'pids/bot{bot_num}.log'
    if not os.path.exists(log_file):
        print(f"Bot {bot_num} log dosyası bulunamadı!")
        return

    print(f"Bot {bot_num} izleniyor... (Ctrl+C ile durdur)")
    with open(log_file, 'r', encoding='utf-8') as f:
        f.seek(0, 2)  # Dosya sonuna git
        while True:
            line = f.readline()
            if line:
                print(line.strip())
            else:
                time.sleep(1)

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'watch':
        bot_num = int(sys.argv[2]) if len(sys.argv) > 2 else 4
        watch_bot(bot_num)
    else:
        check_bot_status()
