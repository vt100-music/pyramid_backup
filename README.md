Welcome to the Squarp Pyramid Backup Utility

The Squarp Pyramid is a MIDI sequencer and stores midi songs and song settings on an SD card.  SD cards can break, get lost, who knows - so backups are important.  Of course a simple solution is simply to copy your card to your computer once in a while - and this is what I did for quite some time.  This works if you don't mind managing the revisions yourself (or don't store revisions) and if you have a single memory card.  After a couple of years this got unwieldy as I had a large number of folders.  Then, to make matters more interesting, I started working with multiple SD cards to work around some of the limitation in the Pyramid.  This left me in a situation where I was trying to copy the contents of two different cards into a directory with lots of other directories in it.  Ugh.

Instead I decided to consolidate into a single historical repoistory to simplify the historical element of my backups - for this I used git.  Then, to manage the incoming data from multiple cards, I wrote this script.  If you have complex backup needs because you write that much music, maybe this script will be helpful.

The idea is simple:
   * Setup a git repositorya with some cloud backup - I used github
   * Stick your card in your sd card reader
   * Run this script
   
I've only run this on my iMac though this should work in linux.  I doubt it will work in windows and I'm not going to make it work in windows :)

To run the script, you must have python 3.8 or newer cause I'm a jerk and used new features:

:: Script Features ::
   * Copies new and modified songs to your git repository and submits them to git
   * Multi Card Support
   ** Detects and warns about divergence (same song, different edits on multiple cards)
   ** Detects if the repository was updated but not a card (you updates a song on one card but not another card)

Note on Divergence:  Divergence is a tricky situation where you have multiple valid changes to a set of files.  In the case of the Pyramid, this means that you author and save modifications to the same song on several card.  If this was source code, we have ways of merging the two changes together, however there's no way to merge core files (yet) and I'm also not about to try to figure out midi merge -- this effectively means that your options are limited if this situation arises.  With pyraback you can choose to override either the card or the backup with the song revision of your choosing.  However, if you truly want to merge the changes from the two (or more) edits of a track, you'll have to do this manually on the Pyramid.

Installation requirements:
   * python 3
   * virtualenv  (pip install virtualenv from your python 3 host env)

Running the script:
   * git clone https://github.com/vt100-music/pyramid_backup.git
   * cd to pyramaid_backup
   * ./setup.sh  (this will setup and enter the runtime env)
   * Run the script

carl@Protocol-C pyramid_backup % python pyra_back.py -h
usage: pyra_back.py [-h] [--backup-folder BACKUP_PATH] [--pyra-card PYRA_PATH]

optional arguments:
  -h, --help            show this help message and exit
  --backup-folder BACKUP_PATH
                        Your pyra backup folder
  --pyra-card PYRA_PATH
                        Path to pyra card
                        
Example:

(venv) carl@Protocol-C pyramid_backup % ./pyra_back.py --backup-folder /Users/carl/Desktop/pyra_back --pyra-card /Volumes/PYRAMID_NEW

PYRA_150_3 appears to be new to the card, doing nothing...
PYRA_150_4 appears to be new to the card, doing nothing...


