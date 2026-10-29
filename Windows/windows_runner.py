import os
import sys
import json
import time
import subprocess
import signal

SUITE_ITERATIONS = 3

RESULTS_DIR = "results"
MASTER_CPU_LOG = os.path.join(RESULTS_DIR, "windows_cpu")
MASTER_PERF_LOG = os.path.join(RESULTS_DIR, "windows_perf.csv")

THERMAL_STABILIZATION_SEC = 600
IDLE_DURATION_SEC = 600
MPV_PLAYBACK_SEC = 600
SEVEN_ZIP_DURATION_SEC = 600
MPV_VIDEO_FILE = r".\Tears-of-Steel.mov"

# --- Environment Setup & Teardown ---

def setup_environment():
    print("Executing Environment Setup.")
    os.makedirs(RESULTS_DIR, exist_ok=True)
    subprocess.run(["powercfg", "/change", "standby-timeout-ac", "0"], check=True)
    subprocess.run(["powercfg", "/change", "monitor-timeout-ac", "0"], check=True)
    subprocess.run(["powercfg", "/change", "hibernate-timeout-ac", "0"], check=True)
    subprocess.run(["netsh", "interface", "set", "interface", "Wi-Fi", "admin=disable"], stderr=subprocess.DEVNULL)
    subprocess.run(["powershell", "-command", "Get-PnpDevice -Class Bluetooth | Where-Object { $_.InstanceId -match '^USB' } | Disable-PnpDevice -Confirm:$false"], stderr=subprocess.DEVNULL)
    subprocess.run(["powershell", "-command", "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, 100)"], stderr=subprocess.DEVNULL)
    time.sleep(5)

def teardown_environment():
    print("\nRestoring System Environment.")
    subprocess.run(["netsh", "interface", "set", "interface", "Wi-Fi", "admin=enable"], stderr=subprocess.DEVNULL)
    subprocess.run(["powershell", "-command", "Get-PnpDevice -Class Bluetooth | Where-Object { $_.InstanceId -match '^USB' } | Enable-PnpDevice -Confirm:$false"], stderr=subprocess.DEVNULL)
    subprocess.run(["powershell", "-command", "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, 80)"], stderr=subprocess.DEVNULL)
    subprocess.run(["powercfg", "/change", "standby-timeout-ac", "30"], check=True)
    subprocess.run(["powercfg", "/change", "monitor-timeout-ac", "15"], check=True)

# --- Master Telemetry Initialization ---

