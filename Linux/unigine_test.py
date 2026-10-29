import os
import sys
import subprocess
import time
import pyautogui

pyautogui.FAILSAFE = False

# GUI coordinates for Unigine Heaven "Run" at 100% scaling
HEAVEN_RUN_BTN_X = 1255
HEAVEN_RUN_BTN_Y = 725

QT_LAUNCH_DELAY_SEC = 10
VRAM_LOAD_DELAY_SEC = 30
BENCHMARK_DURATION_SEC = 270

HEAVEN_CMD = ["prime-run", "unigine-heaven"]
RESULTS_IMG = os.path.join(sys.argv[1], "unigine_results.png")

if __name__ == "__main__":
    # Launch Unigine
    heaven_process = subprocess.Popen(HEAVEN_CMD, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(QT_LAUNCH_DELAY_SEC)

    # Click 'Run' to enter 3D rendering mode
    pyautogui.click(x=HEAVEN_RUN_BTN_X, y=HEAVEN_RUN_BTN_Y)
    time.sleep(VRAM_LOAD_DELAY_SEC)

    # Trigger benchmark
    pyautogui.press('f9')
    time.sleep(BENCHMARK_DURATION_SEC)

    # Take screenshot of results
    subprocess.run(["spectacle", "-b", "-o", RESULTS_IMG], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Force kill lingering Unigine background processes
    subprocess.run(["killall", "-9", "heaven_x64", "browser_x64"], stderr=subprocess.DEVNULL)