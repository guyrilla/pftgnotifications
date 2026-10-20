import os
import sys
import time
import random
import threading
import numpy as np
import soundfile as sf
import soundcard as sc
import requests
from scipy.signal import fftconvolve, resample_poly
from math import gcd
from dotenv import load_dotenv

load_dotenv()

VK_TOKEN = os.environ.get("VK_COMMUNITY_TOKEN")
VK_PEER_ID = os.environ.get("VK_PEER_ID")
VK_API_VER = os.environ.get("VK_API_VERSION", "5.199")

if not VK_TOKEN:
    sys.exit("Ошибка: VK_COMMUNITY_TOKEN не задан в .env")
if not VK_PEER_ID:
    sys.exit("Ошибка: VK_PEER_ID не задан в .env")
if len(sys.argv) < 2:
    sys.exit('Использование: python detector.py "текст сообщения для VK"')

MESSAGE = sys.argv[1]

# ==== Детектор (без изменений) ====
TARGET_FILE = "sound.wav"
THRESHOLD = 0.6
COOLDOWN = 2.0
BLOCK = 4096
TARGET_SR = 48000
# ==================================


def send_vk(text: str) -> None:
    url = "https://api.vk.com/method/messages.send"
    payload = {
        "access_token": VK_TOKEN,
        "v": VK_API_VER,
        "peer_id": VK_PEER_ID,
        "message": text,
        "random_id": random.randint(0, 2**31 - 1),
        # для community-token обязателен group_id:
        "group_id": os.environ.get("VK_GROUP_ID", ""),
        "disable_mentions": 1,
    }
    payload = {k: v for k, v in payload.items() if v != ""}

    try:
        r = requests.post(url, data=payload, timeout=10)
        data = r.json()
        if "response" in data:
            print(f"[+] VK: отправлено (msg_id={data['response']})", flush=True)
            return
        err = data.get("error", {})
        code = err.get("error_code")
        msg = err.get("error_msg")
        hints = {
            5: "неверный/просроченный токен",
            901: "пользователь не писал сообществу — откройте сообщество и напишите ему любое сообщение (вариант A)",
            902: "пользователь запретил сообщения от сообщества",
            945: "беседа закрыта",
            946: "сообщество не разрешает сообщения",
            910: "бот не может писать первым — сначала пользователь должен написать боту",
            100: "неверный peer_id / параметры",
            6: "слишком много запросов в секунду",
        }
        hint = hints.get(code, "")
        print(
            f"[!] VK ошибка {code}: {msg}  {('— ' + hint) if hint else ''}", flush=True
        )
    except Exception as e:
        print(f"[!] Не удалось отправить в VK: {e}", flush=True)


def send_async(text: str) -> None:
    threading.Thread(target=send_vk, args=(text,), daemon=True).start()


# ---- Эталон ----
target, orig_sr = sf.read(TARGET_FILE, dtype="float32")
if target.ndim > 1:
    target = target.mean(axis=1)
if orig_sr != TARGET_SR:
    g = gcd(orig_sr, TARGET_SR)
    target = resample_poly(target, TARGET_SR // g, orig_sr // g).astype(np.float32)
    print(f"[*] Ресемплинг эталона: {orig_sr} → {TARGET_SR} Hz")

sr = TARGET_SR
target_energy = float(np.sum(target.astype(np.float64) ** 2))
target_rev = target[::-1].astype(np.float64)


def find_loopback_mic(speaker):
    try:
        mic = sc.get_microphone(id=str(speaker.name), include_loopback=True)
        if mic is not None:
            return mic
    except Exception:
        pass
    try:
        for m in sc.all_microphones(include_loopback=True):
            if getattr(m, "isloopback", False):
                return m
    except Exception:
        pass
    try:
        for m in sc.all_microphones(include_loopback=True):
            n = str(m.name).lower()
            if ".monitor" in n or n.startswith("monitor of"):
                return m
    except Exception:
        pass
    raise RuntimeError("Loopback-микрофон не найден.")


speaker = sc.default_speaker()
mic = find_loopback_mic(speaker)
print(f"[*] Слушаю: {mic.name}")
print(f"[*] При детекте отправлю: «{MESSAGE}» → peer_id={VK_PEER_ID}")

buf = np.zeros(len(target) + BLOCK * 2, dtype=np.float32)
last_trigger = 0.0

try:
    with mic.recorder(samplerate=sr, channels=1) as rec:
        print("[*] Готов. Ctrl+C для остановки.")
        while True:
            data = rec.record(numframes=BLOCK)
            if data.ndim > 1:
                data = data.mean(axis=1)
            data = data.astype(np.float32)
            if len(data) < BLOCK:
                data = np.pad(data, (0, BLOCK - len(data)))

            buf = np.concatenate([buf[len(data) :], data])

            corr = fftconvolve(buf.astype(np.float64), target_rev, mode="valid")
            cum = np.concatenate([[0.0], np.cumsum(buf.astype(np.float64) ** 2)])
            lags = np.arange(len(corr))
            win_energy = cum[lags + len(target)] - cum[lags]
            win_energy = np.maximum(win_energy, 1e-9)
            norm_corr = corr / np.sqrt(win_energy * target_energy)

            peak = float(norm_corr.max())
            now = time.time()

            if peak >= THRESHOLD and (now - last_trigger) > COOLDOWN:
                last_trigger = now
                print(f"[!] ДЕТЕКТ (score={peak:.2f}) — отправляю в VK", flush=True)
                send_async(MESSAGE)

except KeyboardInterrupt:
    print("\n[*] Остановлено.")
