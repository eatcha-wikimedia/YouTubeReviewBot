# -*- coding: utf-8 -*-
import re
import sys
import pywikibot
import waybackpy
import requests
import langdetect as lang
from datetime import datetime
from pywikibot import pagegenerators


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

def dump_file(filename):
    """Dump files if review not possible for multiple times."""
    dump1_pagetext = pywikibot.Page(SITE,"User:YouTubeReviewBot/dump1",).get(get_redirect=True)
    dump2_pagetext = pywikibot.Page(SITE,"User:YouTubeReviewBot/dump2",).get(get_redirect=True)
    dump3_pagetext = pywikibot.Page(SITE,"User:YouTubeReviewBot/dump3",).get(get_redirect=True)
    if filename in dump2_pagetext:
        commit(dump3_pagetext,(dump3_pagetext + "\n#[[:" + filename + "]]"),pywikibot.Page(SITE,"User:YouTubeReviewBot/dump3",),"dumped [[%s]]" % filename ,)
    elif filename in dump1_pagetext:
        commit(dump2_pagetext,(dump2_pagetext + "\n#[[:" + filename + "]]"),pywikibot.Page(SITE,"User:YouTubeReviewBot/dump2",),"dumped [[%s]]" % filename ,)
    else:
        commit(dump1_pagetext,(dump1_pagetext + "\n#[[:" + filename + "]]"),pywikibot.Page(SITE,"User:YouTubeReviewBot/dump1",),"dumped [[%s]]" % filename ,)

def upload_date(filename):
    """Upload date of the file."""
    for info in (pywikibot.Page(SITE, filename)).revisions(reverse=True, total=1):
        return datetime.strptime(str(info.timestamp), "%Y-%m-%dT%H:%M:%SZ")

def last_edit_time(file_name):
    """Recent most editor for file."""
    for info in (pywikibot.Page(SITE, file_name)).revisions(reverse=False, total=1):
        return datetime.strptime(str(info.timestamp), "%Y-%m-%dT%H:%M:%SZ")

def informatdate():
    """Current date in yyyy-mm-dd format."""
    return (datetime.utcnow()).strftime('%Y-%m-%d')

def AutoFill(site, text, source, author, VideoTitle, uploaddate, description, Replace_nld):
    """Auto fills empty information template parameters."""
    if site == "YouTube":
        License = "{{YouTube CC-BY|%s}}" % author

        # Handle cases where there's no description at all on YouTube
        if description.isspace() or not description:
            description = VideoTitle

    elif site == "Vimeo": #Not Implemented yet, not required yet
        uploaddate = ""
        description = ""

    #remove scheme from urls
    description = re.sub('https?://', '', description).strip()

    if not re.search(r"\|description=(.*)",text).group(1):
        description = "{{%s|%s}}" % (lang.detect(description), description)
        text = text.replace("|description=","|description=%s" % description ,1)

    if uploaddate:
        text = re.sub("\|date=.*", "|date=%s" % uploaddate, text)

    text = re.sub("\|source=.*", "|source=%s" % source, text)
    text = re.sub("\|author=.*", "|author=%s" % author, text)

    if Replace_nld:
        text = re.sub("{{No license since.*?}}", "%s" % License, text, re.IGNORECASE)
        text = re.sub("{{(?:|\s)[Yy]ou(?:|\s)[Tt]ube(?:\|.*?|)(?:|\s)}}", "%s" % License, text)
        text = re.sub("{{(?:|\s)[Yy]ou(?:|\s)[Tt]ube(?:|\s*?)(?:[Cc]{2}-[Bb][Yy]).*?}}", "%s" % License, text)
    return text

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

def archived_url(SourceURL):
    """Get a real-time archived url of the source url."""
    archive_url = None
    status = "Wait"
    iters = 0
    while status == "Wait":
        iters += 1
        try:
            archive_url = waybackpy.Url(SourceURL, "User:YouTubeReviewBot on wikimedia commons").save()
            status = "Done"
        except Exception as e:
            out(
                e,
                color="red",
                )
        if iters > 5:
            status = "Stop"
    return archive_url

