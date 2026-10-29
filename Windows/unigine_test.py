import os
import sys
import subprocess
import time
import pyautogui

pyautogui.FAILSAFE = False

# GUI coordinates for Unigine Heaven "RUN" button
HEAVEN_RUN_BTN_X = 1255
HEAVEN_RUN_BTN_Y = 680

LAUNCH_DELAY_SEC = 10
VRAM_LOAD_DELAY_SEC = 30
BENCHMARK_DURATION_SEC = 270

HEAVEN_CMD = [r"C:\Program Files (x86)\Unigine\Heaven Benchmark 4.0\heaven.bat"]
HEAVEN_DIR = r"C:\Program Files (x86)\Unigine\Heaven Benchmark 4.0"
RESULTS_IMG = os.path.join(sys.argv[1], "unigine_results.png")

if __name__ == "__main__":
    # Launch Unigine
    heaven_process = subprocess.Popen(HEAVEN_CMD, cwd=HEAVEN_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(LAUNCH_DELAY_SEC)

    # Click "RUN" to enter 3D rendering mode
    pyautogui.click(x=HEAVEN_RUN_BTN_X, y=HEAVEN_RUN_BTN_Y)
    time.sleep(VRAM_LOAD_DELAY_SEC)

    # Trigger benchmark
    pyautogui.press('f9')
    time.sleep(BENCHMARK_DURATION_SEC)

    # Take screenshot of results
    pyautogui.screenshot(RESULTS_IMG)

    # Force kill lingering Unigine background processes
    subprocess.run(["taskkill", "/F", "/IM", "heaven.exe", "/IM", "browser_x86.exe"], stderr=subprocess.DEVNULL)