import os
import sys
import subprocess
import time
import pyautogui

pyautogui.FAILSAFE = False

# GUI coordinates for Unigine Heaven's "RUN" button at 100% scaling
HEAVEN_RUN_BTN_X = 1255
HEAVEN_RUN_BTN_Y = 725

QT_LAUNCH_DELAY_SEC = 10
VRAM_LOAD_DELAY_SEC = 30
THERMAL_SOAK_DELAY_SEC = 290
BENCHMARK_DURATION_SEC = 270

RESULTS_IMG = os.path.join(sys.argv[1], "simultaneous_unigine_results.png")
CPU_LOG_FILE = os.path.join(sys.argv[1], "simultaneous_7z.txt")

HEAVEN_CMD = ["prime-run", "unigine-heaven"]
SEVENZIP_CMD = ["7z", "b", "1000"]

if __name__ == "__main__":
    with open(CPU_LOG_FILE, "w") as cpu_bench_log:
        # Start the 7-Zip Benchmark
        cpu_bench = subprocess.Popen(SEVENZIP_CMD, stdout=cpu_bench_log, stderr=subprocess.DEVNULL)

        # Start Unigine Heaven
        heaven_process = subprocess.Popen(HEAVEN_CMD, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(QT_LAUNCH_DELAY_SEC)

        # Click "RUN" to engage the 3D engine
        pyautogui.click(x=HEAVEN_RUN_BTN_X, y=HEAVEN_RUN_BTN_Y) 
        time.sleep(VRAM_LOAD_DELAY_SEC)
        
        # Allow the GPU to heat up
        time.sleep(THERMAL_SOAK_DELAY_SEC)

        # Trigger Unigine Heaven's benchmark sequence
        pyautogui.press('f9')
        time.sleep(BENCHMARK_DURATION_SEC)

        # Take a screenshot of Unigine Heaven's score
        subprocess.run(["spectacle", "-b", "-o", RESULTS_IMG], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Cleanup processes
        subprocess.run(["killall", "-9", "heaven_x64", "browser_x64"], stderr=subprocess.DEVNULL)
        cpu_bench.terminate()