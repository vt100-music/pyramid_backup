#!python

from argparse import ArgumentParser
from checksumdir import dirhash
from datetime import datetime
from filecmp import dircmp
from getpass import getuser
from pathlib import Path
import shutil
import subprocess
import os
import sys


def match_sha1(dir1, dir2):
    dir1_sha = dirhash(dir1, 'md5')
    dir2_sha = dirhash(dir2, 'md5')
    if dir1_sha == dir2_sha:
        return True
    return False


def clean_backup(backup_dir, card_dir):
    '''Clean out files that only exist in the backup '''
    comp = dircmp(backup_dir, card_dir)
    backup_files = [f for f in os.listdir(backup_dir) if not f.startswith('.')]
    print(backup_files)
    for b_file in backup_files:
        if b_file not in comp.common:
            print("Deleting: {}".format(b_file))
            os.remove(os.path.join(backup_dir, b_file))


def copy_from_card(backup_path, pyra_dirs):
    # For now we'll only backup the PYRA directories and not the txt files
    backup_dirs = [d for d in os.listdir(backup_path) if "PYRA" in d]
    new = False
    for pyra_dir in pyra_dirs:
        pyra_backup = os.path.join(backup_path, pyra_dir)
        pyra_card = os.path.join(pyra_path, pyra_dir)
        if pyra_dir not in backup_dirs:
            print("{} not found: new backup".format(pyra_dir))
            shutil.copytree(pyra_card, pyra_backup, dirs_exist_ok=True)
            new = True
        else:
            if not match_sha1(pyra_backup, pyra_card):
                print("{} on the card is newer, copying...".format(pyra_card))
                shutil.copytree(pyra_card, pyra_backup, dirs_exist_ok=True)
                clean_backup(pyra_backup, pyra_card)
                new = True

            else:
                print("{} checksums match".format(pyra_card))
    return new


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

    new = copy_from_card(backup_path, pyra_dirs)

    if new:
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


if __name__ == "__main__":
    main()
