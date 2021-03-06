# -*- coding: utf-8 -*-
import re
import sys
import pywikibot
import waybackpy
import logging
import langdetect as lang
from datetime import datetime
from pywikibot import pagegenerators
from youtube import ytdata
import multiprocessing
import time
import emoji
from collections import OrderedDict
from utils import (
uploader,
last_edit_time,
informatdate,
is_marked_for_deletion,
detect_source_site,
check_channel,
is_own_work,
display_video_info,
out,
escape_wikitext,
sanitize,
)

# Global variables
REGEX_OF_LICENSE_REVIEW_TEMPLATE = r"{{(?:|\s*)[LlVvYy][IiOo][CcMmUu][EeTt][NnUuOo](?:[SsBbCc][Ee]|)(?:|\s*)[Rr][Ee][Vv][Ii][Ee][Ww](?:|\s*)(?:\|.*|)}}"
USER_AGENT = "User:YouTubeReviewBot on wikimedia commons"
DRY = None
AUTO = None
SITE = None

def days_old(file, link=True):
    """Return the link to the user that uploaded the nominated media."""
    page = pywikibot.Page(SITE, file)
    history = page.revisions(reverse=True, total=1)
    for data in history:
        ts = data.timestamp
    delta_days = (datetime.utcnow() - ts).days
    return int(delta_days)

def dump_file(filename, reason):
    #wayback machine API is the most unreliable API I've ever used. Wait for 2 days (lags).
    if days_old(filename, link=True) < 2:
        return

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
        out("\nAbout to make changes at : '%s'" % page.title())

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

def auto_fill(site, text, source, author, VideoTitle, uploaddate, description, replace_nld):
    """Auto fills empty information template parameters."""
    if site == "YouTube":
        License = "{{YouTube CC-BY|%s}}" % author

        # Handle cases where there's no description at all on YouTube
        if not description or description.isspace():
            description = VideoTitle

    if site == "Vimeo": #Not Implemented yet, not required yet
        uploaddate = ""
        description = ""

    #remove scheme from urls

    if re.search(r"\|description=(?:\n|\s*\n)", text):
        description = "{{%s|%s}}" % (lang.detect(description), escape_wikitext(description))
        text = text.replace("|description=","|description=%s" % description ,1)

    if uploaddate and "{{YouTubeReview|id=" not in text:
        text = re.sub("\|date=.*", "|date=%s" % uploaddate, text)

    text = re.sub("\|source=.*", "|source=%s" % source, text)
    text = re.sub("\|author=.*", "|author=%s" % author, text)

    if replace_nld:
        text = re.sub("{{No license since.*?}}", "%s" % License, text, re.IGNORECASE)
        text = re.sub("{{(?:|\s)[Yy]ou(?:|\s)[Tt]ube(?:\|.*?|)(?:|\s)}}", "%s" % License, text)
        text = re.sub("{{(?:|\s)[Yy]ou(?:|\s)[Tt]ube(?:|\s*?)(?:[Cc]{2}-[Bb][Yy]).*?}}", "%s" % License, text)
    return text

#######################   HANDLER FUNCTIONS START  ###############################

def handle_videowiki(page, filename, old_text):
    new_text = re.sub(REGEX_OF_LICENSE_REVIEW_TEMPLATE, "" , old_text)
    edit_summary = "@%s removing license Review template, not required for video-wiki files\
    because all constituent files are from commons." % uploader(filename, link=True)

    try:
        commit(old_text, new_text, page, edit_summary)
    except pywikibot.LockedPage as error:
        out("Page is locked '%s'." % error, color='red')

def handle_ownwork(page, filename, old_text):
    new_text = re.sub(REGEX_OF_LICENSE_REVIEW_TEMPLATE, "" , old_text)
    edit_summary = "@%s removing license Review template, not required for ownwork." % uploader(filename, link=True)
    try:
        commit(old_text, new_text, page, edit_summary)
    except pywikibot.LockedPage as error:
        out("Page is locked '%s'." % error, color='red')

