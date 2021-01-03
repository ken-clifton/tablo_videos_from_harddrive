# Python3 Program Name: extract_videos_from_tablo_hard_drive.py
# Written by: Ken Clifton
# Web site: https://kenclifton.com
# Date Written: 1/2/2021
# Purpose:
# Python script to extract videos from tablo hard disk and
# concatenate .ts video files into a .MP4 file named with the recording ID
# Must Change the variables:
#   tablo_harddrive_mountpoint
#   video_folder_ID
#
# see the sample tablo database queries below to find the 
# recording ID which is the: video_folder_ID
# NOTE: the SQL queries are different for early tablo firmware versus later...
# to find ID (the recording folder name) use SQL query in DB Browser with Tablo.db opened as follows:
'''
-- old 2.2.6 fw database sql query (can use DB Browser software to run)
select title, episodeTitle, length(startTime), json, ID
from Metadata
WHERE
recordingID > 0
and length(startTime) > 0 
order by title
'''
'''
--NEWER 2.2.230 fw database sql query (can use DB Browser software to run)
select ID, title, json, recommendations, episodeTitle  
from Recording
WHERE
recordingID > 0
and length(DateDeleted) < 1
order by title
'''
#------------------------------------------------------------
import json
import pathlib
import subprocess

# Define the mount point of the tablo hard drive, ie. the long text a49a...
# On Ubuntu right-click hard-drive icon and properties, or use Disks tool
tablo_harddrive_mountpoint = "/media/clifton/a49a30f0-ebc3-4e53-b467-78bde47a99d1"

# change the following to the ID of the recording from the tablo.db
# this is found using DB Browser and SQL query as shown in comments above
video_folder_ID = "791164"

mount_path = pathlib.Path(tablo_harddrive_mountpoint)

# make the full recording path by adding /rec , /recording_id, "/segs"
recording_path = mount_path.joinpath( "rec", video_folder_ID, "segs")

def probe(video_file_path):
    ''' Give a json from ffprobe command line

    @video_file_path : The absolute (full) path of the video file, string.
    '''
    if type(video_file_path) != str:
        raise Exception('Give ffprobe a full file path of the video')
        return

    command = ["ffprobe",
            "-loglevel",  "quiet",
            "-print_format", "json",
             "-show_format",
             "-show_streams",
             video_file_path
             ]

    pipe = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out, err = pipe.communicate()
    return json.loads(out)


def get_duration(video_file_path):
    ''' Video's duration in seconds, return a float number
    '''
    _json = probe(video_file_path)

    if 'format' in _json:
        if 'duration' in _json['format']:
            return float(_json['format']['duration'])

    if 'streams' in _json:
        # commonly stream 0 is the video
        for s in _json['streams']:
            if 'duration' in s:
                return float(s['duration'])

    # if everything didn't happen,
    # we got here because no single 'return' in the above happen.
    raise Exception('I found no duration')
    #return None

print("Starting processing of .ts files, this takes a while...")

# get list of files in directory
# recording_path is created near top of this program, just fyi...
sorted_file_list = list(anItem.name for anItem in recording_path.iterdir()  if anItem.is_file() )
# sort the files ascending
sorted_file_list.sort()

# temporary text file for all pieces of video built below then used with ffmpeg built in user's home folder
video_segments_textfile = pathlib.Path.home().joinpath( "video_seg_list.txt" )

# open the temporary outfile
outfile_pointer = open(video_segments_textfile, "w")

# loop through the list of sorted .ts files for the recording adding them to the temp textfile
for filename in sorted_file_list:
    # only add files with .ts extension
    if (filename.endswith(".ts")): 
        # build full .ts file path
        filename_and_path = recording_path.joinpath(filename)
        # write concat text file line 
        outfile_pointer.write(f"file '{filename_and_path}'\n")
        # get .ts file duration, but must subtract 1/2 second so no skipping in video
        duration = get_duration( str(filename_and_path) ) - 0.5
        # write concat text file duration line
        outfile_pointer.write(f"duration {duration:.1f}\n")
        print("Processed file:",  filename)
    else:
        continue
        
outfile_pointer.close()

print("Processing of .ts files completed successfully.")
print("Starting ffmpeg processing, this can take several minutes...")
print("The resulting MP4 video file will be placed in:", pathlib.Path.home().joinpath("Videos", (video_folder_ID + ".mp4")))

# run ffmpeg command to make concatenated video
command = ["ffmpeg",
"-f", "concat", 
"-safe", "0", 
"-i", video_segments_textfile,
"-c", "copy", 
"-bsf:a", "aac_adtstoasc",
"-movflags", "+faststart",
# place new video file in the user's profile home/videos folder with the id.mp4
"-y", pathlib.Path.home().joinpath("Videos", (video_folder_ID + ".mp4"))
]
pipe = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
out, err = pipe.communicate()
print("ffmpeg concatenation of files completed. Command results follow:")
print(out)

# remove the temp file
pathlib.Path(video_segments_textfile).unlink()
