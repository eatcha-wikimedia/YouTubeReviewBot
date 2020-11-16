import  pywikibot
from datetime import datetime
import emoji
import re
from collections import OrderedDict

SITE = pywikibot.Site()

#https://github.com/toolforge/video2commons/blob/a2cb6c3212f3230e0fd134f97ac71de23dfaa9ca/video2commons/frontend/urlextract.py#L227
sanitationRules = [
    # issue #101
    {
        'pattern': emoji.get_emoji_regexp(),
        'replace': ''
    },
    # "signature"
    {
        'pattern': re.compile(r'~{3}'),
        'replace': ''
    },
    # Space, underscore, tab, NBSP and other unusual spaces
    {
        'pattern': re.compile(r'[ _\u0009\u00A0\u1680\u180E\u2000-\u200A'
                              r'\u2028\u2029\u202F\u205F\u3000\s]+'),
        'replace': ' '
    },
    # issue #96
    {
        'pattern': re.compile(r'\u200B'),
        'replace': ''
    },
    # unicode bidi override characters: Implicit, Embeds, Overrides
    {
        'pattern': re.compile(r'[\u200E\u200F\u202A-\u202E]'),
        'replace': ''
    },
    # control characters
    {
        'pattern': re.compile(r'[\x00-\x1f\x7f]'),
        'replace': ''
    },
    # URL encoding (possibly)
    {
        'pattern': re.compile(r'%([0-9A-Fa-f]{2})'),
        'replace': r'% \1'
    },
    # HTML-character-entities
    {
        'pattern': re.compile(r'&(([A-Za-z0-9\x80-\xff]+|'
                              r'#[0-9]+|#x[0-9A-Fa-f]+);)'),
        'replace': r'& \1'
    },
    # slash, colon (not supported by file systems like NTFS/Windows,
    # Mac OS 9 [:], ext4 [/])
    {
        'pattern': re.compile(r'[:/#]'),
        'replace': '-'
    },
    # brackets, greater than
    {
        'pattern': re.compile(r'[\]\}>]'),
        'replace': ')'
    },
    # brackets, lower than
    {
        'pattern': re.compile(r'[\[\{<]'),
        'replace': '('
    },
    # directory structures
    {
        'pattern': re.compile(r'^(\.|\.\.|\./.*|\.\./.*|.*/\./.*|'
                              r'.*/\.\./.*|.*/\.|.*/\.\.)$'),
        'replace': ''
    },
    # everything that wasn't covered yet
    {
        'pattern': re.compile(r'[|#+?:/\\\u0000-\u001f\u007f]'),
        'replace': '-'
    },
    # titleblacklist-custom-double-apostrophe
    {
        'pattern': re.compile(r"'{2,}"),
        'replace': '"'
    },
]

def escape_wikitext(wikitext):
    """Escape wikitext for use in file description."""
    rep = OrderedDict([
        ('{|', '{{(}}&#124;'),
        ('|}', '&#124;{{)}}'),
        ('||', '&#124;&#124;'),
        ('|', '&#124;'),
        ('[[', '{{!((}}'),
        (']]', '{{))!}}'),
        ('{{', '{{((}}'),
        ('}}', '{{))}}'),
        ('{', '{{(}}'),
        ('}', '{{)}}'),
    ])
    rep = dict((re.escape(k), v) for k, v in rep.items())
    pattern = re.compile("|".join(rep.keys()))
    return pattern.sub(lambda m: rep[re.escape(m.group(0))], wikitext)

def sanitize(filename):
    """Sanitize a filename for uploading."""
    for rule in sanitationRules:
        filename = rule['pattern'].sub(rule['replace'], filename)

    return filename


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
