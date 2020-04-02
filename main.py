# -*- coding: utf-8 -*-
import re
import sys
import pywikibot
import savepagenow
from datetime import datetime
from pywikibot import pagegenerators
from urllib.request import Request, urlopen


def uploader(filename, link=True):
    """user that uploaded the video"""
    history = (pywikibot.Page(SITE, filename)).getVersionHistory(reverse=True, total=1)
    if not history:
        return "Unknown"
    if link:
        return "[[User:%s|%s]]" % (history[0][2], history[0][2])
    else:
        return history[0][2]

def isOwnWork(pagetext):
    if (LowerCasePageText.find('{{own}}') != -1):
        return True
    elif (LowerCasePageText.find('own work') != -1):
        return True

def informatdate():
    return (datetime.utcnow()).strftime('%Y-%m-%d')

def IsMarkedForDeletion(pagetext):
    LowerCasePageText = pagetext.lower()
    if (
        (LowerCasePageText.find('{{No permission since') != -1) or
        (LowerCasePageText.find('{{delete') != -1) or
        (LowerCasePageText.find('{{copyvio') != -1) or
        (LowerCasePageText.find('{{speedy') != -1)
        ):
            return True

def DetectSite():
    if (LowerCasePageText.find('{{from vimeo') != -1):
        return "Vimeo"
    if (LowerCasePageText.find('{{from youtube') != -1):
        return "YouTube"
    elif (LowerCasePageText.find('flickr.com/photos') != -1):
        return "Flickr"
    elif (LowerCasePageText.find('vimeo.com') != -1):
        return "Vimeo"
    elif (LowerCasePageText.find('youtube.com') != -1):
        return "YouTube"

def archived_url(SourceURL):
    archive_url = None
    status = "Wait"
    iters = 0
    while status == "Wait":
        iters = iters + 1
        try:
            archive_url = savepagenow.capture(SourceURL)
            status = "Done"
        except:
            pass
        if iters > 5:
            status = "Stop"
    return archive_url

def archived_webpage(archive_url):
    webpage = None
    status = "Wait"
    iters = 0
    while status == "Wait":
        iters = iters + 1
        try:
            req = Request(archive_url,headers={'User-Agent': 'User:YouTubeReviewBot on wikimedia commons'})
            webpage = urlopen(req).read().decode('utf-8')
            status = "Done"
        except:
            pass
        if iters > 5:
            status = "Stop"
    return webpage

def check_channel(ChannelId):
    if ChannelId in (pywikibot.Page(SITE, "User:YouTubeReviewBot/Trusted")).get(get_redirect=True, force=True):
        return "Trusted"
    elif ChannelId in (pywikibot.Page(SITE, "User:YouTubeReviewBot/bad-authors")).get(get_redirect=True, force=True):
        return "Bad"
    else:
        return "Normal"

def OwnWork():
    if (LowerCasePageText.find('{{own}}') != -1):
        return True
    elif (LowerCasePageText.find('own work') != -1):
        return True
    else:
        return False

def ChannelChk(ChannelId):
    PageOfTrustedChannelId = pywikibot.Page(SITE, "User:YouTubeReviewBot/Trusted")
    TextOfPageOfTrustedChannelId = PageOfTrustedChannelId.get(get_redirect=True, force=True)
    if (TextOfPageOfTrustedChannelId.find(ChannelId) != -1):
        return "Trusted"
    PageOfBadChannelId = pywikibot.Page(SITE, "User:YouTubeReviewBot/bad-authors")
    TextOfPageOfBadChannelId = PageOfBadChannelId.get(get_redirect=True, force=True)
    if (TextOfPageOfBadChannelId.find(ChannelId) != -1):
        return "Bad"
    return "Unknown"

def commit(old_text, new_text, page, summary):
    """Show diff and submit text to page."""
    yes = {'yes','y', 'ye', ''}
    quit = {'q','quit','exit'}
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
        pywikibot.showDiff(old_text, new_text)
        page.put(new_text, summary=summary, watchArticle=True, minorEdit=False)
    elif choice in quit:
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
    pywikibot.stdout("%s%s" % (dstr, text), newline=newline)

