"""
Remote Shell

Descreption:
    This program allows users to securely connect to remote machines with SSH
    with a fully functional pseudo-terminal(PTY). It supports interactive
    command execution, live output, proper handling of Ctrl+C, automatic
    terminal restoration on exit, and it can also save target machines
    for quick reconnection.
"""
import paramiko
import getpass
import sys
import json
import os
import select
import tty
import termios
import ipaddress

TARGET_SAVE_FILE = "target_save.json"

# ========================================= Input Check ==========================================
def check_target(name, ip, port, user):
    """
    This function checks if the input are valid
    
    param name: Name of the target
    param ip: IP address of the target
    param port: The port that connect to 
    param user: The user name login with
    """

    # Check if the name is between 1 - 14 characters.
    if not (0 < len(name) <= 14):
        raise ValueError("Target name must be 1–14 characters")

    # Check if the ip address is in valid format.
    try:
        ipaddress.ip_address(ip)
    except ValueError:
        raise ValueError("Invalid IP address")

    # Chekc if the port is an integer and between 1 - 65535.
    try:
        port = int(port)
        if not (1 <= port <= 65535):
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError("Invalid port value")

    # Check is the user name is empty
    if not user:
        raise ValueError("Username cannot be empty")

    return name, ip, port, user
# ========================================= Input Check ==========================================


# ===================================== Target Machine Handling ======================================
def get_target_machine():
    """
    This function asks which target the user want to use.
    """

    # Ask if the user want to use the saved target
    choice = input("Do you want to use your save targets(y/n): ").lower()
    if choice in ("y", "yes", "ye"):
        # Call the load function to load the target that is already saved.
        target = load_target_machine()
        if target:
            # List all the number and name of the saved target
            for i, name in enumerate(target.keys(), start=1):
                print(f"{i}: {name}")
            machine = input("Which one do you want to choose?\n")
            # Check if the use's input is valid
            try:
                machine_number = int(machine)
                if not (1 <= machine_number <= len(target)):
                    raise ValueError 
            except ValueError:
                sys.exit("Invalid Target")
            machine_name = list(target.keys())[machine_number - 1]
            t = target[machine_name]
            # Call the input checking function to check if the inputs are valid
            check_target(machine_name, t["ip"], t["port"], t["user"])
            passwd = getpass.getpass()
            return machine_name, t["ip"], t["port"], t["user"], passwd
        else:
            sys.exit("You don't have any saved targets!")
    elif choice in ("n", "no"):
        target_name = input("Target Name: ").strip()
        target_ip = input("Target IP: ").strip()
        target_port = (input("Port: ").strip())
        target_user = input("Username: ").strip()
        check_target(target_name, target_ip, target_port, target_user)
        # Use the getpass so the password won't ne show in plain text.
        passwd = getpass.getpass() 
        # Call the save function so the user could save the target.
        save_target_machine(target_name, target_ip, target_port, target_user)
        return target_name, target_ip, target_port, target_user, passwd
    else:
        sys.exit("Invalid Input")
    

def save_target_machine(name, ip, port, user):
    """
    This function saves the target that user gives to the saving file
    
    param name: Name of the target
    param ip: IP address of the target
    param port: The port that connect to 
    param user: The user name login with
    """

    target = load_target_machine() or {}

    # If the name is already existed, ask user if they want to overwirte
    if name in target:
        confirm = input(f"target {name} is already existed. Do you want to overwrite?\n").lower()
        if confirm not in ("y", "yes"):
            sys.exit("Saving cancelled.")
    target[name] = {
        "ip": ip,
        "port": port,
        "user": user,
        }
    
    with open(TARGET_SAVE_FILE, "w") as f:
        json.dump(target, f, indent=4)
    print(f"Save Target Information to {TARGET_SAVE_FILE}")

def load_target_machine():
    """
    This function loads all the targets that saves in the saving file
    """

    # Check if the target saving file exisrs
    if not os.path.exists(TARGET_SAVE_FILE):
        sys.exit("The saving file doesn't exist")
        

    # If there's nothing in the saving file, pass.
    try:
        with open(TARGET_SAVE_FILE) as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    except json.JSONDecodeError:
        pass 

# ===================================== Target Machine Handling ======================================


# ====================================== SSH Sessions Handling =======================================
def ssh_session(ip, port, user, passwd):
    """
    This function handles the ssh connection.
    
    param name: Name of the target
    param ip: IP address of the target
    param port: The port that connect to 
    param user: The user name login with
    """
    
    # Create a new SSH client
    client  = paramiko.SSHClient()

    # Automatically accept and trust unknown ssh host
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    # Save the current terminal setting
    old_tty = termios.tcgetattr(sys.stdin)
    try:
        # Connect to the SSH target
        client.connect(ip, port=port, username=user, password=passwd)
        # Open a new SSH session channel
        channel = client.get_transport().open_session()
        # Request a pseudo-terminal(pty)
        channel.get_pty(term="xterm", width=80, height=24)
        # Start an interactive shell on the ssh channel
        channel.invoke_shell()

        print('Connected to the target. Type "exit" to disconnect')
        
        # Set the terminal to raw mode so the input send directly to the target 
        tty.setraw(sys.stdin.fileno())

        # Keep reading from the SSH channel output and user input and display the whichever recieve earlier
        while True:
            # Wait untile either the SSH channel or the user input is ready for reading.
            rlist, _, _ = select.select([channel, sys.stdin], [], [])
            # If the channel has the data, read up to 4096 bytes
            if channel in rlist:
                data = channel.recv(4096)   
                # Exit the loop if the channel close
                if not data:
                    break
                # Decode the data recieved and show them in the terminal
                sys.stdout.write(data.decode(errors="ignore"))
                # Flush the the output to ensure it appears once the program have it
                sys.stdout.flush()
            # If the user types the input, read up to 1024 bytes
            if sys.stdin in rlist:
                cmd = os.read(sys.stdin.fileno(), 1024)
                # Exit the loop if no input recieved
                if not cmd:
                    print("\nDisconnected")
                    break
                # Send the user input to the remote
                channel.send(cmd)
    except KeyboardInterrupt:
        channel.send("\x03")
    except Exception as e:
        sys.exit(f"Connection Failed: {e}")
    finally:
        # Restore the terminal setting
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_tty)
        # Close the SSH connection
        client.close()
# ====================================== SSH Sessions Handling =======================================


# ============================================== Main ================================================
def main():
    name, ip, port, user, passwd = get_target_machine()
    ssh_session(ip, port, user, passwd)

if __name__ == "__main__":
    main()
# ============================================== Main ================================================