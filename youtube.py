import waybackpy
from datetime import datetime
import re
import html as htm
import requests
from utils import out


def clean_html(html):
    """Clean an HTML snippet into a readable string"""
    # copied from youtube-dl source - youtube extractor with. I made some changes though.

    if html is None:  # Convenience for sanitizing descriptions etc.
        return html

    html = htm.unescape(html)
    html = re.sub(r"\\n", "\n", html)
    html = html.replace("\\u0026", "&")
    html = re.sub(r'(?u)\s*<\s*br\s*/?\s*>\s*', '\n', html)
    html = re.sub(r'(?u)<\s*/\s*p\s*>\s*<\s*p[^>]*>', '\n', html)
    # Strip html tags
    html = re.sub('<.*?>', '', html)

    return html.strip()

def format_time(millis):
    millis = int(millis)
    seconds=int((millis/1000)%60)
    minutes=int((millis/(1000*60))%60)
    hours=int((millis/(1000*60*60))%24)
    return ("%d:%d:%d" % (hours, minutes, seconds))

def get_archive(url, user_agent):
    obj = waybackpy.Url(url, user_agent)

    archives_count = obj.total_archives()

    if archives_count > 5:

        try:
            return str(obj.near(year=2020))
        except waybackpy.exceptions.WaybackError as e:
            out(e, color="red")
            try:
                return str(obj.newest())
            except waybackpy.exceptions.WaybackError as e:
                out(e, color="red")
    else:

        try:
            return str(obj.newest())
        except waybackpy.exceptions.WaybackError as e:
            out(e, color="red")
            try:
                return str(obj.save())
            except waybackpy.exceptions.WaybackError as e:
                out(e, color="red")
    return None

def get_video_description(source_code):
    regexes = (
    "\"description\":{\"simpleText\":\"(.*?)\"},\"lengthSeconds",
    "<p id=\"eow-description\"(?:[^,]*?)>(.*?)<\/p>",
    )
    for regex in regexes:

        try:
            video_description = re.search(regex, source_code).group(1).replace("|", "&#124;")
            break
        except AttributeError:
            video_description = None

    return clean_html(video_description)

def get_upload_date(source_code):
    # Diffrent output from regexs don't group the regexes
    upload_date = re.search(r"<strong class=\"watch-time-text\">(?:Published on|Premiered) ([A-Za-z]*?) ([0-9]{1,2}), ([0-9]{2,4})</strong>", source_code)
    if upload_date:
        upload_date = datetime.strptime(("%s %s %s" % (upload_date.group(2), upload_date.group(1), upload_date.group(3))), "%d %b %Y").date()
    else:
        upload_date = re.search(r"\"dateText\":{\"simpleText\":\"([A-Za-z]*?) ([0-9]{1,2}), ([0-9]{2,4})\"}", source_code)
        if upload_date:
            upload_date = str(datetime.strptime(("%s %s %s" % (upload_date.group(2), upload_date.group(1), upload_date.group(3))), "%d %b %Y").date())
        else:
            upload_date = re.search(r"\"uploadDate\":\"([0-9]{2,4})-([0-9]{1,2})-([0-9]{1,2})\"", source_code)
            if upload_date:
                upload_date = str(datetime.strptime(("%s %s %s" % (upload_date.group(1), upload_date.group(2), upload_date.group(3))), "%Y %m %d").date())
            else:
                upload_date = None
    return upload_date

def get_youtube_channel_id(source_code):
    regexes = (
    "data-channel-external-id=\"(UC[^\",]*?)\"",
    "[\"']externalChannelId[\"']:[\"']([a-zA-Z0-9_-]{0,25})[\"']",
    "\"channelId\":\"(UC[^\",]*?)\",",
    )

    for regex in regexes:

        try:
            YouTubeChannelId = re.search(regex, source_code).group(1)
            break
        except AttributeError:
            YouTubeChannelId = None

    return YouTubeChannelId

