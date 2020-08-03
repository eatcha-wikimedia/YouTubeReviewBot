# -*- coding: utf-8 -*-
import re
import sys
import pywikibot
import waybackpy
import requests
import logging
import pprint
import langdetect as lang
from datetime import datetime
from pywikibot import pagegenerators

from utils import (
uploader,
last_edit_time,
informatdate,
IsMarkedForDeletion,
DetectSite,
check_channel,
OwnWork,
display_video_info,
out,
)

def dump_file(filename, reason):
    """Dump files if review not possible for multiple times."""
    dump1_pagetext = pywikibot.Page(SITE,"User:YouTubeReviewBot/dump1",).get(get_redirect=True)
    dump2_pagetext = pywikibot.Page(SITE,"User:YouTubeReviewBot/dump2",).get(get_redirect=True)
    dump3_pagetext = pywikibot.Page(SITE,"User:YouTubeReviewBot/dump3",).get(get_redirect=True)

    summary = "Dumped [[%s]]. (%s)" % (filename, reason)

    file_info = "\n#[[:" + filename + "]]  Reason : " + reason

    if filename in dump2_pagetext:
        commit(dump3_pagetext,(dump3_pagetext + file_info), pywikibot.Page(SITE,"User:YouTubeReviewBot/dump3",), summary)
    elif filename in dump1_pagetext:
        commit(dump2_pagetext,(dump2_pagetext + file_info), pywikibot.Page(SITE,"User:YouTubeReviewBot/dump2",), summary)
    else:
        commit(dump1_pagetext,(dump1_pagetext + file_info), pywikibot.Page(SITE,"User:YouTubeReviewBot/dump1",), summary)

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
            watch=True,
            minor=False,
            )

    elif choice in esc:
        sys.exit(0)

    else:
        pass

