import os
import sys
import json
import time
import subprocess
import threading

SUITE_ITERATIONS = 3

RESULTS_DIR = "results"
MASTER_CPU_LOG = os.path.join(RESULTS_DIR, "linux_cpu.csv")
MASTER_PERF_LOG = os.path.join(RESULTS_DIR, "linux_perf.csv")

THERMAL_STABILIZATION_SEC = 600
IDLE_DURATION_SEC = 600
MPV_PLAYBACK_SEC = 600
SEVEN_ZIP_DURATION_SEC = 600
MPV_VIDEO_FILE = "./Tears-of-Steel.mov"

# --- Environment Setup & Teardown ---

def get_nvidia_pci_address():
    try:
        address = subprocess.check_output("lspci -D | awk '/NVIDIA/ {print $1; exit}'", shell=True, text=True).strip()
        if not address:
            raise ValueError("NVIDIA GPU not found in lspci.")
        print(f"Discovered NVIDIA GPU at PCIe Address: {address}")
        return address
    except Exception as e:
        print(f"Error locating NVIDIA PCIe address: {e}")
        exit(1)

def setup_environment():
    print("Executing Environment Setup.")
    os.makedirs(RESULTS_DIR, exist_ok=True)
    subprocess.run(["sudo", "systemctl", "mask", "sleep.target", "suspend.target", "hibernate.target"], stderr=subprocess.DEVNULL)
    subprocess.run(["powerprofilesctl", "set", "balanced"], stderr=subprocess.DEVNULL)
    subprocess.run(["brightnessctl", "set", "100%"], stderr=subprocess.DEVNULL)
    subprocess.run(["rfkill", "block", "bluetooth"], stderr=subprocess.DEVNULL)
    subprocess.run(["nmcli", "radio", "wifi", "off"], stderr=subprocess.DEVNULL)
    time.sleep(5)

def teardown_environment():
    print("\nRestoring System Environment.")
    subprocess.run(["nmcli", "radio", "wifi", "on"], stderr=subprocess.DEVNULL)
    subprocess.run(["rfkill", "unblock", "bluetooth"], stderr=subprocess.DEVNULL)
    subprocess.run(["brightnessctl", "set", "10%"], stderr=subprocess.DEVNULL)
    subprocess.run(["sudo", "systemctl", "unmask", "sleep.target", "suspend.target", "hibernate.target"], stderr=subprocess.DEVNULL)

# --- Master Telemetry Initialization ---