def oldest_ia_page(archive_url):
    url = re.search(r"(?:[0-9])\/(.*)", archive_url).group(1)
    url = ("https://archive.org/wayback/available?url={url}&timestamp=1998").format(url=url)
    target = waybackpy.Url(url, "User:YouTubeReviewBot on wikimedia commons")
    return target.get(target.oldest())

def archived_webpage(archive_url):
    """Get the source code of the archived webpage."""
    webpage = None
    status = "Wait"
    iters = 0
    while status == "Wait":
        iters += 1
        try:
            webpage = waybackpy.Url(archive_url, "User:YouTubeReviewBot on wikimedia commons").get()
            status = "Done"
        except Exception as e:
            out(
                e,
                color="red",
                )
        if iters > 5:
            status = "Stop"
    error301 = "Got an HTTP 301 response at crawl time"
    if error301 in webpage and webpage is not None:
        out("%s - try to get oldest archived_snapshots" % error301 ,color="red",)
        try:
            webpage = oldest_ia_page(archive_url)
        except Exception as e:
            out(
                e,
                color="red",
                )
    return webpage

def check_channel(ChannelId):
    """Check if the channel is trusted or bad."""
    if ChannelId in (pywikibot.Page(SITE, "User:YouTubeReviewBot/Trusted")).get(get_redirect=True, force=True):
        return "Trusted"
    elif ChannelId in (pywikibot.Page(SITE, "User:YouTubeReviewBot/bad-authors")).get(get_redirect=True, force=True):
        return "Bad"
    return "Normal"

def display_video_info(VideoId,ChannelId,VideoTitle,ArchiveUrl,ChannelName="Not Applicable"):
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

def OwnWork(pagetext):
    """Check if own work by uploader."""
    LowerCasePageText = pagetext.lower()
    if (LowerCasePageText.find('{{own}}') != -1):
        return True
    elif (LowerCasePageText.find('own work') != -1):
        return True
    return False

def commit(old_text, new_text, page, summary):
    """Show diff and submit text to the wiki server."""
    yes = {'yes','y', 'ye', ''}
    esc = {'q','quit','exit'}
    question = "Do you want to accept these changes to '%s' with summary '%s' ? [Yy]es / [Nn]o / [Qq]uit \n" % (
        page.title(),
        summary,
        )

    if DRY:
        choice = "n"
    elif AUTO:
        choice = "y"
    else:
        choice = input(question).lower()

    if choice in yes:
        out(
            "\nAbout to make changes at : '%s'" % page.title()
            )

        pywikibot.showDiff(
            old_text,
            new_text,
            )

        page.put(
            new_text,
            summary=summary,
            watchArticle=True,
            minorEdit=False,
            )

    elif choice in esc:
        sys.exit(0)

    else:
        pass

def out(text, newline=True, date=False, color=None):
    """Just output some text to the consoloe or log."""
    if color:
        text = "\03{%s}%s\03{default}" % (color, text)
    dstr = (
        "%s: " % datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        if date
        else ""
    )
    pywikibot.stdout(
        "%s%s" % (dstr, text),
        newline=newline,
        )