def get_youtube_channel_name(source_code):
    regexes = (
        "\\\",\\\"author\\\":\\\"(.*?)\\\",\\\"",
        "\"ownerChannelName\\\":\\\"(.*?)\\\",",
        "Unsubscribe from ([^<{]*?)\?",
        "\"ownerChannelName\":\"(.*?)\",",
        "<span class=\"g-hovercard\" data-name=\"relmfu\" data-ytid=\"(?:[^\"]*?)\">(.*?)</span>",
        "\",\"author\":\"(.*?)\",\"",
        "Uploaded\sby\s<a class=\"author\" rel=\"author\" href=\".*?\">([^\n]*?)</a>", #https://web.archive.org/web/20110726191125/http://www.youtube.com/watch?v=doGcMijgWx4
        "<div id=\"subscribeCount\" class=\"smallText\">to ([^\n]*?)</div>", #https://web.archive.org/web/20061208083125/https://www.youtube.com/watch?v=jNQXAC9IVRw
        "<a class=\"action-button\" onclick=\"subscribe\(watchUsername, subscribeaxc\); return false;\" title=\"subscribe to ([^\n]*?)'s videos\">", #https://web.archive.org/web/20080220023552/https://www.youtube.com/watch?v=hChq5drjQl4
        "<link itemprop=\"url\" href=\"http://www\.youtube\.com/user/([^\n]*?)\">",
    )

    for regex in regexes:

        try:
            YouTubeChannelName  = re.search(regex, source_code).group(1).replace("|", "&#124;")
            break
        except AttributeError:
            YouTubeChannelName = None

    return YouTubeChannelName

def get_youtube_view_count(source_code):
    match = re.search(r"videoViewCountRenderer\":{\"viewCount\":{\"simpleText\":\"([0-9,]*?) views\"},\"shortViewCount\":{\"simpleText\"", source_code)

    if match:
        view_count = match.group(1)
    else:
         view_count = None

    return view_count

def get_license(source_code):
    license = "Creative Commons Attribution license (reuse allowed)"
    if not re.search(r"Creative Commons", source_code):
        license = "Standard YouTube License"
    return license

def get_duration(source_code):
    regexes = (
    "approxDurationMs\\\":\\\"([0-9]*?)\\\"",
    )

    for regex in regexes:

        try:
            duration = format_time(re.search(regex, source_code).group(1))
            break
        except AttributeError:
            duration = None

    return duration

def get_youtube_video_title(source_code):
    regexes = (
    "<title>(?:\s*|)(.{1,250})(?:\s*|)- YouTube(?:\s*|)</title>",
    "\"title\":\"(.{1,160})\",\"length",
    )

    for regex in regexes:

        try:
            YouTubeVideoTitle  = clean_html(re.search(regex, source_code).group(1)).replace("|", "&#124;")
            break
        except AttributeError:
            YouTubeVideoTitle = None

    return YouTubeVideoTitle

def ytdata(video_id, user_agent):
    url = "https://www.youtube.com/watch?v=%s" % video_id
    archive_url = get_archive(url, user_agent)

    if not archive_url:
        return None

    archive_url = str(archive_url)
    response = requests.get(archive_url)
    source_code = response.text

    if not source_code:
        response = requests.get(url)
        source_code = response.text

    upload_date = get_upload_date(source_code)
    video_description = get_video_description(source_code)
    YouTubeChannelId = get_youtube_channel_id(source_code)
    YouTubeChannelName = get_youtube_channel_name(source_code)
    view_count = get_youtube_view_count(source_code)
    thumbnail = "https://img.youtube.com/vi/%s/maxresdefault.jpg" % video_id
    license = get_license(source_code)
    duration = get_duration(source_code)
    YouTubeVideoTitle = get_youtube_video_title(source_code)

    return (url, user_agent, archive_url, upload_date, video_description, YouTubeChannelId, YouTubeChannelName, YouTubeVideoTitle, license, view_count, duration, thumbnail)