def start_master_cpu_telemetry():
    amduprof_cmd = [
        r"C:\Program Files\AMD\AMDuProf\bin\AMDuProfCLI.exe", "timechart", "--interval", "1000", "--event", "power,frequency,temperature,p-state", "--duration", "999999", "--output-dir", MASTER_CPU_LOG
    ]
    turbo_proc = subprocess.Popen(amduprof_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
    
    typeperf_cmd = [
        "typeperf", r"\System\Context Switches/sec", "-si", "1", "-o", MASTER_PERF_LOG, "-y"
    ]
    perf_proc = subprocess.Popen(typeperf_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
    
    return turbo_proc, perf_proc

# --- Main Workload Wrapper --- 

def get_epoch_file(run_dir):
    return os.path.join(run_dir, "epoch_markers.json")

def init_epoch_log(run_dir):
    with open(get_epoch_file(run_dir), 'w') as f:
        json.dump({}, f)

def log_epoch(run_dir, benchmark_name, start_time, end_time):
    filename = get_epoch_file(run_dir)
    with open(filename, 'r') as f:
        data = json.load(f)
    
    data[benchmark_name] = {
        "start": start_time,
        "end": end_time
    }
    
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)

def run_workload(name, workload_func, run_dir, dgpu_active):
    print(f"\nStarting Benchmark: {name}")
    
    nvidia_proc = None
    if dgpu_active:
        gpu_log = os.path.join(run_dir, f"gpu_nsmi_{name}.csv")
        nvidia_proc = subprocess.Popen([
            "nvidia-smi", 
            "--query-gpu=timestamp,power.draw,utilization.gpu,temperature.gpu,pstate,clocks.gr,clocks.mem,pcie.link.gen.current,pcie.link.width.current", 
            "--format=csv,nounits", "-l", "1", "-f", gpu_log
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
    
    start_time = time.time()
    
    workload_func(run_dir)
    
    end_time = time.time()
    
    if nvidia_proc:
        os.kill(nvidia_proc.pid, signal.CTRL_BREAK_EVENT)
        
    log_epoch(run_dir, name, start_time, end_time)
    print(f"Finished Benchmark: {name}")
    
    time.sleep(THERMAL_STABILIZATION_SEC)

# --- Workload Definitions ---

def workload_idle(run_dir):
    time.sleep(IDLE_DURATION_SEC)

def workload_speedometer(run_dir):
    subprocess.run([sys.executable, "speedometer_test.py", run_dir], check=True)

def workload_mpv(run_dir):
    mpv_cmd = [
        r".\Executables\mpv-x86_64\mpv.exe", "--hwdec=auto", "--loop-file=inf", "--no-audio", 
        "--vo=gpu", "--fs", "--geometry=1920x1080", "--no-terminal",
        f"--log-file={os.path.join(run_dir, 'mpv.txt')}", 
        MPV_VIDEO_FILE
    ]
    proc = subprocess.Popen(mpv_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(MPV_PLAYBACK_SEC)
    subprocess.run(["taskkill", "/F", "/IM", "mpv.exe", "/T"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def workload_geekbench_cpu(run_dir):
    subprocess.run(["netsh", "interface", "set", "interface", "Wi-Fi", "admin=enable"], check=True)
    time.sleep(20) 
    
    with open(os.path.join(run_dir, "geekbench_cpu.txt"), "w") as out:
        subprocess.run([r"C:\Program Files\Geekbench 7\geekbench7.exe"], stdout=out)
        
    subprocess.run(["netsh", "interface", "set", "interface", "Wi-Fi", "admin=disable"], check=True)

def workload_geekbench_compute(run_dir):
    subprocess.run(["netsh", "interface", "set", "interface", "Wi-Fi", "admin=enable"], check=True)
    time.sleep(20) 
    
    with open(os.path.join(run_dir, "geekbench_compute.txt"), "w") as out:
        subprocess.run([r"C:\Program Files\Geekbench 7\geekbench7.exe", "--compute", "CUDA"], stdout=out)
        
    subprocess.run(["netsh", "interface", "set", "interface", "Wi-Fi", "admin=disable"], check=True)

def workload_7zip(run_dir):
    szip_cmd = [r"C:\Program Files\7-Zip\7z.exe", "b", "1000"]

    with open(os.path.join(run_dir, "7z.txt"), "w") as out:
        proc = subprocess.Popen(szip_cmd, stdout=out, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        time.sleep(SEVEN_ZIP_DURATION_SEC)
        os.kill(proc.pid, signal.CTRL_BREAK_EVENT)

def workload_unigine(run_dir):
    subprocess.run([sys.executable, "unigine_test.py", run_dir], check=True)

def workload_simultaneous(run_dir):
    subprocess.run([sys.executable, "simultaneous_test.py", run_dir], check=True)

if __name__ == "__main__":    
    setup_environment()
    
    print("Initializing continuous CPU/Scheduler sensors.")
    turbo_proc, perf_proc = start_master_cpu_telemetry()
    
    try:
        for i in range(1, SUITE_ITERATIONS + 1):
            print(f"\nStarting Suite Iteration {i} -")
            
            run_dir = os.path.join(RESULTS_DIR, f"run_{i}")
            os.makedirs(run_dir, exist_ok=True)
            init_epoch_log(run_dir)

            run_workload("system_idle", workload_idle, run_dir, False)
            run_workload("speedometer", workload_speedometer, run_dir, False)
            run_workload("mpv", workload_mpv, run_dir, True)
            run_workload("geekbench_cpu", workload_geekbench_cpu, run_dir, False)
            run_workload("geekbench_compute", workload_geekbench_compute, run_dir, True)
            run_workload("7zip", workload_7zip, run_dir, False)
            run_workload("unigine_heaven", workload_unigine, run_dir, True)
            run_workload("dual_stress_test", workload_simultaneous, run_dir, True)
            
    finally:
        print("\nSuite Complete.")
        os.kill(turbo_proc.pid, signal.CTRL_BREAK_EVENT)
        os.kill(perf_proc.pid, signal.CTRL_BREAK_EVENT)
        teardown_environment()