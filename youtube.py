import waybackpy
from datetime import datetime
import re
import html as htm



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
    seconds=(millis/1000)%60
    seconds = int(seconds)
    minutes=(millis/(1000*60))%60
    minutes = int(minutes)
    hours=(millis/(1000*60*60))%24
    return ("%d:%d:%d" % (hours, minutes, seconds))

def get_video_description(source_code):
    match = re.search(r"\"description\":{\"simpleText\":\"(.*?)\"},\"lengthSeconds", source_code)
    if match:
        video_description = match.group(1)
    else:
        match = re.search(r"<p id=\"eow-description\"(?:[^,]*?)>(.*?)<\/p>", source_code)
        if match:
            video_description = match.group(1)
        else:
            video_description = None


    return clean_html(video_description)

def get_archive(url, user_agent):
    obj = waybackpy.Url(url, user_agent)
    archive_url = None

    try:
        archive_url = obj.archive_url
    except waybackpy.exceptions.WaybackError as e:
        # print(e)
        try:
            archive_url = obj.save()
        except waybackpy.exceptions.WaybackError as e:
            print(e)

    return archive_url

def ytdata(video_id, user_agent):
    url = "https://www.youtube.com/watch?v=%s" % video_id
    archive_url = get_archive(url, user_agent)


    if archive_url:

        while True:
            try:
                source_code = waybackpy.Url(archive_url, user_agent).get()
                break
            except:
                pass



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


        video_description = get_video_description(source_code)


        YouTubeChannelIdRegex1 = r"data-channel-external-id=\"(.{0,30})\""
        YouTubeChannelIdRegex2 = r"[\"']externalChannelId[\"']:[\"']([a-zA-Z0-9_-]{0,25})[\"']"
        try:
            YouTubeChannelId = re.search(YouTubeChannelIdRegex1, source_code).group(1)
        except AttributeError:
            try:
                YouTubeChannelId = re.search(YouTubeChannelIdRegex2, source_code).group(1)
            except AttributeError:
                YouTubeChannelId = None


        YouTubeChannelNameRegex1 = r"\\\",\\\"author\\\":\\\"(.{1,50})\\\",\\\""
        YouTubeChannelNameRegex2 = r"\"ownerChannelName\\\":\\\"(.{1,50})\\\","
        YouTubeChannelNameRegex3 = r"Unsubscribe from ([^<{]*?)\?"
        YouTubeChannelNameRegex4 = r"\"ownerChannelName\":\"(.*?)\","
        try:
            YouTubeChannelName  = re.search(YouTubeChannelNameRegex1, source_code).group(1)
        except AttributeError:
            try:
                YouTubeChannelName  = re.search(YouTubeChannelNameRegex2, source_code).group(1)
            except AttributeError:
                try:
                    YouTubeChannelName  = re.search(YouTubeChannelNameRegex3, source_code).group(1)
                except AttributeError:
                    try:
                        YouTubeChannelName  = re.search(YouTubeChannelNameRegex4, source_code).group(1)
                    except AttributeError:
                        YouTubeChannelName = None

        match = re.search(r"videoViewCountRenderer\":{\"viewCount\":{\"simpleText\":\"([0-9,]*?) views\"},\"shortViewCount\":{\"simpleText\"", source_code)
        if match:
            view_count = match.group(1)
        else:
             view_count = None


        if re.search(r"Creative Commons", source_code):
            license = "Creative Commons Attribution license (reuse allowed)"
        else:
            license = "Standard YouTube License"


        match = re.search(r"approxDurationMs\\\":\\\"([0-9]*?)\\\"", source_code)
        if match:
            duration = format_time(match.group(1))
        else:
            duration = None

        thumbnail = "https://img.youtube.com/vi/%s/maxresdefault.jpg" % video_id


        YouTubeVideoTitleRegex1 = r"<title>(?:\s*|)(.{1,250})(?:\s*|)- YouTube(?:\s*|)</title>"
        YouTubeVideoTitleRegex2 = r"\"title\":\"(.{1,160})\",\"length"
        try:
            YouTubeVideoTitle   = clean_html(re.search(YouTubeVideoTitleRegex1, source_code).group(1))
        except AttributeError:
            try:
                YouTubeVideoTitle   = clean_html(re.search(YouTubeVideoTitleRegex2, source_code).group(1))
            except AttributeError:
                YouTubeVideoTitle = None

        return (url, user_agent, archive_url, upload_date, video_description, YouTubeChannelId, YouTubeChannelName, YouTubeVideoTitle, license, view_count, duration, thumbnail)

    else:
        return None
