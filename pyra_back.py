#!python
from argparse import ArgumentParser
from checksumdir import dirhash
from datetime import datetime
from filecmp import dircmp
from getpass import getuser
from pathlib import Path
from prompt_toolkit import prompt
import shutil
import subprocess
import os
import sys


def clean_backup(backup_dir, card_dir):
    '''Clean out files that only exist in the backup '''
    comp = dircmp(backup_dir, card_dir)
    backup_files = [f for f in os.listdir(backup_dir) if not f.startswith('.')]
    print(backup_files)
    for b_file in backup_files:
        if b_file not in comp.common:
            print("Deleting: {}".format(b_file))
            os.remove(os.path.join(backup_dir, b_file))


def generate_manifest(pyra_path, pyra_dirs, manifest_dest=None):
    timestamp = datetime.now().strftime("%d/%m/%Y:%H:%M:%S")
    output = ""
    for pyra_dir in pyra_dirs:
        pyra_card = os.path.join(pyra_path, pyra_dir)
        if os.path.exists(pyra_card):
            md5 = dirhash(pyra_card)
            output += "{} {} {}\n".format(pyra_dir, md5, timestamp)
    if manifest_dest:
        manifest_path = os.path.join(manifest_dest, 'MANIFEST')
    else:
        manifest_path = os.path.join(pyra_path, 'MANIFEST')
    print("Writing manifest to: {}".format(manifest_path))
    with open(manifest_path, 'w') as manifest:
        manifest.write(output)


def get_manifest_dict(pyra_path):
    manifest = {}
    try:
        with open(os.path.join(pyra_path, 'MANIFEST')) as manifest_file:
            for line in manifest_file.readlines():
                p_dir, md, md_time = line.split(' ')
                manifest[p_dir] = (md, md_time.strip())
        return manifest
    except Exception:
        return {}


def git_has_local_changes(backup_path, pyra_dir, card_timestamp):
    log_cmd = "git -C {} log -1 -- {} | head -n1".format(backup_path, pyra_dir)
    log_proc = subprocess.run(log_cmd, capture_output=True, shell=True)
    commit = log_proc.stdout.decode('UTF-8').split(' ')[-1].strip()
    show_cmd = "git -C {} show -s --format=%ci {}".format(backup_path, commit)
    show_proc = subprocess.run(show_cmd, capture_output=True, shell=True)
    commit_time = show_proc.stdout.decode('UTF-8').strip()
    # Trim off git's time zone since that's not yet supported.
    commit_time = " ".join(commit_time.split(' ')[0:2])
    card_dt = datetime.strptime(card_timestamp, "%d/%m/%Y:%H:%M:%S")
    git_dt = datetime.strptime(commit_time, "%Y-%m-%d %H:%M:%S")
    if git_dt <= card_dt:
        return False
    print("git has local changes for {}".format(pyra_dir))
    return True


def eval_and_copy(backup_path, pyra_path, pyra_dir):
    # XXX - if we have multiple cards where the same track may be
    # changing, we need to verify that the card is newer more robustly
    # than simply the hashes don't match.  If the hashes don't match
    # we know that there's a difference, but not necessarily that the
    # card is newer.
    # The new scheme will be that we will write manifests on the card
    # and if this manifest is out of date, then we know the track has
    # been modified on the card.
    # We'll also include a datestamp in the manifest and verify this
    # against the repository.  If the most recent commit for a song
    # is newer than the datestamp in the manifest, then we know that
    # what's on the card and what's on disk have a merge conflict.
    pyra_backup = os.path.join(backup_path, pyra_dir)
    pyra_card = os.path.join(pyra_path, pyra_dir)

    manifest = get_manifest_dict(pyra_path)
    p_pash = dirhash(pyra_card)
    mods = False
    backup_changes = False
    if pyra_dir not in manifest:
        print("{} appears to be new to the card, doing nothing...".format(pyra_dir))
        return False

    elif manifest[pyra_dir][0] != p_pash:
        print("Modifications on memory card for {}".format(pyra_dir))
        # We know there's something on the card worth saving,
        # now let's see if it's safe to copy to the git repository
        mods = True

    if git_has_local_changes(backup_path, pyra_dir, manifest[pyra_dir][1]):
        backup_changes = True

    copy = False
    if backup_changes and not mods:
        print("Backup repository has changes not on card")
        ans = prompt("Would you like to sync these changes to the card? (y/n)")
        if ans.lower() == 'y':
            print("Copying {} from backup to card".format(pyra_dir))
            shutil.rmtree(pyra_card, ignore_errors=True)
            shutil.copytree(pyra_backup, pyra_card)

    elif backup_changes and mods:
        # TODO - WARNING
        print("backup repo and card have diverged.  This means there are")
        print("unique changes in your backup and unique changes to your card.")
        print("\n\nYour selection here may DESTROY data FOREVER.")
        print("1. Copy the contents of the card OVER the backup")
        print("2. Copy the contents of the backup OVER the card")
        print("3. Do nothing - resolve this yourself")
        ans = prompt("Select your choice (1, 2, 3): ")
        if ans == "1":
            copy = True
        elif ans == "2":
            print("Copying {} from backup to card".format(pyra_dir))
            shutil.rmtree(pyra_card, ignore_errors=True)
            shutil.copytree(pyra_backup, pyra_card)
        else:
            print("Doing nothing - backups not made for {}".format(pyra_dir))

    elif mods and not backup_changes:
        print("{} on the card is newer, copying...".format(pyra_card))
        copy = True

    elif not mods and not backup_changes:
        print("{}: new changes not detected on card".format(pyra_card))

    if copy:
        shutil.copytree(pyra_card, pyra_backup, dirs_exist_ok=True)
        clean_backup(pyra_backup, pyra_card)
        return True
    return False


