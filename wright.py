# -*- coding: utf-8 -*-
import os, sys, re, time, gzip
import io
import urllib
from bs4 import BeautifulSoup
import shutil
import csv
from tempfile import NamedTemporaryFile
import subprocess
from finefun import *
from cryptography.fernet import Fernet
from urllib.parse import urlencode, quote_plus
import html
import simplejson as json
import unidecode



emailIdPattern = re.compile(r"\W(\w+\.?\w{0,}@\w+\.\w+\.?\w*)\W", re.MULTILINE | re.DOTALL)
absUrlPattern = re.compile(r"^https?:\/\/", re.IGNORECASE)
anchorTagPattern = re.compile(r"<a\s+[^>]{0,}href=([^\s\>]+)\s?.*?>\s*\w+", re.IGNORECASE | re.MULTILINE | re.DOTALL)
doubleQuotePattern = re.compile('"', re.MULTILINE | re.DOTALL)
htmlTagPattern = re.compile("\<\/?[^\<\>]*\/?\>", re.DOTALL)
newlinePattern = re.compile(r"\n")
multipleWhitespacePattern = re.compile(r"\s+")
pathEndingWithSlashPattern = re.compile(r"\/$")
javascriptUrlPattern = re.compile("^javascript:")
startsWithSlashPattern = re.compile("^/")
htmlEntitiesDict = {'&nbsp;' : ' ', '&#160;' : ' ', '&amp;' : '&', '&#038;' : '&', '&lt;' : '<', '&#60;' : '<', '&gt;' : '>', '&#62;' : '>', '&apos;' : '\'', '&#39;' : '\'', '&quot;' : '"', '&#34;' : '"', '&#8211;' : '-', '&ndash;' : '-' }
httpHeaders = { 'User-Agent' : r'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36',  'Accept' : 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8', 'Accept-Language' : 'en-US,en;q=0.8', 'Accept-Encoding' : 'gzip,deflate,sdch', 'Accept-Charset' : 'ISO-8859-1,utf-8;q=0.7,*;q=0.3', 'Connection' : 'keep-alive'}


def decodeGzippedContent(encoded_content):
    response_stream = io.BytesIO(encoded_content)
    decoded_content = ""
    try:
        gzipper = gzip.GzipFile(fileobj=response_stream)
        decoded_content = gzipper.read()
    except: # Maybe this isn't gzipped content after all....
        decoded_content = encoded_content
    decoded_content = decoded_content.decode('utf-8')
    return decoded_content


def stripHtmlEntities(content):
    for entityKey in htmlEntitiesDict.keys():
        entityKeyPattern = re.compile(entityKey)
        content = re.sub(entityKeyPattern, htmlEntitiesDict[entityKey], content)
    return content


def isAbsoluteUrl(url):
    s = absUrlPattern.search(url)
    if s:
        return True
    else:
        return False


def updatestatus(auctionno, auctionurl):
    auctionurl = auctionurl.replace("%3A", ":")
    auctionurl = auctionurl.replace("%2F", "/")
    pageurl = "http://216.137.189.57:8080/scrapers/finish/?scrapername=Wright&auctionnumber=%s&auctionurl=%s&scrapertype=2"%(auctionno, urllib.parse.quote(auctionurl))
    pageResponse = None
    try:
        pageResponse = urllib.request.urlopen(pageurl)
    except:
        print ("Error: %s"%sys.exc_info()[1].__str__()) 


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def http_error_302(self, req, fp, code, msg, headers):
        infourl = urllib.response.addinfourl(fp, headers, req.get_full_url())
        infourl.status = code
        infourl.code = code
        return infourl

    http_error_300 = http_error_302
    http_error_301 = http_error_302
    http_error_303 = http_error_302
    http_error_307 = http_error_302


def _getCookieFromResponse(lastHttpResponse):
    cookies = ""
    lastResponseHeaders = lastHttpResponse.info()
    responseCookies = lastHttpResponse.info().getheaders("Set-Cookie")
    pathCommaPattern = re.compile(r"path=/,", re.IGNORECASE)
    domainPattern = re.compile(r"Domain=[^;]+;", re.IGNORECASE)
    expiresPattern = re.compile(r"Expires=[^;]+;", re.IGNORECASE)
    if responseCookies.__len__() > 1:
        for cookie in responseCookies:
            cookieParts = cookie.split("Path=/")
            cookieParts[0] = re.sub(domainPattern, "", cookieParts[0])
            cookieParts[0] = re.sub(expiresPattern, "", cookieParts[0])
            cookies += cookieParts[0]
        return(cookies)
    else:
        if "Set-Cookie" in lastResponseHeaders.keys():
            cookieValue = lastResponseHeaders.get("Set-Cookie")
            cookieLines = cookieValue.split("\r\n")
            if pathCommaPattern.search(cookieValue):
                cookieLines = cookieValue.split("path=/,")
            deletedPattern = re.compile("deleted", re.IGNORECASE)
            for line in cookieLines:
                if deletedPattern.search(line):
                    continue
                cookieParts = line.split(";")
                cookies += cookieParts[0].__str__() + ";"
            cookies.strip()
            cookies = cookies[:-1]
        return cookies


def stripHTML(dataitem):
    dataitem = re.sub(htmlTagPattern, "", dataitem) # stripped off all HTML tags...
    # Handle HTML entities...
    for entity in htmlEntitiesDict.keys():
        dataitem = dataitem.replace(entity, htmlEntitiesDict[entity])
    return dataitem


def cleanhtml(raw_html):
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', raw_html)
    return cleantext


def quoteText(content):
    content = str(stripHtmlEntities(content))
    content = content.replace('"', '\"')
    content = '"' + content + '"'
    return content

def formatDate(datestr):
    mondict = {'January' : '01', 'February' : '02', 'March' : '03', 'April' : '04', 'May' : '05', 'June' : '06', 'July' : '07', 'August' : '08', 'September' : '09', 'October' : '10', 'November' : '11', 'December' : '12' }
    mondict3 = {'jan.' : '01', 'fév.' : '02', 'mar.' : '03', 'avr.' : '04', 'mai.' : '05', 'jui.' : '06', 'jul.' : '07', 'aoû.' : '08', 'sep.' : '09', 'oct.' : '10', 'nov.' : '11', 'déc.' : '12' }
    datestrcomponents = datestr.split(" ")
    dd = str(datestrcomponents[0])
    mmm = datestrcomponents[1][:3]
    yyyy = str(datestrcomponents[2][2:])
    retdate = dd + "-" + mmm + "-" + yyyy
    return retdate

def encryptFilename(filename):
    k = Fernet.generate_key()
    f = Fernet(k)
    encfilename = f.encrypt(filename.encode())
    return encfilename


def renameImageFile(basepath, imagefilename, mappedImagename):
    oldfilename = basepath + "/" + imagefilename
    newfilename = basepath + "/" + mappedImagename
    newfilename = newfilename.replace("'", "")
    try:
        os.rename(oldfilename, newfilename)
    except:
        pass


def getImagenameFromUrl(imageUrl):
    urlparts = imageUrl.split("/")
    imagefilepart = urlparts[-1]
    imagefilenameparts = imagefilepart.split("?")
    imagefilename = imagefilenameparts[0]
    return imagefilename


def getImage(imageUrl, imagepath, downloadimages):
    imageUrlParts = imageUrl.split("/")
    imagefilename = imageUrlParts[-1]
    opener = urllib.request.build_opener()
    if downloadimages == "1":
        pageRequest = urllib.request.Request(imageUrl, headers=httpHeaders)
        pageResponse = None
        try:
            pageResponse = opener.open(pageRequest)
        except:
            print ("Error: %s"%sys.exc_info()[1].__str__())
        try:
            imageContent = pageResponse.read()
            ifp = open(imagepath + os.path.sep + imagefilename, "wb")
            ifp.write(imageContent)
            ifp.close()
        except:
            print("Error: %s"%sys.exc_info()[1].__str__())



if __name__ == "__main__":
    if sys.argv.__len__() < 5:
        print("Insufficient parameters")
        sys.exit()
    auctionurl = sys.argv[1]
    auctionnumber = sys.argv[2]
    csvpath = sys.argv[3]
    imagepath = sys.argv[4]
    downloadImages = 0
    convertfractions = 0
    if sys.argv.__len__() > 5:
        downloadImages = sys.argv[5]
    if sys.argv.__len__() > 6:
        convertfractions = sys.argv[6]
    auctionNum = auctionnumber # This is actually the name of the auction as this site doesn't have any Id associated with any auction.
    requestUrl = auctionurl # Online auctions #requestUrl="https://www.wright20.com/auctions/2018/01/important-italian-glass"
    auctionNumList = requestUrl.split("/")
    domainUrl = "https://www.wright20.com"
    domainUrl = re.sub(pathEndingWithSlashPattern, "", domainUrl)
    print("Initializing...\n")
    opener = urllib.request.build_opener()
    no_redirect_opener = urllib.request.build_opener(urllib.request.HTTPHandler(), urllib.request.HTTPSHandler(), NoRedirectHandler())
    debug_opener = urllib.request.build_opener(urllib.request.HTTPHandler(debuglevel=1))
    sessionCookies = ""
    endslashPattern = re.compile("/$")
    infourl = auctionurl + "/info"
    if re.search(endslashPattern, auctionurl):
        infourl = auctionurl + "info"
    inforequest = urllib.request.Request(infourl, None, httpHeaders)
    infocontent = ""
    auctionlocation = ""
    try:
        inforesponse = opener.open(inforequest)
        infocontent = decodeGzippedContent(inforesponse.read())
    except:
        pass
    infosoup = BeautifulSoup(infocontent, features="html.parser")
    h4tags = infosoup.find_all("h4", {'class' : 'text-center'})
    if h4tags.__len__() > 1:
        h4contents = h4tags[1].renderContents().decode('utf-8')
        locPattern = re.compile("at\s+Rago\s+in\s+([\w\s,\.]+)\.", re.IGNORECASE|re.DOTALL)
        lps = re.search(locPattern, h4contents)
        if lps:
            auctionlocation = lps.groups()[0]
    auctionlocation = "Chicago"
    pageRequest = urllib.request.Request(requestUrl, None, httpHeaders)
    pageResponse = None
    postData = {}
    try:
        pageResponse = opener.open(pageRequest)
        headers = pageResponse.info()
        while "Location" in headers.keys():
            requestUrl = headers["Location"]
            print("Redirecting to %s...\n"%requestUrl)
            pageRequest = urllib.request.Request(requestUrl, None, httpHeaders)
            try:
                pageResponse = opener.open(pageRequest)
                headers = pageResponse.info()
            except:
                print("Couldn't fetch page.... Error: %s!\n"%sys.exc_info()[1].__str__())
                sys.exit()
    except:
        print("Could not fetch page.... Error: %s!\n"%sys.exc_info()[1].__str__())
        sys.exit()
    pageContent = decodeGzippedContent(pageResponse.read())
    soup = BeautifulSoup(pageContent, features="html.parser")
    lotCount = len(soup.findAll("div", {'class' : re.compile('^item  w1  h1  ')}))
    allAuctionsDivTags = soup.find_all("header")
    auctionsDict = {}
    if downloadImages:
        imageDir = imagepath
    matcatdict_en = {}
    matcatdict_fr = {}
    with open("/root/artwork/deploydirnew/docs/fineart_materials.csv", newline='') as mapfile:
    #with open("docs/fineart_materials.csv", newline='') as mapfile:
        mapreader = csv.reader(mapfile, delimiter=",", quotechar='"')
        for maprow in mapreader:
            matcatdict_en[maprow[1]] = maprow[3]
            matcatdict_fr[maprow[2]] = maprow[3]
    mapfile.close()
    allAuctionsDiv = allAuctionsDivTags[0]
    if not allAuctionsDiv:
        print("Could not find any auctions div... Quitting!")
        exit()
    auctionNameh1tag=allAuctionsDiv.find('h1')
    if auctionNameh1tag is not None:
        auctionName = auctionNameh1tag.renderContents().decode('utf-8')
        auctionName = htmlTagPattern.sub("", auctionName)
        auctionName = auctionName.replace("\n", "").replace("\r", "")
    auctiondatePattern = re.compile("(\d{1,2}\s+\w+\s+\d{4})")
    auctionDate = ""
    dps = re.search(auctiondatePattern, auctionName)
    if dps:
        auctionDate = dps.groups()[0]
        auctionDate = formatDate(auctionDate)
    auctionName = auctiondatePattern.sub("", auctionName)
    titletags = infosoup.find_all("title")
    if auctionDate == "" and titletags.__len__() > 0:
        titlecontents = titletags[0].renderContents().decode('utf-8')
        datePattern = re.compile("(\d{1,2})\s+(\w+)\s+(\d{4})", re.DOTALL)
        dps = re.search(datePattern, titlecontents)
        if dps:
            aucday = dps.groups()[0]
            aucmon = dps.groups()[1]
            aucyear = dps.groups()[2]
            auctionDate = aucday + " " + aucmon + " " + aucyear
            auctionDate = formatDate(auctionDate)
    timePattern = re.compile("\d{1,2}\s+\w{2}\s+\w{2}")
    auctionName = timePattern.sub("", auctionName)
    auctionName = auctionName.replace("&nbsp;", " ").replace("&amp;", "&")
    auctionName = auctionName.replace("/", "")
    fp = open(csvpath, "w")
    auctionInfoKeysList = ['auction_house_name', 'auction_location', 'auction_num', 'auction_start_date', 'auction_end_date', 'auction_name', 'lot_num', 'sublot_num', 'price_kind', 'price_estimate_min', 'price_estimate_max', 'price_sold', 'artist_name', 'artist_birth', 'artist_death', 'artist_nationality', 'artwork_name', 'artwork_year_identifier', 'artwork_start_year', 'artwork_end_year', 'artwork_materials', 'artwork_category', 'artwork_markings', 'artwork_edition', 'artwork_description', 'artwork_measurements_height', 'artwork_measurements_width', 'artwork_measurements_depth', 'artwork_size_notes', 'auction_measureunit', 'artwork_condition_in', 'artwork_provenance', 'artwork_exhibited', 'artwork_literature', 'artwork_images1', 'artwork_images2', 'artwork_images3', 'artwork_images4', 'artwork_images5', 'image1_name', 'image2_name', 'image3_name', 'image4_name', 'image5_name', 'lot_origin_url'] 
    fp.write(",".join(auctionInfoKeysList) + "\n")
    realizedPrice = "0"
    artistFirstName, artistLastName, yearOfBirth, yearOfDeath, material, yearDesigned, provenance, literature, condition, width, depth, height, diameter, length, lowLimit, highLimit, countryDesigned, idVal, priceType, scrapedDetails = "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "0", "Unknown", ""
    signture = ""
    exhibited = ""
    allProductsTags = soup.find_all("a", {'class' : 'mosaic-text'})
    lotList = []
    for prodTag in allProductsTags:
        lotnum, artistName, artTitle, lowhighLimits, itemLink = "", "", "", "", ""
        viewGrid = prodTag.find("div", {'class' : 'inner'}) 
        if viewGrid:
            dataimg = 'data-src'
            lotnoTag = prodTag.find("span", {'class' : 'lot_no'})
            lotnum = lotnoTag.renderContents().decode('utf-8')
            try:
                print("Scraping lot number %s\n"%lotnum)
            except:
                continue
            nameTag = prodTag.find("span", {'class' : 'name'})
            artistName = ""
            if nameTag:
                artistName = nameTag.renderContents().decode('utf-8')
            artTitle = prodTag.find("div", {'class' : 'title'}).renderContents().decode('utf-8')
            artTitle = htmlTagPattern.sub("", artTitle)
            artTitle = artTitle.replace("\n", "").replace("\r", "")
        else:
            dataimg = 'data-original'
            lotnoTag = prodTag.findNext("span", {'class' : 'lot_no'})
            try:
                lotnum = str(lotnoTag.getText())
                print("Scraping lot number %s\n"%lotnum)
            except:
                continue
            artistName = ""
            nameTag = prodTag.findNext("div", {'class' : 'title'})
            artistName = prodTag.findNext("span", {'class' : 'name'}).getText()
            artistName = artistName.encode('utf-8', 'ignore')
            artTitleTag = nameTag.find('p')
            artTitle = artTitleTag.getText()
        if "," in artTitle: 
            artTitleParts= artTitle.split(",")
            artTitle= artTitleParts[0]
        itemLink = domainUrl + prodTag['href']
        #print(lotnum + " ########## " + artistName + " ######## " + artTitle + " ###### " + lowhighLimits + " ####### " + itemLink + "\n")
        requestUrl = itemLink
        pageRequest = urllib.request.Request(requestUrl, None, httpHeaders)
        pageResponse = None
        try:
            pageResponse = opener.open(pageRequest)
            headers = pageResponse.info()
            while "Location" in headers.keys():
                requestUrl = headers["Location"]
                print("Redirecting to %s...\n"%requestUrl)
                pageRequest = urllib.request.Request(requestUrl, None, httpHeaders)
                try:
                    pageResponse = opener.open(pageRequest)
                    headers = pageResponse.info()
                except:
                    print("Couldn't fetch page.... aborting this URL - %s!\n"%sys.exc_info()[1].__str__())
                    break
        except:
            print("Could not fetch page.... %s!\n"%sys.exc_info()[1].__str__())
            continue
        artistnationality, artworkcategory, description, measureunit, artimages1, artimages2, artimages3, artimages4, artimages5 = "", "", "", "", "", "", "", "", ""
        imagename1, imagename2, imagename3, imagename4, imagename5 = "", "", "", "", ""
        birthyear, deathyear, startyear, endyear, material, width, depth, height, diameter, length = "", "", "", "", "", "", "", "", "", ""
        estimatelow, estimatehigh, soldprice, condition, provenance, literature, exhibition, markings, location = "", "", "", "", "", "", "", "", ""
        sizenote, measureunit, description, edition, sublot, pricekind = "", "", "", "", "", ""
        yearPattern = re.compile("(\d{4})\-")
        withdrawnPattern = re.compile("withdrawn", re.IGNORECASE|re.DOTALL)
        sizePattern1 = re.compile("([\d\.]+\s*x\s*[\d\.]+\s*x?\s*[\d\.]*)\s+([incm]{2})\.?")
        pageContent = decodeGzippedContent(pageResponse.read())
        lotdataPattern = re.compile("window\.lot_data_cache\s+=\s*(\{.*\}\}\});", re.DOTALL)
        ldps = re.search(lotdataPattern, pageContent)
        if ldps:
            ldcontent = ldps.groups()[0]
            zps1 = re.search(sizePattern1, ldcontent)
            if zps1:
                sizenote = zps1.groups()[0]
                measureunit = zps1.groups()[1]
            lddata = json.loads(ldcontent)
            lddict = lddata['lot_' + str(lotnum)]['item']
            artistnationality = lddict['country']
            #sublot = lddict['id']
            #print(artistnationality)
            year_of_birth = str(lddict['year_of_birth'])
            year_of_death = str(lddict['year_of_death'])
            if year_of_birth is not "":
                yps = re.search(yearPattern, year_of_birth)
                if yps:
                    birthyear = yps.groups()[0]
            if year_of_death is not "":
                yps = re.search(yearPattern, year_of_death)
                if yps:
                    deathyear = yps.groups()[0]
            year_produced = str(lddict['year_produced'])
            if year_produced is None:
                year_produced = str(lddict['year_designed'])
            startyear = year_produced
            if not startyear or startyear is None or startyear == "None":
                startyear = ""
            material = str(lddict['material'])
            width = str(lddict['width'])
            depth = str(lddict['depth'])
            if depth == 'None':
                depth = ""
            height = str(lddict['height'])
            diameter = str(lddict['diameter'])
            length = str(lddict['length'])
            estimatelow = str(lddict['estimate_low'])
            estimatehigh = str(lddict['estimate_high'])
            soldprice = str(lddict['result_amount'])
            condition = str(lddict['item_condition'])
            provenance = str(lddict['provenance'])
            literature = str(lddict['literature'])
            exhibition = str(lddict['exhibited'])
            markings = str(lddict['specifications'])
            location = str(lddict['location'])
            artimages1 = str(lddict['combined_media_list'][0]['data-zoom-src'])
            artimages1 = artimages1.replace("\\/", "/")
            processedAuctionTitle = auctionName.replace(" ", "_")
            processedArtistName = artistName.replace(" ", "_")
            processedArtistName = unidecode.unidecode(processedArtistName)
            processedArtworkName = artTitle.replace(" ", "_")
            #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + str(auctionNum) + "__" + str(lotnum) + "__" + str(sublot)
            newname1 = str(auctionNum) + "__" + processedArtistName + "__" + str(lotnum) + "_a"
            #encryptedFilename = encryptFilename(newname1)
            encryptedFilename = newname1
            imagepathparts = artimages1.split("/")
            origimagename1 = getImagenameFromUrl(artimages1)
            imagename1 = encryptedFilename + ".jpg"
            if downloadImages == "1":
                getImage(artimages1, imagepath, downloadImages)
                imagename1 = str(encryptedFilename) + "-a.jpg"
                imagename1 = imagename1.replace("b'", "").replace("'", "")
                renameImageFile(imagepath, origimagename1, imagename1)
            if lddict['combined_media_list'].__len__() > 1:
                artimages2 = str(lddict['combined_media_list'][1]['data-zoom-src'])
                artimages2 = artimages2.replace("\\/", "/")
            if lddict['combined_media_list'].__len__() > 2:
                artimages3 = str(lddict['combined_media_list'][2]['data-zoom-src'])
                artimages3 = artimages3.replace("\\/", "/")
            if lddict['combined_media_list'].__len__() > 3:
                artimages4 = str(lddict['combined_media_list'][3]['data-zoom-src'])
                artimages4 = artimages4.replace("\\/", "/")
            if lddict['combined_media_list'].__len__() > 4:
                artimages5 = str(lddict['combined_media_list'][4]['data-zoom-src'])
                artimages5 = artimages5.replace("\\/", "/")
            origimagename2 = getImagenameFromUrl(artimages2)
            imagename2 = str(encryptedFilename) + "-b.jpg"
            imagename2 = imagename2.replace("b'", "").replace("'", "")
            if downloadImages == "1" and artimages2 != "":
                getImage(artimages2, imagepath, downloadImages)
                renameImageFile(imagepath, origimagename2, imagename2)
            origimagename3 = getImagenameFromUrl(artimages3)
            imagename3 = str(encryptedFilename) + "-c.jpg"
            imagename3 = imagename3.replace("b'", "").replace("'", "")
            if downloadImages == "1" and artimages3 != "":
                getImage(artimages3, imagepath, downloadImages)
                renameImageFile(imagepath, origimagename3, imagename3)
            origimagename4 = getImagenameFromUrl(artimages4)
            imagename4 = str(encryptedFilename) + "-d.jpg"
            imagename4 = imagename4.replace("b'", "").replace("'", "")
            if downloadImages == "1" and artimages4 != "":
                getImage(artimages4, imagepath, downloadImages)
                renameImageFile(imagepath, origimagename4, imagename4)
            origimagename5 = getImagenameFromUrl(artimages5)
            imagename5 = str(encryptedFilename) + "-e.jpg"
            imagename5 = imagename5.replace("b'", "").replace("'", "")
            if downloadImages == "1" and artimages5 != "":
                getImage(artimages5, imagepath, downloadImages)
                renameImageFile(imagepath, origimagename5, imagename5)
            pricekind = "unknown"
            if re.search(withdrawnPattern, soldprice) or re.search(withdrawnPattern, estimatehigh):
                pricekind = "withdrawn"
            elif soldprice != "":
                pricekind = "price realized"
            elif estimatehigh != "":
                pricekind = "estimate"
            else:
                pass
            if soldprice == "" or soldprice == "0" or soldprice == 0:
                pricekind = "estimate"
            materialparts = material.split(" ")
            catfound = 0
            for matpart in materialparts:
                if matpart in ['in', 'on', 'of', 'the', 'from']:
                    continue
                try:
                    matPattern = re.compile(matpart, re.IGNORECASE|re.DOTALL)
                    for enkey in matcatdict_en.keys():
                        if re.search(matPattern, enkey):
                            artworkcategory = matcatdict_en[enkey]
                            catfound = 1
                            break
                    for frkey in matcatdict_fr.keys():
                        if re.search(matPattern, frkey):
                            artworkcategory = matcatdict_fr[frkey]
                            catfound = 1
                            break
                    if catfound:
                        break
                except:
                    pass
            description = "<strong><br>Description:</strong><br>Artist: %s<br/>Title: %s<br/>"%(artistName, artTitle) + description
            description = description + markings + "<br><strong>Condition Report</strong><br>" + condition + "<br><strong>Provenance</strong><br>" + provenance + "<br><strong>Literature</strong><br>" + literature + "<br><strong>Exhibited</strong><br>" + exhibited + "<Strong><br>Note</strong><br>"
            description = htmlTagPattern.sub("", description)
            description = description.replace("\n", " ")
            description = description.replace("\r", " ")
            description = description.replace('"', "'")
            if height and width:
                sizenote = str(height) + " x " + str(width)
            if depth is not None and depth != "None" and depth != "":
                sizenote += " x " + str(depth)
            if measureunit == "":
                measureunit = "in"
            sizenote += " " + measureunit
            estimatelow = str(estimatelow).replace(",", "").replace(" ", "")
            estimatehigh = str(estimatehigh).replace(",", "").replace(" ", "")
            soldprice = str(soldprice).replace(",", "").replace(" ", "")
        fp.write('"Wright","' + auctionlocation + '","' + str(auctionnumber) + '","' + str(auctionDate) + '","","' + str(auctionName) + '","' + str(lotnum) + '","' + str(sublot) + '","' + str(pricekind) + '","' + str(estimatelow) + '","' + str(estimatehigh) + '","' + str(soldprice) + '","' + artistName + '","' + str(birthyear) + '","' + str(deathyear) + '","' + str(artistnationality) + '","' + str(artTitle) + '","","' + str(startyear) + '","' + str(endyear) + '","' + str(material) + '","' + artworkcategory + '","' + str(markings) + '","' + str(edition) + '","' + str(description) + '","' + str(height) + '","' + str(width) + '","' + str(depth) + '","' + str(sizenote) + '","' + str(measureunit) + '","' + condition + '","' + provenance + '","' + exhibited + '","' + literature + '","' + artimages1 + '","' + artimages2 + '","' + artimages3 + '","' + artimages4 + '","' + artimages5 + '","' + imagename1 + '","' + imagename2 + '","' + imagename3 + '","' + imagename4 + '","' + imagename5 + '","' + itemLink + '"\n')
    #['auction_house_name', 'auction_location', 'auction_num', 'auction_start_date', 'auction_end_date', 'auction_name', 'lot_num', 'sublot_num', 'price_kind', 'price_estimate_min', 'price_estimate_max', 'price_sold', 'artist_name', 'artist_birth', 'artist_death', 'artist_nationality', 'artwork_name', 'artwork_year_identifier', 'artwork_start_year', 'artwork_end_year', 'artwork_materials', 'artwork_category', 'artwork_markings', 'artwork_edition', 'artwork_description', 'artwork_measurements_height', 'artwork_measurements_width', 'artwork_measurements_depth', 'artwork_size_notes', 'auction_measureunit', 'artwork_condition_in', 'artwork_provenance', 'artwork_exhibited', 'artwork_literature', 'artwork_images1', 'artwork_images2', 'artwork_images3', 'artwork_images4', 'artwork_images5', 'image1_name', 'image2_name', 'image3_name', 'image4_name', 'image5_name', 'lot_origin_url'] 
    fp.close()
    updatestatus(auctionnumber, auctionurl)
    print("Id's added to csv")

# Example: python wright.py https://www.wright20.com/auctions/2021/05/post-war-contemporary-art 202105 /home/supmit/work/art2/wright_202105.csv /home/supmit/work/art2/images/wright/202105 1 0

# https://www.wright20.com/auctions/2018/01/important-italian-glass