def checkfiles():
    category = pywikibot.Category(SITE,'License_review_needed_(video)')
    RegexOfLicenseReviewTemplate = r"{{(?:|\s*)[LlVvYy][IiOo][CcMmUu][EeTt][NnUuOo](?:[SsBbCc][Ee]|)(?:|\s*)[Rr][Ee][Vv][Ii][Ee][Ww](?:|\s*)(?:\|.*|)}}"
    gen = pagegenerators.CategorizedPageGenerator(category)
    file_count = 0
    for page in gen:
        file_count = 1 + file_count
        filename = page.title()
        out("\n%d - %s" % (file_count,filename), color="white")
        page = pywikibot.Page(SITE, filename)
        pagetext = page.get(get_redirect=True)
        old_text = pagetext
        global LowerCasePageText
        LowerCasePageText = pagetext.lower()
        out("Identified as %s" % DetectSite(), color="yellow")
        if IsMarkedForDeletion(pagetext) == True:
            out("IGNORE - File is marked for deletion", color='red')
            continue

        elif OwnWork():
            new_text = re.sub(RegexOfLicenseReviewTemplate, "" , old_text)
            EditSummary = "@%s Removing licenseReview Template, not required for ownwork." % uploader(filename,link=True)
            try:
                commit(old_text, new_text, page, EditSummary)
            except pywikibot.LockedPage as error:
                out("Page is locked '%s'." % error, color='red')
                continue

        elif DetectSite() == "Flickr":
            new_text = re.sub(RegexOfLicenseReviewTemplate, "{{FlickrReview}}" , old_text)
            EditSummary = "@%s Marking for flickr review, file added to [[Category:Flickr videos review needed]]." % uploader(filename,link=True)
            try:
                commit(old_text, new_text, page, EditSummary)
            except pywikibot.LockedPage as error:
                out("Page is locked '%s'." % error, color='red')
                continue

        elif DetectSite() == "Vimeo":
            VimeoUrlPattern = re.compile(r'vimeo\.com\/((?:[0-9_]+))')
            FromVimeoRegex = re.compile(r'{{\s*?[Ff]rom\s[Vv]imeo\s*(?:\||\|1\=|\s*?)(?:\s*)(?:1\=|)(?:\s*?|)([0-9_]+)')
            try:
                VimeoVideoId = re.search(r"{{\s*?[Ff]rom\s[Vv]imeo\s*(?:\||\|1\=|\s*?)(?:\s*)(?:1\=|)(?:\s*?|)([0-9_]+)",pagetext).group(1)
            except AttributeError:
                try:
                    VimeoVideoId = re.search(r"vimeo\.com\/((?:[0-9_]+))",pagetext).group(1)
                except:
                    out("PARSING FAILED - Can't get VimeoVideoId", color='red')
                    continue
            SourceURL = "https://vimeo.com/%s" % VimeoVideoId

            if archived_url(SourceURL) != None:
                archive_url = archived_url(SourceURL)
            else:
                out("WAYBACK FAILED - Can't get archive_url", color='red')
                continue

            if archived_webpage(archive_url) == None:
                out("WAYBACK FAILED - Can't get webpage", color='red')
                continue
            else:
                webpage = archived_webpage(archive_url)
            
            # Try to get the ChannelID
            try:
                VimeoChannelId = re.search(r"http(?:s|)\:\/\/vimeo\.com\/(user[0-9]{0,30})\/video", webpage, re.MULTILINE).group(1)
            except:
                out("PARSING FAILED - Can't get VimeoChannelId", color='red')
                continue
            if check_channel(VimeoChannelId) == "Trusted":pass  #TODO : PASS LR similar as YouTube

            if check_channel(VimeoChannelId) == "Bad":
                out("IGNORE - Bad Channel %s" % VimeoChannelId, color="red")
                continue
            
            # Try to get video title
            try:
                VimeoVideoTitle = re.search(r"<title>(.*?) on Vimeo<\/title>", webpage, re.MULTILINE).group(1)
            except:
                out("PARSING FAILED - Can't get VimeoVideoTitle", color='red')
                continue

            StandardCreativeCommonsUrlRegex = re.compile('https\:\/\/creativecommons\.org\/licenses\/(.*?)\/(.*?)\/')

            Allowedlicenses = [
                'by-sa',
                'by',
                'publicdomain',
                'cc0'
                ]

            if re.search(r"creativecommons.org", webpage):
                matches = StandardCreativeCommonsUrlRegex.finditer(webpage)
                for m in matches:
                    licensesP1, licensesP2  = (m.group(1)), (m.group(2))
                if licensesP1 not in Allowedlicenses:
                    out("The file is licensed under %-%, but it's not allowed on commons" % (licensesP1,licensesP2) , color="red")
                    continue
                else:pass
            else:
                out(
                    "Creative commons Not found - File is not licensed under any type of creative commons license including CC-NC/ND",
                    color='red'
                    )
                continue

            new_text = re.sub(RegexOfLicenseReviewTemplate, "{{VimeoReview|id=%s|license=%s-%s|ChannelID=%s|archive=%s|date=%s}}" % (
                VimeoVideoId,
                licensesP1,
                licensesP2,
                VimeoChannelId,
                archive_url,
                informatdate()),
                old_text)

            EditSummary = "LR Passed, %s , by %s under terms of %-% at https://vimeo.com/%s (Archived - WayBack Machine)" % (
                VimeoVideoTitle,
                VimeoChannelId,
                licensesP1,
                licensesP2,
                VimeoVideoId,
                )

            try:
                commit(old_text, new_text, page, EditSummary)
            except pywikibot.LockedPage as error:
                out("Page is locked '%s'." % error, color='red')
                continue

        elif DetectSite() == "YouTube":
            try:
                YouTubeVideoId = re.search(r"{{\s*?[Ff]rom\s[Yy]ou[Tt]ube\s*(?:\||\|1\=|\s*?)(?:\s*)(?:1|=\||)(?:=|)([^\"&?\/ ]{11})",pagetext).group(1)
            except AttributeError:
                try:
                    YouTubeVideoId = re.search(r"https?\:\/\/(?:www|m|)(?:|\.)youtube\.com/watch\Wv\=([^\"&?\/ ]{11})",pagetext).group(1)
                except:
                    out("PARSING FAILED - Can't get YouTubeVideoId", color='red')
                    continue
            SourceURL = "https://www.youtube.com/watch?v=%s" % YouTubeVideoId
            if archived_url(SourceURL) != None:
                archive_url = archived_url(SourceURL)
            else:
                out("WAYBACK FAILED - Can't get archive_url", color='red')
                continue
            if archived_webpage(archive_url) == None:
                out("WAYBACK FAILED - Can't get webpage", color='red')
                continue
            else:
                webpage = archived_webpage(archive_url)
            if ((
                webpage.find('YouTube account associated with this video has been terminated') or
                webpage.find('playerErrorMessageRenderer') or
                webpage.find('Video unavailable') or
                webpage.find('If the owner of this video has granted you access') or
                (webpage.find('player-unavailable') and webpage.find('Sorry about that'))
                ) != -1):
                    not_available_page = pywikibot.Page(
                        SITE,
                        ("User:YouTubeReviewBot/Video not available on YouTube and marked for license review/%s" % (datetime.utcnow()).strftime('%B %Y')),
                        )

                    try:
                        not_available_old_text = not_available_page.get(get_redirect=True, force=True)
                    except pywikibot.NoPage:
                        not_available_old_text = "<gallery>\n</gallery>"

                    if (not_available_old_text.find(filename) != -1):
                        continue
                    else:pass

                    not_available_new_text = re.sub("</gallery>", "%s|Uploader Name : %s <br> video url : %s <br> oldest archive : %s \n</gallery>" % ( filename, uploader(filename,link=True), OriginalURL , oldest_archive_url) , not_available_old_text)
                    EditSummary = "Adding [[%s]], was uploaded by %s" % (filename, uploader(filename,link=True))
                    try:
                        commit(not_available_old_text, not_available_new_text, not_available_page, EditSummary)
                    except pywikibot.LockedPage as error:
                        out("Page is locked '%s'." % error, color='red')
                        continue
            else:
                pass
            YouTubeChannelIdRegex1 = r"data-channel-external-id=\"(.{0,30})\""
            YouTubeChannelIdRegex2 = r"[\"']externalChannelId[\"']:[\"']([a-zA-Z0-9_-]{0,25})[\"']"
            YouTubeChannelNameRegex1 = r"\\\",\\\"author\\\":\\\"(.{1,50})\\\",\\\""
            YouTubeChannelNameRegex2 = r"\"ownerChannelName\\\":\\\"(.{1,50})\\\","
            #YouTubeChannelNameRegex3 = r"Unsubscribe from ([^<{]*?)\?"
            YouTubeVideoTitleRegex1 = r"\"title\":\"(.{1,160})\",\"length"
            YouTubeVideoTitleRegex2 = r"<title>(?:\s*|)(.{1,250})(?:\s*|)- YouTube(?:\s*|)</title>"

            # try to get channel Id
            try:
                YouTubeChannelId = re.search(YouTubeChannelIdRegex1,webpage).group(1)
            except AttributeError:
                try:
                    YouTubeChannelId = re.search(YouTubeChannelIdRegex2,webpage).group(1)
                except AttributeError:
                    out("PARSING FAILED - Can't get YouTubeChannelId", color='red')
                    continue

            if ChannelChk(YouTubeChannelId) == "Bad":
                out("IGONRE - Bad Channel %s" % YouTubeChannelId , color="red")
                continue

            # try to get Channel name
            try:
                YouTubeChannelName  = re.search(YouTubeChannelNameRegex1,webpage).group(1)
            except AttributeError:
                try:
                    YouTubeChannelName  = re.search(YouTubeChannelNameRegex2,webpage).group(1)
                except AttributeError:
                    out("PARSING FAILED - Can't get YouTubeChannelName", color='red')
                    continue

            # try to get YouTube Video's Title
            try:
                YouTubeVideoTitle   = re.search(YouTubeVideoTitleRegex1,webpage).group(1)
            except AttributeError:
                try:
                    YouTubeVideoTitle   = re.search(YouTubeVideoTitleRegex2,webpage).group(1)
                except AttributeError:
                    out("PARSING FAILED - Can't get YouTubeVideoTitle", color='red')
                    continue

            # Remove unwanted sysmbols that may fuck-up the wiki-text, if present in Video title or Channel Name
            YouTubeChannelName = re.sub(r'[{}\|\+\]\[]', r'-', YouTubeChannelName)
            YouTubeVideoTitle  = re.sub(r'[{}\|\+\]\[]', r'-', YouTubeVideoTitle)

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

            out(
                str(
                "video Id : " + YouTubeVideoId + 
                "\nChannel Name : " + YouTubeChannelName + 
                "\nChannel Id : " + YouTubeChannelId +
                "\nVideo Title : " + YouTubeVideoTitle + 
                "\nArchive : " + archive_url +
                "\nDate : " + informatdate()),
                color="white",
                )

            if ChannelChk(YouTubeChannelId) == "Trusted":
                TrustTextAppend = "[[User:YouTubeReviewBot/Trusted|✔️ - Trusted YouTube Channel of  %s ]]" %  YouTubeChannelName
                YouTubeLicense = ""
            else:
                TrustTextAppend = ""
                YouTubeLicense = "under terms of CC BY 3.0"

            EditSummary = "%s LR Passed, %s, by %s (%s) %s at www.youtube.com/watch?v=%s (Archived - WayBack Machine)" % (
                TrustTextAppend,
                YouTubeVideoTitle,
                YouTubeChannelName,
                YouTubeChannelId,
                YouTubeLicense,
                YouTubeVideoId,
                )

            if re.search(r"Creative Commons", webpage) is not None or ChannelChk(YouTubeChannelId) == "Trusted":
                new_text = re.sub(RegexOfLicenseReviewTemplate, TAGS, old_text)
            else:
                out("Video is not Creative Commons 3.0 licensed on YouTube nor from a Trusted Channel", color="red")
                continue
            if new_text == old_text:
                out("IGONRE - New text was equal to Old text.", color="red")
                continue
            else:
                pass
            try:
                commit(old_text, new_text, page, EditSummary)
            except pywikibot.LockedPage as error:
                out("Page is locked '%s'." % error, color='red')
                continue
        else:
            continue

def main(*args):
    global SITE
    global DRY
    global AUTO
    DRY = None
    AUTO = None
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
    if not SITE.logged_in():
        SITE.login()
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
            
    
    checkfiles()

if __name__ == "__main__":
    try:
        main()
    finally:
        pywikibot.stopme()