def handle_flickr(page, filename, old_text):
    new_text = re.sub(REGEX_OF_LICENSE_REVIEW_TEMPLATE, "{{FlickrReview}}" , old_text)
    edit_summary = "@%s Marking for flickr review, file now in [[Category:Flickr videos review needed]]." % uploader(filename, link=True)
    try:
        commit(old_text, new_text, page, edit_summary)
    except pywikibot.LockedPage as error:
        out("Page is locked '%s'." % error, color='red')

def handle_youtube(source_area, page, filename, old_text):

    if "{{YouTubeReview|id=" and "|ChannelName=" and "|ChannelID=" in old_text: #Fox files already reviewed by other instance
        return # YouTubeReview and Information template have date parameter

    try:
        youtube_video_id = re.search(
            r"{{\s*?[Ff]rom\s[Yy]ou[Tt]ube\s*(?:\||\|1\=|\s*?)(?:\s*)(?:1|=\||)(?:=|)([^\"&?\/ ]{11})", source_area).group(1)
    except AttributeError:
        try:
            youtube_video_id = re.search(r"https?\:\/\/(?:www|m|)(?:|\.)youtube\.com/watch\W(?:feature\\=player_embedded&)?v\=([^\"&?\/ ]{11})", source_area).group(1)
        except AttributeError:
            reason = "PARSING FAILED - Can't get youtube_video_id"
            out(reason, color='red')
            dump_file(filename, reason)
            return

    user_agent = USER_AGENT
    youtube_data = ytdata(youtube_video_id, user_agent)


    if not youtube_data:
        reason = "Can't scrape any data from Internet Archive. youtube_data is None."
        out(reason, color='red')
        dump_file(filename, reason)
        return

    url = youtube_data[0]
    user_agent = youtube_data[1]
    archive_url = str(youtube_data[2])
    upload_date = youtube_data[3]
    description = youtube_data[4]
    youtube_channel_id = str(youtube_data[5])
    youtube_channel_name = youtube_data[6]
    youtube_video_title = youtube_data[7].replace("|", "&#124;")
    license = youtube_data[8]
    view_count = youtube_data[9]
    duration = youtube_data[10]
    thumbnail = youtube_data[11]

    source_url = "https://www.youtube.com/watch?v=%s" % youtube_video_id

    youtube_data_attributes = {
    "youtube_video_id" : youtube_video_id,
    "youtube_channel_id" : youtube_channel_id,
    "youtube_video_title" : youtube_video_title,
    "archive_url" : archive_url,
    "youtube_channel_name" : youtube_channel_name,
    }

    for youtube_attribute_name, youtube_attribute in youtube_data_attributes.items():
        if type(youtube_attribute) == None.__class__:
            reason = "Can't parse %s from %s" % (youtube_attribute_name, archive_url)
            out(reason, color='red')
            dump_file(filename, reason)
            return

    #Out puts some basic info about the video.
    display_video_info(youtube_video_id, youtube_channel_id, youtube_video_title, archive_url, ChannelName=youtube_channel_name)

    TAGS = str(
        "{{YouTubeReview"
        "|id=" + youtube_video_id +
        "|ChannelName=" + youtube_channel_name +
        "|ChannelID=" + youtube_channel_id +
        "|title=" + youtube_video_title +
        "|archive=" + archive_url +
        "|date=" + informatdate() +
        "}}"
        )

    if check_channel(youtube_channel_id) != "Trusted" and not re.search(r"Creative Commons", license):
        reason = "File not from trusted channel nor freely licensed."
        out(reason, color="red")
        dump_file(filename, reason)
        return

    if check_channel(youtube_channel_id) == "Trusted":
        trusted_text_append = "[[User:YouTubeReviewBot/Trusted|✔️ - Trusted YouTube Channel of  %s ]]" %  youtube_channel_name
        youtube_license = ""
        replace_nld = False
    else:
        trusted_text_append = ""
        youtube_license = "under terms of CC BY 3.0"
        replace_nld = True # replace no license with {{YouTube CC-BY|ChannelName}}

    edit_summary = "%s LR Passed, %s, by %s (%s) %s at www.youtube.com/watch?v=%s (Archived - WayBack Machine)" % (
        trusted_text_append,
        youtube_video_title,
        youtube_channel_name,
        youtube_channel_id,
        youtube_license,
        youtube_video_id,
        )


    new_text = auto_fill(
        "YouTube",
        old_text,
        ("{{From YouTube|1=%s|2=%s}}" % (youtube_video_id, youtube_video_title)),
        ("[https://www.youtube.com/channel/%s %s]" % (youtube_channel_id, youtube_channel_name)),
        youtube_video_title,
        upload_date,
        description,
        replace_nld
        )


    if not re.search(r"Creative Commons", license) and not check_channel(youtube_channel_id) == "Trusted":
        reason = "Video is not licensed Creative Commons on YouTube also not from a trusted channel."
        out(reason ,color="red")
        dump_file(filename, reason)
        return

    new_text = re.sub(
        REGEX_OF_LICENSE_REVIEW_TEMPLATE,
        TAGS,
        new_text,
        )

    if new_text == old_text:
        out("IGONRE - New text was equal to Old text.", color="red")
        dump_file(filename, reason)
        return

    try:
        commit(
            old_text,
            new_text,
            page,
            edit_summary,
            )

    except pywikibot.LockedPage as error:
        out(
            "Page is locked '%s'." % error,
            color='red',
            )
        return