def AutoFill(site, text, source, author, VideoTitle, uploaddate, description, Replace_nld):
    """Auto fills empty information template parameters."""
    if site == "YouTube":
        License = "{{YouTube CC-BY|%s}}" % author

        # Handle cases where there's no description at all on YouTube
        if description.isspace() or not description:
            description = VideoTitle

    if site == "Vimeo": #Not Implemented yet, not required yet
        uploaddate = ""
        description = ""

    #remove scheme from urls

    if re.search(r"\|description=(?:\n|\s*\n)",text):
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
            out("IGNORE - File dumped for 3rd time.", color='red')
            continue

        if (datetime.utcnow()-last_edit_time(filename)).days > 30:
            reason = "Not edited for more than a month."
            out(reason, color='red')
            dump_file(filename, reason)
            continue

        page = pywikibot.Page(SITE, filename)
        old_text = pagetext = page.get()

        try:
            source_area = re.search("\|[Ss]ource=(.*)", pagetext).group(1)
        except AttributeError:
            source_area = pagetext #If we found empty source param we treat the full page as source

        if source_area.isspace(): #check if it's just newlines tabs and spaces.
            source_area = pagetext

        Identified_site = DetectSite((source_area.lower()))

        out("A file from %s." % Identified_site, color="yellow")

        if not Identified_site:
            out("Skipping cuz source unidentified.", color="yellow")
            continue

        if IsMarkedForDeletion(pagetext) is True:
            out("IGNORE - File is marked for deletion", color='red')
            continue

        elif Identified_site == "VideoWiki":
            new_text = re.sub(RegexOfLicenseReviewTemplate, "" , old_text)
            EditSummary = "@%s removing license Review template, not required for video-wiki files\
            because all constituent files are from commons." % uploader(filename, link=True)

            try:
                commit(old_text, new_text, page, EditSummary)
            except pywikibot.LockedPage as error:
                out("Page is locked '%s'." % error, color='red')
                continue

        elif OwnWork(pagetext):
            new_text = re.sub(RegexOfLicenseReviewTemplate, "" , old_text)
            EditSummary = "@%s removing license Review template, not required for ownwork." % uploader(filename,link=True)
            try:
                commit(old_text, new_text, page, EditSummary)
            except pywikibot.LockedPage as error:
                out("Page is locked '%s'." % error, color='red')
                continue

        elif Identified_site == "Flickr":
            new_text = re.sub(RegexOfLicenseReviewTemplate, "{{FlickrReview}}" , old_text)
            EditSummary = "@%s Marking for flickr review, file's added to [[Category:Flickr videos review needed]]." % uploader(filename,link=True)
            try:
                commit(old_text, new_text, page, EditSummary)
            except pywikibot.LockedPage as error:
                out("Page is locked '%s'." % error, color='red')
                continue

        elif Identified_site == "Vimeo":
            try:
                VimeoVideoId = re.search(r"{{\s*?[Ff]rom\s[Vv]imeo\s*(?:\||\|1\=|\s*?)(?:\s*)(?:1\=|)(?:\s*?|)([0-9_]+)", source_area).group(1)
            except AttributeError:
                try:
                    VimeoVideoId = re.search(r"vimeo\.com\/((?:[0-9_]+))", source_area).group(1)
                except AttributeError:
                    out("PARSING FAILED - Can't get VimeoVideoId", color='red')
                    continue

            SourceURL = "https://vimeo.com/%s" % VimeoVideoId
            user_agent = "User:YouTubeReviewBot on wikimedia commons"

            try:
                archive_url = waybackpy.Url(SourceURL, user_agent).newest()
            except Exception:
                try:
                    archive_url = waybackpy.Url(SourceURL, user_agent).save()
                except Exception as e:
                    out(e, color="red")
                    continue

            try:
                webpage = waybackpy.Url(SourceURL, user_agent).get()
            except Exception as e:
                reason = "Unable to get source code of %s" % SourceURL
                out(e, color="red")
                dump_file(filename, reason)
                continue


            # Try to get the ChannelID
            try:
                VimeoChannelId = re.search(r"http(?:s|)\:\/\/vimeo\.com\/(user[0-9]{0,30})\/video", webpage).group(1)
            except AttributeError:
                try:
                    VimeoChannelId = re.search(r"https://vimeo\.com/([^:/\"]{0,250}?)/videos\"", webpage).group(1)
                except AttributeError:
                    reason = "PARSING FAILED - Can't get VimeoChannelId"
                    out(reason, color='red')
                    dump_file(filename, reason)
                    continue

            # If bad Channel do not review it, we do not support trusted Channel for vimeo yet.
            if check_channel(VimeoChannelId) == "Bad":
                reason = "DUMP - %s is from a shady channel %s" % (filename, VimeoChannelId)
                out(reason, color="red")
                dump_file(filename, reason)
                continue

            # Try to get video title
            try:
                VimeoVideoTitle = re.search(r"<title>(.*?) on Vimeo<\/title>", webpage, re.MULTILINE).group(1)
            except AttributeError:
                reason = "PARSING FAILED - Can't get VimeoVideoTitle"
                out(reason, color='red')
                dump_file(filename, reason)
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
                    reason = "Licensed under %s, and isn't valid on wikimedia commons" % VimeoLicense
                    out(reason, color="red")
                    dump_file(filename, reason)
                    continue
            else:
                reason = "File is not licensed under any type of creative commons\
                license including CC-NC/ND"
                out(reason, color='red')
                dump_file(filename, reason)
                continue

            TAGS = "{{VimeoReview|id=%s|title=%s|license=%s|ChannelID=%s|archive=%s|date=%s}}" % (
                VimeoVideoId,
                VimeoVideoTitle,
                VimeoLicense,
                VimeoChannelId,
                archive_url,
                informatdate(),
                )

            #Out puts some basic info about the video.
            display_video_info(VimeoVideoId,VimeoChannelId,VimeoVideoTitle,archive_url)

            new_text = re.sub(RegexOfLicenseReviewTemplate, TAGS, old_text)

            EditSummary = "LR Passed, %s , by %s under terms of %s at https://vimeo.com/%s (Archived\
            - WayBack Machine)" % (VimeoVideoTitle, VimeoChannelId, VimeoLicense, VimeoVideoId)

            try:
                commit(
                    old_text,
                    new_text,
                    page,
                    EditSummary
                    )
            except pywikibot.LockedPage as error:
                out("Page is locked '%s'." % error, color='red')
                continue

        elif Identified_site == "YouTube":

            try:
                YouTubeVideoId = re.search(
                    r"{{\s*?[Ff]rom\s[Yy]ou[Tt]ube\s*(?:\||\|1\=|\s*?)(?:\s*)(?:1|=\||)(?:=|)([^\"&?\/ ]{11})", source_area).group(1)
            except AttributeError:
                try:
                    YouTubeVideoId = re.search(r"https?\:\/\/(?:www|m|)(?:|\.)youtube\.com/watch\W(?:feature\\=player_embedded&)?v\=([^\"&?\/ ]{11})", source_area).group(1)
                except AttributeError:
                    reason = "PARSING FAILED - Can't get YouTubeVideoId"
                    out(reason, color='red')
                    dump_file(filename, reason)
                    continue

            SourceURL = "https://www.youtube.com/watch?v=%s" % YouTubeVideoId
            out(SourceURL)


            res = requests.get("https://eatchabot.toolforge.org/youtube?url=%s&user_agent=%s" % (SourceURL, "User:YouTubeReviewBot on wikimedia commons"))
            if res.status_code == 200:
                data = res.json()
            else:
                out("Status code %s. Skipping" % (res.status_code) , color="red")
                continue


            if data['available']:
                archive_url = data['archive_url']
                YouTubeVideoTitle = data['video_title']
                YouTubeChannelName = data['channel_name']
                description = data['description']
                upload_date = data['upload_date']
                YouTubeChannelId = data['channel_id']
                license = data['license']

            if data['available'] and not data['channel_id'] and not data['channel_name']:
                reason = "Can not parse data from %s. Dumping file." % archive_url
                pprint.pprint(data, width=1)
                out(reason, color="red")
                dump_file(filename, reason)
                continue

            #Out puts some basic info about the video.
            display_video_info(YouTubeVideoId, YouTubeChannelId, YouTubeVideoTitle, archive_url, ChannelName=YouTubeChannelName)

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

            if check_channel(YouTubeChannelId) != "Trusted" and not re.search(r"Creative Commons", license):
                reason = "File not from trusted channel nor freely licensed."
                out(reason, color="red")
                dump_file(filename, reason)
                continue

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


            if re.search(r"Creative Commons", license) or check_channel(YouTubeChannelId) == "Trusted":
                new_text = re.sub(
                    RegexOfLicenseReviewTemplate,
                    TAGS,
                    new_text
                    )
            else:
                reason = "Video is not licensed Creative Commons on YouTube also not from a trusted channel."
                out(reason ,color="red")
                dump_file(filename, reason)
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
                out("Warning - unknown argument '%s' aborting, use -auto for automatic review\
                or -dry to test and not submit the edits. see -help for pywikibot help" % arg, color="red")
                sys.exit(0)

    try:
        checkfiles()
    except Exception as e:
        logging.error(e, exc_info=True)


if __name__ == "__main__":
    try:
        main()
    finally:
        pywikibot.stopme()
