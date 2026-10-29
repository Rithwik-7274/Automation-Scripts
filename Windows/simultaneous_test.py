import os
import sys
import subprocess
import time
import pyautogui
import signal

pyautogui.FAILSAFE = False

# GUI coordinates for Unigine Heaven's "RUN" button
HEAVEN_RUN_BTN_X = 1255
HEAVEN_RUN_BTN_Y = 680

LAUNCH_DELAY_SEC = 10
VRAM_LOAD_DELAY_SEC = 20
THERMAL_SOAK_DELAY_SEC = 290
BENCHMARK_DURATION_SEC = 270

RESULTS_IMG = os.path.join(sys.argv[1], "simultaneous_unigine_results.png")
CPU_LOG_FILE = os.path.join(sys.argv[1], "simultaneous_7z.txt")

HEAVEN_CMD = [r"C:\Program Files (x86)\Unigine\Heaven Benchmark 4.0\heaven.bat"]
HEAVEN_DIR = r"C:\Program Files (x86)\Unigine\Heaven Benchmark 4.0"
SEVENZIP_CMD = [r"C:\Program Files\7-Zip\7z.exe", "b", "1000"]

if __name__ == "__main__":
    with open(CPU_LOG_FILE, "w") as cpu_bench_log:
        # Start the 7-Zip Benchmark
        cpu_bench = subprocess.Popen(SEVENZIP_CMD, stdout=cpu_bench_log, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)

        # Start Unigine Heaven
        heaven_process = subprocess.Popen(HEAVEN_CMD, cwd=HEAVEN_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(LAUNCH_DELAY_SEC)

        # Click "RUN" to engage the 3D engine
        pyautogui.click(x=HEAVEN_RUN_BTN_X, y=HEAVEN_RUN_BTN_Y) 
        time.sleep(VRAM_LOAD_DELAY_SEC)
        
        # Allow the GPU to heat up
        time.sleep(THERMAL_SOAK_DELAY_SEC)

        # Trigger Unigine Heaven's benchmark sequence
        pyautogui.press('f9')
        time.sleep(BENCHMARK_DURATION_SEC)

        # Take a screenshot of Unigine Heaven's score
        pyautogui.screenshot(RESULTS_IMG)

        # Cleanup processes
        subprocess.run(["taskkill", "/F", "/IM", "heaven.exe", "/IM", "browser_x86.exe"], stderr=subprocess.DEVNULL)
        os.kill(cpu_bench.pid, signal.CTRL_BREAK_EVENT)