def start_master_cpu_telemetry():
    turbo_proc = subprocess.Popen(
        ["sudo", "turbostat", "--interval", "1", "--quiet", "--Summary", 
         "--show", "Time_Of_Day_Seconds,CorWatt,PkgWatt,Busy%,C1%,C2%,C3%,Bzy_MHz,Avg_MHz", 
         "--out", MASTER_CPU_LOG],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    
    perf_proc = subprocess.Popen(
        ["sudo", "perf", "stat", "-I", "1000", "-e", "context-switches,cpu-migrations", "-x,", "-o", MASTER_PERF_LOG],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    
    return turbo_proc, perf_proc

# --- Dynamic GPU Telemetry ---

def poll_d3cold(pci_address, log_file, stop_event):
    path = f"/sys/bus/pci/devices/{pci_address}/power/runtime_status"
    with open(log_file, 'w') as f:
        f.write("timestamp,runtime_status\n")
        while not stop_event.is_set():
            try:
                with open(path, 'r') as status_file:
                    status = status_file.read().strip()
            except Exception:
                status = "error"
            
            f.write(f"{time.time()},{status}\n")
            f.flush()
            time.sleep(1)

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

def run_workload(name, workload_func, run_dir, dgpu_active, pci_address):
    print(f"\nStarting Benchmark: {name}")
    
    stop_event = threading.Event()
    gpu_thread = None
    nvidia_proc = None
    
    if dgpu_active:
        gpu_log = os.path.join(run_dir, f"gpu_nsmi_{name}.csv")
        nvidia_proc = subprocess.Popen([
            "nvidia-smi", 
            "--query-gpu=timestamp,power.draw,utilization.gpu,temperature.gpu,pstate,clocks.gr,clocks.mem,pcie.link.gen.current,pcie.link.width.current", 
            "--format=csv,nounits", "-l", "1", "-f", gpu_log
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        gpu_log = os.path.join(run_dir, f"gpu_status_{name}.csv")
        gpu_thread = threading.Thread(target=poll_d3cold, args=(pci_address, gpu_log, stop_event))
        gpu_thread.start()
    
    start_time = time.time()
    
    workload_func(run_dir)
    
    end_time = time.time()
    
    if dgpu_active and nvidia_proc:
        nvidia_proc.terminate()
    else:
        stop_event.set()
        gpu_thread.join()

    # Prevent formatting issues
    sys.stdout.write('\r')
    sys.stdout.flush()

    log_epoch(run_dir, name, start_time, end_time)
    print(f"Finished Benchmark: {name}")

    
    sys.stdout.write('\r')
    sys.stdout.flush()
    
    time.sleep(THERMAL_STABILIZATION_SEC)

# --- Workload Definitions ---

def workload_idle(run_dir):
    time.sleep(IDLE_DURATION_SEC)

def workload_speedometer(run_dir):
    subprocess.run(["python", "speedometer_test.py", run_dir], check=True)

def workload_mpv(run_dir):
    mpv_cmd = [
        "mpv", "--hwdec=auto", "--loop-file=inf", "--no-audio", 
        "--vo=gpu", "--geometry=1920x1080", "--fs", "--no-terminal",
        f"--log-file={os.path.join(run_dir, 'mpv.txt')}", 
        MPV_VIDEO_FILE
    ]
    proc = subprocess.Popen(mpv_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(MPV_PLAYBACK_SEC)
    proc.terminate()

def workload_geekbench_cpu(run_dir):
    subprocess.run(["nmcli", "radio", "wifi", "on"], check=True)
    time.sleep(20) 
    
    with open(os.path.join(run_dir, "geekbench_cpu.txt"), "w") as out:
        subprocess.run(["geekbench"], stdout=out)
        
    subprocess.run(["nmcli", "radio", "wifi", "off"], check=True)

def workload_geekbench_compute(run_dir):
    subprocess.run(["nmcli", "radio", "wifi", "on"], check=True)
    time.sleep(20) 
    
    with open(os.path.join(run_dir, "geekbench_compute.txt"), "w") as out:
        subprocess.run(["geekbench", "--compute", "CUDA"], stdout=out)
        
    subprocess.run(["nmcli", "radio", "wifi", "off"], check=True)

def workload_7zip(run_dir):
    szip_cmd = ["7z", "b", "1000"]

    with open(os.path.join(run_dir, "7z.txt"), "w") as out:
        proc = subprocess.Popen(szip_cmd, stdout=out, stderr=subprocess.DEVNULL)
        time.sleep(SEVEN_ZIP_DURATION_SEC) 
        proc.terminate()

def workload_unigine(run_dir):
    subprocess.run(["python", "unigine_test.py", run_dir], check=True)

def workload_simultaneous(run_dir):
    subprocess.run(["python", "simultaneous_test.py", run_dir], check=True)

if __name__ == "__main__":    
    pci_address = get_nvidia_pci_address()
    setup_environment()
    
    print("Initializing continuous CPU/Scheduler sensors.")
    turbo_proc, perf_proc = start_master_cpu_telemetry()
    
    try:
        for i in range(1, SUITE_ITERATIONS + 1):
            print(f"\nStarting Suite Iteration {i} -")
            
            run_dir = os.path.join(RESULTS_DIR, f"run_{i}")
            os.makedirs(run_dir, exist_ok=True)
            init_epoch_log(run_dir)

            run_workload("system_idle", workload_idle, run_dir, False, pci_address)
            run_workload("speedometer", workload_speedometer, run_dir, False, pci_address)
            run_workload("mpv", workload_mpv, run_dir, True, pci_address)
            run_workload("geekbench_cpu", workload_geekbench_cpu, run_dir, False, pci_address)
            run_workload("geekbench_compute", workload_geekbench_compute, run_dir, True, pci_address)
            run_workload("7zip", workload_7zip, run_dir, False, pci_address)
            run_workload("unigine_heaven", workload_unigine, run_dir, True, pci_address)
            run_workload("dual_stress_test", workload_simultaneous, run_dir, True, pci_address)
            
    finally:
        print("\nSuite Complete.")
        turbo_proc.terminate()
        perf_proc.terminate()
        teardown_environment()