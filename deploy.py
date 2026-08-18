import os
import tarfile
import paramiko
from scp import SCPClient

# ================= CONFIG =================
PEM_FILE = r"C:\Users\chawl\Desktop\PRESENT\Interhips\C4GT-The Apprentice Project\Deployment\tap-ai-videos"
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
ARCHIVE_NAME = "translation.tar.gz"

REMOTE_USER = "tap-vid"
REMOTE_HOST = "34.148.172.114"
REMOTE_PATH = "/home/tap-vid"

EXCLUDES = [
    ".git", 
    "node_modules", 
    ".next", 
    "temp", 
    "tmp", 
    "logs", 
    "downloads", 
    ".playwright-cli", 
    ".venv",
    ".env.local",
    "dist",
    "__pycache__"
]
# ==========================================


def create_archive():
    print("Creating project archive...")

    parent_dir = os.path.dirname(PROJECT_DIR)
    archive_path = os.path.join(parent_dir, ARCHIVE_NAME)

    with tarfile.open(archive_path, "w:gz") as tar:
        for root, dirs, files in os.walk(PROJECT_DIR):
            # Exclude folders
            dirs[:] = [d for d in dirs if d not in EXCLUDES and not d.startswith("__")]

            # Determine relative path from project root
            rel_dir = os.path.relpath(root, PROJECT_DIR)

            for file in files:
                # Skip OS specific or cached files
                if file.startswith(".DS_Store") or file.endswith(".pyc"):
                    continue

                full_path = os.path.join(root, file)
                arcname = os.path.relpath(full_path, PROJECT_DIR)
                tar.add(full_path, arcname=arcname)

    print("Archive created")
    return archive_path


def create_ssh():
    key = None
    errors = []
    
    for key_class in [paramiko.RSAKey, paramiko.Ed25519Key, paramiko.ECDSAKey, paramiko.DSSKey]:
        try:
            key = key_class.from_private_key_file(PEM_FILE)
            break
        except Exception as e:
            errors.append(f"{key_class.__name__}: {str(e)}")
            
    if not key:
        raise Exception("Failed to load SSH private key. Errors:\n" + "\n".join(errors))

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    ssh.connect(
        hostname=REMOTE_HOST,
        username=REMOTE_USER,
        pkey=key
    )

    return ssh


def upload(ssh, file_path):
    print("Uploading to VM...")

    with SCPClient(ssh.get_transport()) as scp:
        scp.put(file_path, REMOTE_PATH)
        
        # Upload local .env to the VM (prioritize production keys)
        prod_env = os.path.join(PROJECT_DIR, ".env")
        local_env = os.path.join(PROJECT_DIR, ".env.local")
        
        if os.path.exists(prod_env):
            print("Found local .env (Live Keys). Uploading to VM as /home/tap-vid/.env...")
            scp.put(prod_env, "/home/tap-vid/.env")
        elif os.path.exists(local_env):
            print("WARNING: No .env found. Falling back to .env.local...")
            scp.put(local_env, "/home/tap-vid/.env")

    print("Upload complete")


def deploy(ssh):
    print("Running deployment tasks on VM...")

    commands = """
    set -e

    BASE_DIR=/home/tap-vid
    ARCHIVE=$BASE_DIR/translation.tar.gz

    echo "Creating deployment folder..."
    DEPLOY_DIR=$BASE_DIR/deploy_translation_$(date +%s)
    mkdir -p $DEPLOY_DIR

    echo "Extracting archive..."
    tar -xzf $ARCHIVE -C $DEPLOY_DIR

    cd $DEPLOY_DIR

    echo "Removing local .env.local if present..."
    rm -f .env.local

    echo "Linking production .env file from home directory..."
    # The production .env must exist in /home/tap-vid/.env
    ln -sf $BASE_DIR/.env $DEPLOY_DIR/.env
    # Sync backend .env as well
    ln -sf $BASE_DIR/.env $DEPLOY_DIR/backend/.env

    echo "Building and running Docker Containers..."
    # Run Docker Compose with project name 'video-translation' to update existing stack
    sudo docker compose -p video-translation -f compose.yaml -f compose.production.yaml up -d --build

    echo "Cleaning up dangling docker images to free disk space..."
    sudo docker image prune -f

    echo "Cleaning up older deploy folders (keeping latest 3)..."
    cd $BASE_DIR
    ls -dt deploy_translation_* | tail -n +4 | xargs rm -rf 2>/dev/null || true

    echo "Deployment Successful!"
    """

    stdin, stdout, stderr = ssh.exec_command(commands)

    for line in stdout:
        try:
            print(line.strip())
        except UnicodeEncodeError:
            try:
                sys.stdout.buffer.write(line.encode(sys.stdout.encoding or 'cp1252', errors='replace'))
                sys.stdout.buffer.write(b'\n')
                sys.stdout.flush()
            except Exception:
                pass

    err = stderr.read().decode('utf-8', errors='ignore')
    if err:
        try:
            print("Warnings/Output:", err)
        except UnicodeEncodeError:
            try:
                sys.stdout.buffer.write(b"Warnings/Output: " + err.encode(sys.stdout.encoding or 'cp1252', errors='replace') + b"\n")
                sys.stdout.flush()
            except Exception:
                pass


def main():
    try:
        archive = create_archive()
        ssh = create_ssh()
        upload(ssh, archive)
        deploy(ssh)
        ssh.close()

        # Clean up local archive
        if os.path.exists(archive):
            os.remove(archive)

        print("Deployment completed successfully!")

    except Exception as e:
        print("Failed:", str(e))


if __name__ == "__main__":
    main()
