#!/usr/bin/env python3

import shutil
import sqlite3
import os
import sys
import getopt
from datetime import datetime
from subprocess import Popen, PIPE
from hashlib import sha1

input_db = None
dest = None
comp_sha = True
rotate = False


def show_usage():
    print(
        """
Usage:""",
        sys.argv[0],
        """
    -i      Input Shotwell Database (required)
    -d      Destination to copy events (required)
    -r      Rotate source photos in place. Off by default. Requires
            'exiftran' to be installed. Will slow down process.
    -f      Compare by filename rather than sha1 of header (sha1 is slower + default)
    -h      Show this help
""",
    )


def parse_args():
    global input_db
    global dest
    global rotate
    global comp_sha

    input_db_set = False
    dest_set = False

    try:
        opts, args = getopt.getopt(sys.argv[1:], "i:d:rfh")
    except getopt.GetoptError:
        show_usage()
        sys.exit(10)

    for o, a in opts:
        if o == "-i":
            input_db_set = True
            input_db = a
        elif o == "-d":
            dest_set = True
            dest = a
        elif o == "-h":
            show_usage()
            exit(0)
        elif o == "-f":
            comp_sha = False
        elif o == "-r":
            rotate = True

    if not input_db_set or not dest_set:
        print("Missing options")
        show_usage()
        exit(10)


def shafile(filename):
    try:
        with open(filename, "rb") as f:
            return sha1(f.read()).hexdigest()
    # Could just sha header...
    # return sha1(f.read(512)).hexdigest()
    except IOError:
        return 0


def main():

    parse_args()

    print("Going to output to", dest)
    print("Going to read database from", input_db)
    print("Rotation of source photos? ", rotate)
    print("Compare files by sha1? ", comp_sha)

    conn = sqlite3.connect(input_db)
    crs = conn.cursor()
    crs.execute("SELECT id, name FROM EventTable")
    for row in crs:
        if row[1] is not None:

            print("======================")
            print(f"Dealing with event '{row[1]}'")
            timestamp_crs = conn.cursor()
            timestamp_crs.execute(
                """
                SELECT exposure_time
                FROM PhotoTable
                WHERE event_id=? AND exposure_time IS NOT NULL
                ORDER BY exposure_time LIMIT 1
                """,
                (row[0],),
            )
            try:
                event_ym = datetime.fromtimestamp(
                    timestamp_crs.fetchall()[0][0]
                ).strftime("%Y-%m")
                print(f"Identified event date '{event_ym}'")
            except IndexError:
                print("Seems no files present in DB that match this event; skipped")
                continue
            event_dir = (
                dest + os.sep + event_ym + "_" + row[1].replace(os.sep, "_")
            )  # in case of seps in the string
            if not os.path.exists(event_dir):
                print(f"Creating '{event_dir}'")
                os.makedirs(event_dir)
            photo_crs = conn.cursor()
            photo_crs.execute(
                """
                SELECT filename, BackingPhotoTable.filepath AS jpg_filename
                FROM PhotoTable
                LEFT OUTER JOIN BackingPhotoTable
                ON BackingPhotoTable.id = PhotoTable.develop_camera_id
                WHERE event_id=?
                """,
                (row[0],),
            )
            copy_cnt = 0
            exist_cnt = 0
            copy_paths = []
            for photo in photo_crs:
                sourcefile = photo[0]

                if rotate:
                    Popen(
                        ("exiftran", "-a", "-i", "-p", sourcefile),
                        stdout=PIPE,
                        stderr=PIPE,
                    ).communicate()

                # special treatment for RAW that contain linked developed files
                if photo[1]:
                    # add "RAW/" subdirectory name to target file path
                    raw_subdir = event_dir + os.sep + "RAW"
                    if not os.path.exists(raw_subdir):
                        print(f"Creating {raw_subdir}")
                        os.makedirs(raw_subdir)
                    filename = raw_subdir + os.sep + os.path.basename(sourcefile)
                    # check if same-named JPEG exists, and add to copy list if so
                    jpeg_suspect = photo[1]
                    if os.path.exists(jpeg_suspect):
                        jpeg_filename = (
                            event_dir + os.sep + os.path.basename(jpeg_suspect)
                        )
                        copy_paths.append((jpeg_suspect, jpeg_filename))
                else:
                    filename = event_dir + os.sep + os.path.basename(sourcefile)
                copy_paths.append((sourcefile, filename))

            for sourcefile, targetfile in copy_paths:
                copy_needed = False
                if comp_sha:
                    copy_needed = not os.path.exists(targetfile) or shafile(
                        targetfile
                    ) != shafile(sourcefile)
                else:
                    copy_needed = not os.path.exists(targetfile)

                if copy_needed:
                    sys.stdout.write(".")
                    sys.stdout.flush()

                    shutil.copyfile(sourcefile, targetfile)
                    copy_cnt = copy_cnt + 1
                else:
                    sys.stdout.write("e")
                    sys.stdout.flush()
                    exist_cnt = exist_cnt + 1

            print(
                f"\nCopied {copy_cnt} files. (Ignored {exist_cnt} files as they already existed)"
            )

    # Finally, delete empty dirs to tidy up (caused by old events in DB)
    for name in os.listdir(dest):
        if os.path.isdir(name) and len(os.listdir(name)) == 0:
            os.rmdir(name)


if __name__ == "__main__":
    main()