def handle_vimeo(source_area, page, filename, old_text):
    try:
        VimeoVideoId = re.search(r"{{\s*?[Ff]rom\s[Vv]imeo\s*(?:\||\|1\=|\s*?)(?:\s*)(?:1\=|)(?:\s*?|)([0-9_]+)", source_area).group(1)
    except AttributeError:
        try:
            VimeoVideoId = re.search(r"vimeo\.com\/((?:[0-9_]+))", source_area).group(1)
        except AttributeError:
            reason = "PARSING FAILED - Can't get VimeoVideoId"
            out(reason, color='red')
            dump_file(filename, reason)
            return

    source_url = "https://vimeo.com/%s" % VimeoVideoId
    user_agent = USER_AGENT

    try:
        archive_url = str(waybackpy.Url(source_url, user_agent).oldest())
    except Exception:
        try:
            archive_url = str(waybackpy.Url(source_url, user_agent).save())
        except Exception as e:
            dump_file(filename, e)
            out(e, color="red")
            return

    try:
        webpage = waybackpy.Url(source_url, user_agent).get()
    except Exception as e:
        reason = "Unable to get source code of %s" % source_url
        out(e, color="red")
        dump_file(filename, reason)
        return


    # Try to get the ChannelID
    try:
        vimeo_channel_id = re.search(r"http(?:s|)\:\/\/vimeo\.com\/(user[0-9]{0,30})\/video", webpage).group(1)
    except AttributeError:
        try:
            vimeo_channel_id = re.search(r"https://vimeo\.com/([^:/\"]{0,250}?)/videos\"", webpage).group(1)
        except AttributeError:
            reason = "PARSING FAILED - Can't get vimeo_channel_id"
            out(reason, color='red')
            dump_file(filename, reason)
            return

    # If bad Channel do not review it, we do not support trusted Channel for vimeo yet.
    if check_channel(vimeo_channel_id) == "Bad":
        reason = "DUMP - %s is from a shady channel %s" % (filename, vimeo_channel_id)
        out(reason, color="red")
        dump_file(filename, reason)
        return

    # Try to get video title
    try:
        vimeo_video_title = re.search(r"<title>(.*?) on Vimeo<\/title>", webpage, re.MULTILINE).group(1)
    except AttributeError:
        reason = "PARSING FAILED - Can't get vimeo_video_title"
        out(reason, color='red')
        dump_file(filename, reason)
        return

    if not re.search(r"creativecommons.org", webpage):
        reason = "File is not licensed under any type of creative commons\
        license including CC-NC/ND"
        out(reason, color='red')
        dump_file(filename, reason)
        return

    standard_creative_commons_url_regex = re.compile('https\:\/\/creativecommons\.org\/licenses\/(.*?)\/(.*?)\/')
    matches = standard_creative_commons_url_regex.finditer(webpage)
    for m in matches:
        license_part_one, license_part_two  = (m.group(1)), (m.group(2))
    vimeo_license = license_part_one + "-" + license_part_two
    allowed_licenses = [
        'by-sa',
        'by',
        'publicdomain',
        'cc0',
        ]
    if license_part_one not in allowed_licenses:
        reason = "Licensed under %s, and isn't valid on wikimedia commons" % vimeo_license
        out(reason, color="red")
        dump_file(filename, reason)
        return

    TAGS = "{{VimeoReview|id=%s|title=%s|license=%s|ChannelID=%s|archive=%s|date=%s}}" % (
        VimeoVideoId,
        vimeo_video_title,
        vimeo_license,
        vimeo_channel_id,
        archive_url,
        informatdate(),
        )

    #Out puts some basic info about the video.
    display_video_info(VimeoVideoId, vimeo_channel_id, vimeo_video_title, archive_url)

    new_text = re.sub(REGEX_OF_LICENSE_REVIEW_TEMPLATE, TAGS, old_text)

    edit_summary = "LR Passed, %s , by %s under terms of %s at https://vimeo.com/%s (Archived\
    - WayBack Machine)" % (vimeo_video_title, vimeo_channel_id, vimeo_license, VimeoVideoId)

    try:
        commit(
            old_text,
            new_text,
            page,
            edit_summary
            )
    except pywikibot.LockedPage as error:
        out("Page is locked '%s'." % error, color='red')
        return


