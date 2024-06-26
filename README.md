# Export files from Shotwell DB to folders named \<YYYY\>-\<MM\>_\<EVENT\>

I want to re-organize my personal photo collection to be ordered by
events, with the (approximate) monthly date added to the directory
name:

    2020-12_Christmas
    2021-01_Birthday
    2021-01_NewYear
    ...

I use [Shotwell](https://wiki.gnome.org/Apps/Shotwell) to organize the
photos itself into events, then use this script to copy the then
sorted files to a output directory with the desired subdirectory
structure.

The script is forked from a [similar script](https://github.com/steprobe/Shotwell-Export-To-Events) by [Stephen Rogers](https://github.com/steprobe),
with the only additions that I added integration for the monthly string
in the target directory name, and handling of developed RAW files to my version.
All credits for the idea and implementation go to the original author, obviously.

Example:

    sw_export_to_event.py -i ~/.local/share/shotwelll/data/photo.db -d <output_directory>
