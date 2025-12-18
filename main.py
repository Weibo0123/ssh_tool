import paramiko
import getpass
import sys
import json
import os
import select
import tty
import termios

TARGET_SAVE_FILE = "target_save.json"

def get_target_machine():
    choice = input("Do you want to use your save targets(y/n): ").lower()
    if choice in ("y", "yes", "ye"):
        target = load_target_machine()
        if target:
            for i, name in enumerate(target.keys(), start=1):
                print(f"{i}: {name}")
            machine = input("Which one do you want to choose?\n")
            try:
                machine_number = int(machine)
                if not (1 <= machine_number <= len(target)):
                    raise ValueError 
            except ValueError:
                sys.exit("Invalid Target")
            select_name = list(target.keys())[machine_number - 1]
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
    name, ip, port, user, passwd = get_target_machine()
    
    client  = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    old_tty = termios.tcgetattr(sys.stdin)
    try:
        client.connect(ip, port=port, username=user, password=passwd)
        channel = client.get_transport().open_session()
        channel.get_pty(term="xterm", width=80, height=24)
        channel.invoke_shell()

        print('Connected to the target. Type "exit" to disconnect')
        
        tty.setraw(sys.stdin.fileno())

        while True:
            rlist, _, _ = select.select([channel, sys.stdin], [], [])
            if channel in rlist:
                data = channel.recv(4096)   
                if not data:
                    break
                sys.stdout.write(data.decode(errors="ignore"))
                sys.stdout.flush()
            if sys.stdin in rlist:
                cmd = os.read(sys.stdin.fileno(), 1024)
                if not cmd:
                    print("\nDisconnected")
                    break
                channel.send(cmd)
    except KeyboardInterrupt:
        channel.send("\x03")
    except Exception as e:
        sys.exit(f"Connection Failed: {e}")
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_tty)
        client.close()

if __name__ == "__main__":
    main()