#######################   HANDLER FUNCTIONS END  ###############################

def checkfiles():
    category = pywikibot.Category(
        SITE,
        'License_review_needed_(video)',
        )

    gen = pagegenerators.CategorizedPageGenerator(category)
    file_count = 0
    dump_hell = pywikibot.Page(SITE,"User:YouTubeReviewBot/dump3",).get(get_redirect=True)
    for page in gen:
        file_count += 1
        filename = page.title()

        out("\n%d - %s" % (
        file_count,
        filename,
        ), color="white" )

        if filename in dump_hell:
            out("IGNORE - File dumped for 3rd time.", color='red')
            continue

        if (datetime.utcnow() - last_edit_time(filename)).days > 30:
            reason = "File could not be reviwed and no changes made to file in last 30 days."
            out(reason, color='red')
            dump_file(filename, reason)
            continue

        page = pywikibot.Page(SITE, filename)
        old_text = pagetext = page.get()

        source_area = None
        try:
            source_area = re.search("\|[Ss]ource=(.*)", pagetext).group(1)
        except AttributeError:
            source_area = pagetext #If we found empty source param we treat the full page as source

        if source_area.isspace(): #check if it's just newlines tabs and spaces.
            source_area = pagetext


        if is_marked_for_deletion(pagetext) is True:
            out("IGNORE - File is marked for deletion", color='red')
            continue

        identified_site = detect_source_site((source_area.lower()))
        out("A file from %s." % identified_site, color="yellow")
        if not identified_site and not is_own_work(pagetext):
            reason = "Skipping cuz source unidentified and not ownwork."
            out(reason, color="yellow")
            dump_file(filename, reason)
            continue

        elif identified_site == "VideoWiki":
            handle_videowiki(page, filename, old_text)

        elif identified_site == "Flickr":
            handle_flickr(page, filename, old_text)

        elif identified_site == "Vimeo":
            p = multiprocessing.Process(target=handle_vimeo, name="handle_vimeo", args=(source_area, page, filename, old_text))
            p.start()
            p.join(300) #2 minutes
            if p.is_alive():
                # Terminate handle_youtube
                p.terminate()
                p.join()

        elif identified_site == "YouTube":
            # handle_youtube(source_area, page, filename, old_text)
            p = multiprocessing.Process(target=handle_youtube, name="handle_youtube", args=(source_area, page, filename, old_text))
            p.start()
            p.join(300) #3 minutes
            if p.is_alive():
                # Terminate handle_youtube
                p.terminate()
                p.join()

        elif is_own_work(pagetext):
            handle_ownwork(page, filename, old_text)

        else:
            continue

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
    SITE = pywikibot.Site("commons", "commons")

    if DRY is not True:
        if not SITE.logged_in():
            SITE.login()

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