def copy_from_card(backup_path, pyra_path, pyra_dirs):
    # For now we'll only backup the PYRA directories and not the txt files
    backup_dirs = [d for d in os.listdir(backup_path) if "PYRA" in d]
    repo_changes = False
    for pyra_dir in pyra_dirs:
        if pyra_dir not in backup_dirs:
            pyra_backup = os.path.join(backup_path, pyra_dir)
            pyra_card = os.path.join(pyra_path, pyra_dir)
            print("{} not found: new backup".format(pyra_dir))
            shutil.copytree(pyra_card, pyra_backup, dirs_exist_ok=True)
            new = True
        else:
            new = eval_and_copy(backup_path, pyra_path, pyra_dir)
        repo_changes = repo_changes or new
    return repo_changes


def checkin_to_git(backup_path):
    try:
        print("Commiting changes to git...")
        cwd = os.getcwd()
        os.chdir(backup_path)
        res = subprocess.run(['git', 'add', '-A'])
        res.check_returncode()
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        cmt_msg = "Backup on {}".format(timestamp)
        res = subprocess.run(['git', 'commit', '-m', cmt_msg],
                             capture_output=True)
        res.check_returncode()
        print(res.stdout.decode('UTF-8'))
        print("Changes committed, pushing...")
        res = subprocess.run(['git', 'push'], capture_output=True)
        res.check_returncode()
        print(res.stdout.decode('UTF-8'))
        print("Done!")

    except Exception:
        print("Looks like there was a problem running git commands")
        print("Check the git repo cause shits weird.")
        print(res.stdout.decode('UTF-8'))
        import traceback
        print(traceback.format_exc())

    finally:
        os.chdir(cwd)


def main():
    user = getuser()

    parser = ArgumentParser()
    parser.add_argument("--backup-folder",
                        help="Your pyra backup folder",
                        default="/Users/{}/Desktop/pyra_back".format(user),
                        dest="backup_path")

    parser.add_argument("--pyra-card",
                        help="Path to pyra card",
                        dest="pyra_path")

    args = parser.parse_args()
    if not args.pyra_path:
        print("You need to supply a path to the pyra sd card")
        parser.print_help()
        sys.exit(1)

    backup_path = Path(args.backup_path)
    pyra_path = Path(args.pyra_path)

    # TODO - setup the git repo?
    if not os.path.exists(os.path.join(backup_path, '.git')):
        print("Please setup a git repository at {} and try again".args.backup_path)
        sys.exit(1)

    if not os.path.exists(args.pyra_path):
        print("Card not present at {}".format(pyra_path))
        sys.exit(1)
    else:
        files = os.listdir(pyra_path)
        pyra_dirs = [d for d in files if 'PYRA' in d]
        if not pyra_dirs:
            print("No pyramid directories found on the card")
            sys.exit(1)

    manifest_path = os.path.join(pyra_path, 'MANIFEST')
    if not os.path.exists(manifest_path):
        print("MANIFEST not found on card, generating from git")
        generate_manifest(backup_path, pyra_dirs, manifest_dest=pyra_path)

    new = copy_from_card(backup_path, pyra_path, pyra_dirs)

    if new:
        checkin_to_git(backup_path)

    # It's always okay to make the card manifest up to date.
    generate_manifest(pyra_path, pyra_dirs)


if __name__ == "__main__":
    main()
