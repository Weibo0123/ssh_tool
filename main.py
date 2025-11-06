import paramiko
import getpass
import sys
import json
import os
import readline

HISTORY_SAVE_FILE = "history_save.txt"
TARGET_SAVE_FILE = "target_save.json"

def shell_simulation():
    readline.parse_and_bind("tab: complete")
    if os.path.exists(HISTORY_SAVE_FILE):
        readline.read_history_file(HISTORY_SAVE_FILE)
    
def get_target_machine():
    choice = input("Do you want to use your save targets(y/n): ").lower()
    if choice in ("y", "yes", "ye"):
        target = load_target_machine()
        if target:
            for i, name in enumerate(target.keys(), start=1):
                print(f"{i}: {name}")
            select = input("Which one do you want to choose?")
            try:
                select_number = int(select)
                if not (1 <= select_number <= len(target)):
                    raise ValueError 
            except ValueError:
                sys.exit("Invalid Target")
            select_name = list(target.keys())[select_number - 1]
            t = target[select_name]
            passwd = getpass.getpass()
            return select_name, t["ip"], t["port"], t["user"], passwd
        else:
            sys.exit("You don't have any saved targets!")
    elif choice in ("n", "no"):
        target_name = input("Target Name: ").strip()
        target_ip = input("Target IP: ").strip()
        try:
            target_port = int(input("Port: ").strip())
        except ValueError:
            sys.exit("Invalid Port")
        target_user = input("Username: ").strip()
        passwd = getpass.getpass()
        save_target_machine(target_name, target_ip, target_port, target_user)
        return target_name, target_ip, target_port, target_user, passwd
    else:
        sys.exit("Invalid Input")
    

def save_target_machine(name, ip, port, user):
    target = load_target_machine() or {}

    target[name] = {
        "ip": ip,
        "port": port,
        "user": user,
        }
    
    with open(TARGET_SAVE_FILE, "w") as f:
        json.dump(target, f, indent=4)
    print(f"Save Target Information to {TARGET_SAVE_FILE}")

def load_target_machine():
    if os.path.exists(TARGET_SAVE_FILE):
        with open(TARGET_SAVE_FILE) as f:
            return json.load(f)
    return None


def main():
    shell_simulation()
    name, ip, port, user, passwd = get_target_machine()
    
    client  = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(ip, port=port, username=user, password=passwd)
        while True:
            cmd = input("Command: ").strip()
            if cmd in ("exit", "quit"):
                break
            if not cmd:
                continue
            _, stdout, stderr = client.exec_command(cmd)
            output = stdout.readlines() + stderr.readlines()
            if output:
                print("\n=== Output ===\n")
                for line in output:
                    print(line.strip())
                    print("")
    except KeyboardInterrupt:
        sys.exit("Disconnected by user")
    except Exception as e:
        sys.exit(f"Connection Failed: {e}")

    client.close()

if __name__ == "__main__":
    main()