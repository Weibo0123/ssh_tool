import paramiko
import getpass
import sys

def get_target_machine():
    target_name = input("Target Name: ")
    target_ip = input("Target IP: ")
    try:
        target_port = int(input("Port: "))
    except ValueError:
        sys.exit("Invalid Port")
    target_user = input("Username: ")
    passwd = getpass.getpass()
    return target_name, target_ip, target_port, target_user, passwd


def main():
    name, ip, port, user, passwd = get_target_machine()
    cmd = input("Command: ")

    client  = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(ip, port=port, username=user, password=passwd)
        _, stdout, stderr = client.exec_command(cmd)
        output = stdout.readlines() + stderr.readlines()
        if output:
            print("=== Output ===")
            for line in output:
                print(line.strip())
    except Exception as e:
        sys.exit(f"Connection Failed: {e}")

    client.close()

if __name__ == "__main__":
    main()