def checkfiles():
    category = pywikibot.Category(
        SITE,
        'License_review_needed_(video)',
        )
    RegexOfLicenseReviewTemplate = r"{{(?:|\s*)[LlVvYy][IiOo][CcMmUu][EeTt][NnUuOo](?:[SsBbCc][Ee]|)(?:|\s*)[Rr][Ee][Vv][Ii][Ee][Ww](?:|\s*)(?:\|.*|)}}"
    gen = pagegenerators.CategorizedPageGenerator(
        category,
        )
    file_count = 0
    dumpHell = pywikibot.Page(SITE,"User:YouTubeReviewBot/dump3",).get(get_redirect=True)

    for page in gen:
        file_count += 1
        filename = page.title()

        out(
            "\n%d - %s" % (
                file_count,
                filename,
                ),
                color="white",
                )

        if filename in dumpHell:
            out(
                "IGNORE - File dumped for 3rd time.",
                color='red',
                )
            continue


        if (datetime.utcnow()-last_edit_time(filename)).days > 30:
            out(
                "File is not edited for a long time 1 months, will not process it.",
                color='red',
                )
            dump_file(filename)
            continue

        page = pywikibot.Page(
            SITE,
            filename,
            )

        old_text = pagetext = page.get()

        try:
            source_area = re.search("\|[Ss]ource=(.*)", pagetext).group(1)
        except AttributeError:
            source_area = pagetext #If we found empty source param we treat the full page as source

        if source_area.isspace(): #check if it's just newlines tabs and spaces.
            source_area = pagetext

        Identified_site = DetectSite((source_area.lower()))

        out(
            "Identified as %s" % Identified_site,
            color="yellow",
            )

        if not Identified_site:
            continue

        if IsMarkedForDeletion(pagetext) is True:
            out(
                "IGNORE - File is marked for deletion",
                color='red',
                )
            continue

        elif Identified_site == "VideoWiki":
            new_text = re.sub(RegexOfLicenseReviewTemplate, "" , old_text)
            EditSummary = "@%s Removing licenseReview Template, not required for video-wiki files beacuse all constituent files are from commons." % uploader(
                filename,
                link=True,
                )
            try:
                commit(old_text, new_text, page, EditSummary)
            except pywikibot.LockedPage as error:
                out(
                    "Page is locked '%s'." % error,
                    color='red',
                    )
                continue

        elif OwnWork(pagetext):
            new_text = re.sub(RegexOfLicenseReviewTemplate, "" , old_text)
            EditSummary = "@%s Removing licenseReview Template, not required for ownwork." % uploader(filename,link=True)
            try:
                commit(old_text, new_text, page, EditSummary)
            except pywikibot.LockedPage as error:
                out(
                    "Page is locked '%s'." % error,
                    color='red',
                    )
                continue

        elif Identified_site == "Flickr":
            new_text = re.sub(RegexOfLicenseReviewTemplate, "{{FlickrReview}}" , old_text)
            EditSummary = "@%s Marking for flickr review, file's added to [[Category:Flickr videos review needed]]." % uploader(filename,link=True)
            try:
                commit(
                    old_text,
                    new_text,
                    page,
                    EditSummary,
                    )
            except pywikibot.LockedPage as error:
                out(
                    "Page is locked '%s'." % error,
                    color='red',
                    )
                continue

        elif Identified_site == "Vimeo":
            try:
                VimeoVideoId = re.search(r"{{\s*?[Ff]rom\s[Vv]imeo\s*(?:\||\|1\=|\s*?)(?:\s*)(?:1\=|)(?:\s*?|)([0-9_]+)", source_area).group(1)
            except AttributeError:
                try:
                    VimeoVideoId = re.search(r"vimeo\.com\/((?:[0-9_]+))", source_area).group(1)
                except AttributeError:
                    out(
                        "PARSING FAILED - Can't get VimeoVideoId",
                        color='red',
                        )
                    continue
            SourceURL = "https://vimeo.com/%s" % VimeoVideoId

            try:
                if archived_url(SourceURL) is not None:
                    archive_url = archived_url(SourceURL)
                else:
                    out(
                        "WAYBACK FAILED - Can't get archive_url",
                        color='red',
                        )
                    dump_file(filename)
                    continue

                if archived_webpage(archive_url) is None:
                    out(
                        "WAYBACK FAILED - Can't get webpage",
                        color='red',
                        )
                    dump_file(filename)
                    continue

                else:
                    webpage = archived_webpage(archive_url)
            except Exception as e:
                out(e, color="red")
                dump_file(filename)
                continue

            # Try to get the ChannelID
            try:
                VimeoChannelId = re.search(r"http(?:s|)\:\/\/vimeo\.com\/(user[0-9]{0,30})\/video", webpage).group(1)
            except AttributeError:
                try:
                    VimeoChannelId = re.search(r"https://vimeo\.com/([^:/\"]{0,250}?)/videos\"", webpage).group(1)
                except AttributeError:
                    out(
                        "PARSING FAILED - Can't get VimeoChannelId",
                        color='red',
                        )
                    dump_file(filename)
                    continue

            # If bad Channel do not review it, we do not support trusted Channel for vimeo yet.
            if check_channel(VimeoChannelId) == "Bad":
                out(
                    "IGNORE - Bad Channel %s" % VimeoChannelId,
                    color="red",
                    )
                dump_file(filename)
                continue

            # Try to get video title
            try:
                VimeoVideoTitle = re.search(r"<title>(.*?) on Vimeo<\/title>", webpage, re.MULTILINE).group(1)
            except AttributeError:
                out(
                    "PARSING FAILED - Can't get VimeoVideoTitle",
                    color='red',
                    )
                dump_file(filename)
                continue

            if re.search(r"creativecommons.org", webpage):
                StandardCreativeCommonsUrlRegex = re.compile('https\:\/\/creativecommons\.org\/licenses\/(.*?)\/(.*?)\/')
                matches = StandardCreativeCommonsUrlRegex.finditer(webpage)
                for m in matches:
                    licensesP1, licensesP2  = (m.group(1)), (m.group(2))
                VimeoLicense = licensesP1 + "-" + licensesP2
                Allowedlicenses = [
                    'by-sa',
                    'by',
                    'publicdomain',
                    'cc0',
                    ]
                if licensesP1 not in Allowedlicenses:
                    out(
                        "The file is licensed under %s, but it's not allowed on commons" % VimeoLicense,
                        color="red",
                        )
                    dump_file(filename)
                    continue
                else:pass
            else:
                out(
                    "Creative commons Not found - File is not licensed under any type of creative commons license including CC-NC/ND",
                    color='red'
                    )
                dump_file(filename)
                continue

            TAGS = '{{VimeoReview|id=%s|title=%s|license=%s|ChannelID=%s|archive=%s|date=%s}}' % (
                VimeoVideoId,
                VimeoVideoTitle,
                VimeoLicense,
                VimeoChannelId,
                archive_url,
                informatdate(),
                )

            #Out puts some basic info about the video.
            display_video_info(VimeoVideoId,VimeoChannelId,VimeoVideoTitle,archive_url)

            new_text = re.sub(
                RegexOfLicenseReviewTemplate,
                TAGS,
                old_text
                )

            EditSummary = "LR Passed, %s , by %s under terms of %s at https://vimeo.com/%s (Archived - WayBack Machine)" % (
                VimeoVideoTitle,
                VimeoChannelId,
                VimeoLicense,
                VimeoVideoId,
                )

            try:
                commit(
                    old_text,
                    new_text,
                    page,
                    EditSummary
                    )
            except pywikibot.LockedPage as error:
                out(
                    "Page is locked '%s'." % error,
                    color='red'
                    )
                continue

        elif Identified_site == "YouTube":

            try:
                YouTubeVideoId = re.search(
                    r"{{\s*?[Ff]rom\s[Yy]ou[Tt]ube\s*(?:\||\|1\=|\s*?)(?:\s*)(?:1|=\||)(?:=|)([^\"&?\/ ]{11})", source_area).group(1)
            except AttributeError:
                try:
                    YouTubeVideoId = re.search(r"https?\:\/\/(?:www|m|)(?:|\.)youtube\.com/watch\W(?:feature\\=player_embedded&)?v\=([^\"&?\/ ]{11})", source_area).group(1)
                except AttributeError:
                    out(
                        "PARSING FAILED - Can't get YouTubeVideoId",
                        color='red'
                        )
                    dump_file(filename)
                    continue

            SourceURL = "https://www.youtube.com/watch?v=%s" % YouTubeVideoId

            res = requests.get("https://eatchabot.toolforge.org/youtube?url=%s&user_agent=%s" % (SourceURL, "User:YouTubeReviewBot on wikimedia commons"))

            data = res.json()

            if data['available']:
                archive_url = data['archive_url']
                YouTubeVideoTitle = data['video_title']
                YouTubeChannelName = data['channel_name']
                description = data['description']
                upload_date = data['upload_date']
                YouTubeChannelId = data['channel_id']
                license = data['license']
            else:
                dump_file(filename)


            TAGS = str(
                "{{YouTubeReview"
                "|id=" + YouTubeVideoId +
                "|ChannelName=" + YouTubeChannelName +
                "|ChannelID=" + YouTubeChannelId +
                "|title=" + YouTubeVideoTitle +
                "|archive=" + archive_url +
                "|date=" + informatdate() +
                "}}"
                )

            #Out puts some basic info about the video.
            display_video_info(YouTubeVideoId,YouTubeChannelId,YouTubeVideoTitle,archive_url, ChannelName=YouTubeChannelName)

            if check_channel(YouTubeChannelId) == "Trusted":
                TrustTextAppend = "[[User:YouTubeReviewBot/Trusted|✔️ - Trusted YouTube Channel of  %s ]]" %  YouTubeChannelName
                YouTubeLicense = ""
                Replace_nld = False
            else:
                TrustTextAppend = ""
                YouTubeLicense = "under terms of CC BY 3.0"
                Replace_nld = True # replace no license with {{YouTube CC-BY|ChannelName}}

            EditSummary = "%s LR Passed, %s, by %s (%s) %s at www.youtube.com/watch?v=%s (Archived - WayBack Machine)" % (
                TrustTextAppend,
                YouTubeVideoTitle,
                YouTubeChannelName,
                YouTubeChannelId,
                YouTubeLicense,
                YouTubeVideoId,
                )


            new_text = AutoFill(
                "YouTube",
                old_text,
                ("{{From YouTube|1=%s|2=%s}}" % (YouTubeVideoId, YouTubeVideoTitle)),
                ("[https://www.youtube.com/channel/%s %s]" % (YouTubeChannelId, YouTubeChannelName)),
                YouTubeVideoTitle,
                upload_date,
                description,
                Replace_nld
                )


            if re.search(r"Creative Commons", license) is not None or check_channel(YouTubeChannelId) == "Trusted":
                new_text = re.sub(
                    RegexOfLicenseReviewTemplate,
                    TAGS,
                    new_text
                    )
            else:
                out("Video is not Creative Commons 3.0 licensed on YouTube nor from a Trusted Channel",color="red")
                dump_file(filename)
                continue

            if new_text == old_text:
                out(
                    "IGONRE - New text was equal to Old text.",
                    color="red"
                    )
                continue
            else:
                pass
            try:
                commit(
                    old_text,
                    new_text,
                    page,
                    EditSummary
                    )
            except pywikibot.LockedPage as error:
                out(
                    "Page is locked '%s'." % error,
                    color='red'
                    )
                continue
        else:
            continue

# Global variables defined at the module level
DRY = None
AUTO = None
SITE = None

def main(*args):
    global SITE
    global DRY
    global AUTO
    for arg in sys.argv[1:]:
        if arg == "-auto":
            AUTO = True
            sys.argv.remove(arg)
            continue
        elif arg == "-dry":
            DRY = True
            sys.argv.remove(arg)
            continue
    args = pywikibot.handle_args(*args)
    SITE = pywikibot.Site()

    if DRY is not True:
        if not SITE.logged_in():
            SITE.login()
        else:pass
    else:pass

    # Abort on unknown arguments
    for arg in args:
        if arg not in [
            "-auto",
            "-dry",
            ]:
                out(
                    "Warning - unknown argument '%s' aborting, use -auto for automatic review or -dry to test and not submit the edits. see -help for pywikibot help" % arg,
                    color="lightred",
                    )
                sys.exit(0)
    try:
        checkfiles()
    except Exception as e:
        out(e, color="red")


if __name__ == "__main__":
    try:
        main()
    finally:
        pywikibot.stopme()
