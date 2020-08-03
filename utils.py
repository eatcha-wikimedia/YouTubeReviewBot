import  pywikibot
from datetime import datetime
SITE = pywikibot.Site()


def uploader(filename, link=True):
    """User that uploaded the file."""
    history = (pywikibot.Page(SITE, filename)).revisions(reverse=True, total=1)
    for info in history:
        username = (info.user)
    if not history:
        return "Unknown"
    if link:
        return "[[User:%s|%s]]" % (username, username)
    return username

def last_edit_time(file_name):
    """Recent most editor for file."""
    for info in (pywikibot.Page(SITE, file_name)).revisions(reverse=False, total=1):
        return datetime.strptime(str(info.timestamp), "%Y-%m-%dT%H:%M:%SZ")

def informatdate():
    """Current date in yyyy-mm-dd format."""
    return (datetime.utcnow()).strftime("%Y-%m-%d")

def IsMarkedForDeletion(pagetext):
    """Determine if the file is marked for deletion."""
    LowerCasePageText = pagetext.lower()
    if (
        (LowerCasePageText.find('{{No permission since') != -1) or
        (LowerCasePageText.find('{{delete') != -1) or
        (LowerCasePageText.find('{{copyvio') != -1) or
        (LowerCasePageText.find('{{speedy') != -1)
        ):
            return True

def DetectSite(source_area):
    """Identify the source website of the file."""
    if (source_area.find('{{from vimeo') != -1):
        return "Vimeo"
    elif (source_area.find('{{from youtube') != -1):
        return "YouTube"
    elif (source_area.find('videowiki.wmflabs.org') != -1):
        return "VideoWiki"
    elif (source_area.find('flickr.com/photos') != -1):
        return "Flickr"
    elif (source_area.find('vimeo.com') != -1):
        return "Vimeo"
    elif (source_area.find('youtube.com') != -1):
        return "YouTube"

def check_channel(ChannelId):
    """Check if the channel is trusted or bad."""
    if ChannelId in (pywikibot.Page(SITE, "User:YouTubeReviewBot/Trusted")).get(get_redirect=True, force=True):
        return "Trusted"
    elif ChannelId in (pywikibot.Page(SITE, "User:YouTubeReviewBot/bad-authors")).get(get_redirect=True, force=True):
        return "Bad"
    return "Normal"

def OwnWork(pagetext):
    """Check if own work by uploader."""
    LowerCasePageText = pagetext.lower()
    if (LowerCasePageText.find('{{own}}') != -1):
        return True
    elif (LowerCasePageText.find('own work') != -1):
        return True
    return False

def display_video_info(VideoId, ChannelId, VideoTitle, ArchiveUrl, ChannelName="Not Applicable"):
    out(
        str(
            "video Id : " + VideoId +
            "\nChannel Name : " + ChannelName +
            "\nChannel Id : " + ChannelId +
            "\nVideo Title : " + VideoTitle +
            "\nArchive : " + ArchiveUrl +
            "\nDate : " + informatdate()),
            color="white",
            )

def out(text, newline=True, date=False, color=None):
    """Just output some text to the consoloe or log."""
    if color:
        text = "\03{%s}%s\03{default}" % (color, text)
    dstr = (
        "%s: " % datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        if date
        else ""
    )
    pywikibot.stdout("%s%s" % (dstr, text), newline=newline)
