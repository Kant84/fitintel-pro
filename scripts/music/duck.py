# -*- coding: utf-8 -*-
"""Авто-дакинг: пока человек говорит в микрофон — музыка приглушается.
Детектор: RMS уровня микрофона (sounddevice). Порог + hold — настраиваются."""
import threading
import time


class VoiceDucker:
    def __init__(self, on_voice, on_silence,
                 threshold=0.08, hold_seconds=2.0,
                 device=None, blocksize=1024, dry_run=False):
        self.on_voice = on_voice
        self.on_silence = on_silence
        self.threshold = threshold
        self.hold = hold_seconds
        self.device = device
        self.blocksize = blocksize
        self.dry = dry_run
        self.speaking = False
        self.last_voice = 0.0
        self._stop = False
        self._thread = None

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return self

    def stop(self):
        self._stop = True

    def _run(self):
        if self.dry:
            print("DUCK | dry-run: дакинг эмулируется (без микрофона)")
            return
        try:
            import sounddevice as sd
            import numpy as np
        except ImportError:
            print("DUCK | sounddevice не установлен: pip install sounddevice"
                  " — дакинг отключён")
            return
        try:
            with sd.InputStream(device=self.device, channels=1,
                                blocksize=self.blocksize) as stream:
                while not self._stop:
                    data, _ = stream.read(self.blocksize)
                    rms = float(np.sqrt(np.mean(np.square(data))))
                    now = time.time()
                    if rms >= self.threshold:
                        self.last_voice = now
                        if not self.speaking:
                            self.speaking = True
                            try:
                                self.on_voice()
                            except Exception as e:
                                print("DUCK | on_voice ERR:", e)
                    elif self.speaking and now - self.last_voice >= self.hold:
                        self.speaking = False
                        try:
                            self.on_silence()
                        except Exception as e:
                            print("DUCK | on_silence ERR:", e)
        except Exception as e:
            print("DUCK | микрофон недоступен (%s) — дакинг отключён" % e)