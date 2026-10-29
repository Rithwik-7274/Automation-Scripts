import time
import csv
import tinytuya

DEVICE_ID = ''
LOCAL_KEY = ''
VERSION = 3.5
DPS_POWER = '19'

def get_plug():
    """Initializes the plug with Auto-IP discovery and strict timeout overrides."""
    plug = tinytuya.OutletDevice(DEVICE_ID, 'Auto', LOCAL_KEY, version=VERSION)
    plug.set_socketPersistent(True)
    plug.set_socketTimeout(3)
    # Force tinytuya to abort immediately instead of hanging in an internal retry loop
    plug.socketRetryLimit = 1
    plug.socketRetryDelay = 1
    return plug

def main():
    print("Starting Tuya logger.")
    plug = None

    with open("tuya_wattage_log.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["host_timestamp", "wattage_W"])

        while True:
            try:
                # If the plug isn't connected, attempt to discover it
                if plug is None:
                    plug = get_plug()

                plug.updatedps([18, 19, 20])
                time.sleep(0.2)

                payload = plug.status()

                # Catch silent network timeouts
                if type(payload) is dict and 'Error' in payload:
                    raise ConnectionError(payload['Error'])

                if payload and 'dps' in payload:
                    watts = payload['dps'].get(DPS_POWER, 0) / 10.0
                    writer.writerow([time.time(), watts])
                    f.flush()
                    print(f"Logged: {watts}W")
                else:
                    # Standard behavior for a dropped packet/stale read without a full disconnect
                    plug.heartbeat()

            except Exception as e:
                # Catch everything
                print(f"Connection dropped or plug not found ({e}). Retrying in 2s.")
                plug = None
                time.sleep(2)

if __name__ == "__main__":
    main()