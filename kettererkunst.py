# -*- coding: utf-8 -*-
from finefun import *
import subprocess
import os, sys, re, time, gzip,io
import csv
from tempfile import NamedTemporaryFile
import shutil
import logging
import subprocess
from io import StringIO
import time
from os import path
import urllib
from urllib.parse import urlencode
try:
    from urllib import quote  # Python 2.X
except ImportError:
    from urllib.parse import quote  # Python 3+
from cryptography.fernet import Fernet
import unidecode


emailIdPattern = re.compile(r"\W(\w+\.?\w{0,}@\w+\.\w+\.?\w*)\W", re.MULTILINE | re.DOTALL)
absUrlPattern = re.compile(r"^https?:\/\/", re.IGNORECASE)
anchorTagPattern = re.compile(r"<a\s+[^>]{0,}href=([^\s\>]+)\s?.*?>\s*\w+", re.IGNORECASE | re.MULTILINE | re.DOTALL)
doubleQuotePattern = re.compile('"', re.MULTILINE | re.DOTALL)
htmlTagPattern = re.compile(r"<[^>]+>", re.MULTILINE | re.DOTALL)
newlinePattern = re.compile(r"\n")
multipleWhitespacePattern = re.compile(r"\s+")
pathEndingWithSlashPattern = re.compile(r"\/$")
javascriptUrlPattern = re.compile("^javascript:")
startsWithSlashPattern = re.compile("^/")
htmlEntitiesDict = {'&nbsp;': ' ', '&#160;': ' ', '&amp;': '&', '&#038;': '&', '&lt;': '<', '&#60;': '<', '&gt;': '>',
                    '&#62;': '>', '&apos;': '\'', '&#39;': '\'', '&quot;': '"', '&#34;': '"', '&#8211;': '-',
                    '&euro;': 'Euro', '&hellip;': '...'}


def quoteText(content):
    content = str(stripHtmlEntities(content))
    content = content.replace('"', '\"')
    content = '"' + content + '"'
    return content


def stripHtmlEntities(content):
    for entityKey in htmlEntitiesDict.keys():
        entityKeyPattern = re.compile(entityKey)
        content = re.sub(entityKeyPattern, htmlEntitiesDict[entityKey], content)
    return content


def stripHTML(dataitem):
    dataitem = re.sub(htmlTagPattern, "", dataitem)  # stripped off all HTML tags...
    # Handle HTML entities...
    for entity in htmlEntitiesDict.keys():
        dataitem = dataitem.replace(entity, htmlEntitiesDict[entity])
    return (dataitem)




class Scrape:
    def __init__(self, mainUrl, auctionId, csvpath, imagedir, downloadImages, scrapperName, fp):
        self.auctionId = auctionId
        self.mainUrl = mainUrl
        self.domainUrl = domainUrl
        self.downloadImages = downloadImages
        self.scrapperName = scrapperName
        self.fp = fp
        self.run()

    def _decodeGzippedContent(cls, encoded_content):
        response_stream = io.BytesIO(encoded_content)
        decoded_content = ""
        try:
            gzipper = gzip.GzipFile(fileobj=response_stream)
            decoded_content = gzipper.read()
        except:  # Maybe this isn't gzipped content after all....
            decoded_content = encoded_content
        decoded_content = decoded_content.decode('utf-8')
        return (decoded_content)

    _decodeGzippedContent = classmethod(_decodeGzippedContent)


    def getImagenameFromUrl(self, imageUrl):
        urlparts = imageUrl.split("/")
        imagefilepart = urlparts[-1]
        imagefilenameparts = imagefilepart.split("?")
        imagefilename = imagefilenameparts[0]
        return imagefilename


    def encryptFilename(self, filename):
        k = Fernet.generate_key()
        f = Fernet(k)
        encfilename = f.encrypt(filename.encode())
        return encfilename

    def run(self):
        nextPage = True
        AUCTION_LOCATION, AUCTION_END_DATE, AUCTION_DATE, AUCTION_NAME = "Hamburg, Germany", "", "", ""
        soup = get_soup(self.mainUrl)
        self.writeHeaders(soup)  # Write the header part of csv
        productDetails = soup.findAll('div', {'class': 'result_objekt'})
        brPattern = re.compile("<br\s*\/?>", re.IGNORECASE)
        datedivtags = soup.find_all("div", {'class' : 'resultsbezeichnung'})
        if datedivtags.__len__() > 0:
            datecontent = datedivtags[0].renderContents().decode('utf-8')
            datePattern = re.compile("(\w{3}\.?\s+\d{1,2},\s+\d{4})", re.IGNORECASE|re.DOTALL)
            dps = re.search(datePattern, datecontent)
            if dps:
                AUCTION_DATE = dps.groups()[0]
            try:
                AUCTION_NAME = datedivtags[0].find("b").renderContents().decode('utf-8')
            except:
                pass
        matcatdict_en = {}
        matcatdict_fr = {}
        #with open("docs/fineart_materials.csv", newline='') as mapfile:
        with open("/root/artwork/deploydirnew/docs/fineart_materials.csv", newline='') as mapfile:
            mapreader = csv.reader(mapfile, delimiter=",", quotechar='"')
            for maprow in mapreader:
                matcatdict_en[maprow[1]] = maprow[3]
                matcatdict_fr[maprow[2]] = maprow[3]
        mapfile.close()
        pagecounter = 2
        while nextPage:
            for product in productDetails:
                CATEGORY = ''
                ARTIST = ''
                BIRTHDATE = ''
                DEATHDATE = ''
                DEFAULT_IMAGE_URL = ''
                ADDITIONAL_IMAGE_URLS = ''
                TITLE = ''
                MEDIUM_RAW = ''
                SIZE_IMAGE = ''
                SHEET_SIZE = ''
                YEARFROM = ''
                YEARTO = ''
                CONCEPTION_YEAR_FROM = ''
                CONCEPTION_YEAR_TO = ''
                SIGNATURE = ''
                EDITIONTYPE = ''
                EDITION_ = ''
                PLATE = ''
                PRINTER = ''
                PUBLISHER = ''
                FOUNDRY = ''
                STUDIO = ''
                LETTER_OF_AUTHENTICITY = ''
                INSCRIPTION = ''
                GUARANTEE = ''
                ESTIMATE = ''
                SOLD_PRICE = ''
                AUCTION_HOUSE = ''
                SALENUMBER = ''
                LOT = ''
                LOT_URL = ''
                CATALOG_RAISONNE = ''
                EXHIBITION = ''
                LITERATURE = ''
                PROVENANCE = ''
                ARTWORK_IMAGES1, ARTWORK_IMAGES2, ARTWORK_IMAGES3, ARTWORK_IMAGES4, ARTWORK_IMAGES5 = "", "", "", "", ""
                IMAGE1_NAME, IMAGE2_NAME, IMAGE3_NAME, IMAGE4_NAME, IMAGE5_NAME = "", "", "", "", ""
                SUBLOT_NUMBER, PRICE_KIND, ARTIST_NATIONALITY, ART_YEAR_ID, ARTWORK_CATEGORY, ARTWORK_DESC, ART_CONDITION = "", "", "", "", "", "", ""
                try:
                    aTag = product.find("a")
                except:
                    aTag = None
                    pass

                if aTag:
                    detailPageUrl = "https://www.kettererkunst.com"+aTag["href"]
                    try:
                        LOT_URL=detailPageUrl
                        print(LOT_URL)
                    except:
                        pass
                    detailPageSoup = get_soup(detailPageUrl)
                    try:
                        LOT=detailPageSoup.find("div",{"style":"height:35px; font-size:28px; margin-top:0px; "}).getText().strip()
                        print(LOT)
                    except:
                        pass
                    try:
                        ARTIST=detailPageSoup.find("span",{"style":"text-transform:uppercase;"}).getText().strip()
                        #print(ARTIST)
                    except:
                        pass
                    BIRTHDATE,DEATHDATE=getStartEndYear(ARTIST)
                    try:
                        TITLE = detailPageSoup.find("div", {"style": "margin-top:10px; font-size:20px; line-height:30px; "}).find('i').getText().strip()
                        #print(TITLE)
                    except:
                        pass
                    titledivtags = detailPageSoup.find_all("div", {'class' : 'block_beschreibung_sub beschreibung'})
                    if titledivtags.__len__() > 0:
                        titlecontents = titledivtags[0].renderContents().decode('utf-8')
                        #contentparts = re.split(brPattern, titlecontents)
                        titlecontents = htmlTagPattern.sub("", titlecontents)
                        ARTWORK_DESC = titlecontents
                        ARTWORK_DESC = ARTWORK_DESC.replace("\n", "").replace("\r", "")
                        ARTWORK_DESC = ARTWORK_DESC.strip()
                        ARTWORK_DESC = htmlTagPattern.sub("", ARTWORK_DESC)
                        ARTWORK_DESC = ARTWORK_DESC.replace("\n", " ")
                        ARTWORK_DESC = ARTWORK_DESC.replace("\r", " ")
                        ARTWORK_DESC = ARTWORK_DESC.replace('"', "'")
                        ARTWORK_DESC = ARTWORK_DESC.replace("PROVENANCE:", "<br><strong>Provenance</strong><br>")
                        ARTWORK_DESC = ARTWORK_DESC.replace("LITERATURE:", "<br><strong>Literature</strong><br>")
                        ARTWORK_DESC = ARTWORK_DESC.replace("EXHIBITED:", "<br><strong>Exhibited</strong><br>")
                        ARTWORK_DESC = ARTWORK_DESC.replace("EXPOSITIONS:", "<br><strong>Expositions</strong><br>")
                        ARTWORK_DESC = ARTWORK_DESC.replace("BIBLIOGRAPHIE:", "<br><strong>Literature</strong><br>")
                        ARTWORK_DESC = ARTWORK_DESC.replace("Condition Report", "<br><strong>Condition Report</strong><br>")
                        ARTWORK_DESC = ARTWORK_DESC.replace("Notes:", "<br><strong>Notes:</strong><br>")
                        ARTWORK_DESC = "<strong><br>Description<br></strong>" + ARTWORK_DESC
                        ARTWORK_DESC = ARTWORK_DESC.replace('"', "'")
                        # Unfinished part - we won't want it right now... as long as the above construct works - supmit 
                    YEARFROM,YEARTO=getStartEndYear(detailPageSoup.find("div", {"style": "margin-top:10px; font-size:20px; line-height:30px; "}).getText())
                    try:
                        MEDIUM_RAW = detailPageSoup.find("div", {"style": "margin-top:15px;"}).getText().strip()
                    except:
                        pass
                    if MEDIUM_RAW != "":
                        materials = MEDIUM_RAW
                        materialparts = materials.split(" ")
                        catfound = 0
                        for matpart in materialparts:
                            if matpart in ['in', 'on', 'of', 'the', 'from']:
                                continue
                            try:
                                matPattern = re.compile(matpart, re.IGNORECASE|re.DOTALL)
                                for enkey in matcatdict_en.keys():
                                    if re.search(matPattern, enkey):
                                        ARTWORK_CATEGORY = matcatdict_en[enkey]
                                        catfound = 1
                                        break
                                for frkey in matcatdict_fr.keys():
                                    if re.search(matPattern, frkey):
                                        ARTWORK_CATEGORY = matcatdict_fr[frkey]
                                        catfound = 1
                                        break
                                if catfound:
                                    break
                            except:
                                pass
                    def get_image(imageurl, path_name):
                        image_name = LOT.strip() + path_name
                        folderImage = 'kettererkunst'
                        try:
                            image = requests.get(imageurl)
                        except OSError:  # Little too wide, but work OK, no additional imports needed. Catch all conection problems
                            return False
                        if image.status_code == 200:  # we could have retrieved error page
                            base_dir = path.join(path.dirname(path.realpath(__file__)),
                                             "images")  # Use your own path or "" to use current working directory. Folder must exist.
                            with open(path.join(base_dir, folderImage, image_name), "wb") as f:
                                f.write(image.content)
                            return image_name

                    try:
                        DEFAULT_IMAGE_URL = "https://www.kettererkunst.com"+detailPageSoup.find("img",{"class","bild"})['src']
                        path_name = "_a.jpg"
                        #image = get_image(DEFAULT_IMAGE_URL, path_name)
                        DEFAULT_IMAGE_URL = "https://theeolico.com/wp-content/uploads/Kettererkunst/" + "images" + "/" +auctionId+"/" + LOT.strip() + "_a.jpg"
                        imagename1 = self.getImagenameFromUrl(DEFAULT_IMAGE_URL)
                        imagename1 = str(imagename1)
                        imagename1 = imagename1.replace("b'", "").replace("'", "")
                        processedAuctionTitle = AUCTION_NAME.replace(" ", "_")
                        processedArtistName = ARTIST.replace(" ", "_")
                        processedArtistName = unidecode.unidecode(processedArtistName)
                        processedArtworkName = TITLE.replace(" ", "_")
                        sublot_number = ""
                        #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + self.auctionId + "__" + str(LOT) + "__" + sublot_number
                        newname1 = self.auctionId + "__" + processedArtistName + "__" + str(LOT) + "_a"
                        #encryptedFilename = self.encryptFilename(newname1)
                        encryptedFilename = newname1
                        imagepathparts = DEFAULT_IMAGE_URL.split("/")
                        defimageurl = "/".join(imagepathparts[:-2])
                        encryptedFilename = str(encryptedFilename).replace("b'", "")
                        encryptedFilename = str(encryptedFilename).replace("'", "")
                        IMAGE1_NAME = str(encryptedFilename) + ".jpg"
                        ARTWORK_IMAGES1 = DEFAULT_IMAGE_URL
                    except:
                        pass
                    additionalimages = []
                    imagedivtags = detailPageSoup.find_all("div", {'class' : 'details_w_abb_div_img'})
                    ictr = 0
                    for imgdivtag in imagedivtags:
                        if ictr >= 5:
                            break
                        imgtag = imgdivtag.find("img")
                        if imgtag:
                            imgsrc = "https://www.kettererkunst.com" + imgtag['src']
                            additionalimages.append(imgsrc)
                        ictr += 1
                    imgctr = 2
                    if additionalimages.__len__() > 0:
                        altimage2 = additionalimages[0]
                        altimage2parts = altimage2.split("/")
                        altimageurl = "/".join(altimage2parts[:-2])
                        processedAuctionTitle = AUCTION_NAME.replace(" ", "_")
                        processedArtistName = ARTIST.replace(" ", "_")
                        processedArtistName = unidecode.unidecode(processedArtistName)
                        processedArtworkName = TITLE.replace(" ", "_")
                        sublot_number = ""
                        #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + self.auctionId + "__" + str(LOT) + "__" + sublot_number
                        newname1 = self.auctionId + "__" + processedArtistName + "__" + str(LOT) + "_b"
                        #encryptedFilename = self.encryptFilename(newname1)
                        encryptedFilename = newname1
                        IMAGE2_NAME = str(encryptedFilename) + ".jpg"
                        ARTWORK_IMAGES2 = altimage2
                        imgctr += 1
                    if additionalimages.__len__() > 1:
                        altimage2 = additionalimages[1]
                        altimage2parts = altimage2.split("/")
                        altimageurl = "/".join(altimage2parts[:-2])
                        processedAuctionTitle = AUCTION_NAME.replace(" ", "_")
                        processedArtistName = ARTIST.replace(" ", "_")
                        processedArtistName = unidecode.unidecode(processedArtistName)
                        processedArtworkName = TITLE.replace(" ", "_")
                        sublot_number = ""
                        #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + self.auctionId + "__" + str(LOT) + "__" + sublot_number
                        newname1 = self.auctionId + "__" + processedArtistName + "__" + str(LOT) + "_c"
                        #encryptedFilename = self.encryptFilename(newname1)
                        encryptedFilename = newname1
                        IMAGE3_NAME = str(encryptedFilename) + ".jpg"
                        ARTWORK_IMAGES3 = altimage2
                        imgctr += 1
                    if additionalimages.__len__() > 2:
                        altimage2 = additionalimages[2]
                        altimage2parts = altimage2.split("/")
                        altimageurl = "/".join(altimage2parts[:-2])
                        processedAuctionTitle = AUCTION_NAME.replace(" ", "_")
                        processedArtistName = ARTIST.replace(" ", "_")
                        processedArtistName = unidecode.unidecode(processedArtistName)
                        processedArtworkName = TITLE.replace(" ", "_")
                        sublot_number = ""
                        #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + self.auctionId + "__" + str(LOT) + "__" + sublot_number
                        newname1 = self.auctionId + "__" + processedArtistName + "__" + str(LOT) + "_d"
                        #encryptedFilename = self.encryptFilename(newname1)
                        encryptedFilename = newname1
                        IMAGE4_NAME = str(encryptedFilename) + ".jpg"
                        ARTWORK_IMAGES4 = altimage2
                        imgctr += 1
                    if additionalimages.__len__() > 3:
                        altimage2 = additionalimages[3]
                        altimage2parts = altimage2.split("/")
                        altimageurl = "/".join(altimage2parts[:-2])
                        processedAuctionTitle = AUCTION_NAME.replace(" ", "_")
                        processedArtistName = ARTIST.replace(" ", "_")
                        processedArtistName = unidecode.unidecode(processedArtistName)
                        processedArtworkName = TITLE.replace(" ", "_")
                        sublot_number = ""
                        #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + self.auctionId + "__" + str(LOT) + "__" + sublot_number
                        newname1 = self.auctionId + "__" + processedArtistName + "__" + str(LOT) + "_e"
                        #encryptedFilename = self.encryptFilename(newname1)
                        encryptedFilename = newname1
                        IMAGE5_NAME = str(encryptedFilename) + ".jpg"
                        ARTWORK_IMAGES5 = altimage2
                    SALENUMBER=auctionId
                    AUCTION_HOUSE='KETTERER'
                    try:
                        ESTIMATE=detailPageSoup.findAll("div",{"style":"margin-top:10px;"})[0].getText().replace(",",'').replace("$",'').strip().encode('ascii', 'ignore').decode('ascii')
                        ESTIMATE = ESTIMATE.replace("\n", "").replace("\r", "")
                        ESTIMATE = htmlTagPattern.sub("", ESTIMATE)
                        ESTIMATE = ESTIMATE.replace("Estimate: ", "")
                        #ESTIMATE = ESTIMATE + " EUR"
                        #print(ESTIMATE)
                    except:
                        ESTIMATE = ""
                    estimateparts = ESTIMATE.split(" - ")
                    PRICE_EST_MIN = estimateparts[0]
                    PRICE_EST_MIN = PRICE_EST_MIN.split("/")[0]
                    PRICE_EST_MAX = ""
                    if estimateparts.__len__() > 1:
                        estimateparts[1] = re.sub(re.compile("[A-Za-z]{3}"), "", estimateparts[1])
                        PRICE_EST_MAX = estimateparts[1]
                        PRICE_EST_MAX = PRICE_EST_MAX.split("/")[0]
                    soldspan = detailPageSoup.find("span", {'style' : 'color:darkred;'})
                    if soldspan:
                        soldcontent = soldspan.renderContents().decode('utf-8')
                        soldPattern = re.compile("€\s+([\d\.,]+)")
                        soldcontent = soldcontent.replace("\n", "").replace("\r", "")
                        soldcontent = htmlTagPattern.sub("", soldcontent)
                        sps = re.search(soldPattern, soldcontent)
                        if sps:
                            SOLD_PRICE = sps.groups()[0]
                    withdrawnPattern = re.compile("withdrawn", re.IGNORECASE|re.DOTALL)
                    PRICE_KIND = "unknown"
                    if re.search(withdrawnPattern, SOLD_PRICE) or re.search(withdrawnPattern, PRICE_EST_MAX):
                        PRICE_KIND = "withdrawn"
                    elif SOLD_PRICE != "":
                        PRICE_KIND = "price realized"
                    elif PRICE_EST_MAX != "":
                        PRICE_KIND = "estimate"
                    else:
                        pass
                    #All_Data=detailPageSoup.find("div",{"style":"line-height:18px;"}).getText(separator=u'@').strip().replace('@@@', '@').replace('@@', '@').split("@")
                    All_Data=detailPageSoup.find("div",{"class":"block_beschreibung_sub beschreibung"}).getText(separator=u'@').strip().replace('@@@', '@').replace('@@', '@').split("@")
                    #print(All_Data)
                    #functionfile = detailPageSoup.find("div",{"style":"line-height:18px;"})
                    functionfile = detailPageSoup.find("div",{"class":"block_beschreibung_sub beschreibung"})
                    functionfile = functionfile.renderContents().decode('utf-8')
                    functionfile = functionfile.split("<br/><br/>")
                    try:
                        PROVENANCE = [x for x in functionfile if "PROVENANCE:" in x.strip()][0].strip()
                        PROVENANCE=PROVENANCE.replace("PROVENANCE:",'').strip()
                        PROVENANCE=remove_tags(PROVENANCE)
                    except:
                        pass
                    try:
                        EXHIBITION = [x for x in functionfile if "EXHIBITION:" in x.strip()][0].strip()
                        EXHIBITION=EXHIBITION.replace("EXHIBITION:","")
                        EXHIBITION = remove_tags(EXHIBITION)
                    except:
                        pass
                    try:
                        LITERATURE = [x for x in functionfile if "LITERATURE:" in x.strip()][0].strip()
                        LITERATURE=LITERATURE.replace("LITERATURE:","")
                        LITERATURE = remove_tags(LITERATURE)
                    except:
                        pass

                    SIGNATURE=getSignature(All_Data)
                    SIGNATURE=SIGNATURE.encode('ascii', 'ignore').decode('ascii')
                    # SIGNATURE=SIGNATURE.split(". ")
                    # SIGNATURE = getSignature(SIGNATURE)

                    pattern = re.compile("\s*([\d\.\sx]+\s*cm)\s*\([^\)]+\)", re.DOTALL)
                    SIGNATURE = pattern.sub("", SIGNATURE)
                    SIGNATURE=SIGNATURE.split(";")[0]

                    #print(SIGNATURE)
                    #SIZE_IMAGE=''.join(re.findall("\s*([\d\.\sx]+\s*cm)\s*\([^\)]+\)",detailPageSoup.find("div",{"style":"line-height:18px;"}).getText()))
                    SIZE_IMAGE=''.join(re.findall("\s*([\d\.\sx]+\s*cm)\s*\([^\)]+\)",detailPageSoup.find("div",{"class":"block_beschreibung_sub beschreibung"}).getText()))
                    #print(SIZE_IMAGE)
                    SIZE_IMAGE=re.sub("cm.*","",SIZE_IMAGE)
                    SIZE_IMAGE=SIZE_IMAGE.replace(". ",'').strip()

                    SIZE_IMAGE=SIZE_IMAGE.replace(',','.')+' '+"cm"
                    sizeparts = SIZE_IMAGE.split("x")
                    ART_HEIGHT = sizeparts[0]
                    ART_WIDTH = ""
                    ART_DEPTH = ""
                    AUCTION_MEASUREUNIT = ""
                    measureunitPattern = re.compile("([a-zA-Z]{2})")
                    if sizeparts.__len__() > 1:
                        ART_WIDTH = sizeparts[1]
                        mups = re.search(measureunitPattern, ART_WIDTH)
                        if mups:
                            AUCTION_MEASUREUNIT = mups.groups()[0]
                            ART_WIDTH = measureunitPattern.sub("", ART_WIDTH)
                    if sizeparts.__len__() > 2:
                        ART_DEPTH = sizeparts[2]
                        mups = re.search(measureunitPattern, ART_DEPTH)
                        if mups:
                            AUCTION_MEASUREUNIT = mups.groups()[0]
                            ART_DEPTH = measureunitPattern.sub("", ART_DEPTH)
                    #print(SIZE_IMAGE)
                    try:
                        numberofcategory = re.findall("\sx\s", SIZE_IMAGE)
                        if numberofcategory.__len__() == 2:
                            CATEGORY = "3d"
                        if numberofcategory.__len__() == 1:
                            CATEGORY = "2d"
                        if numberofcategory.__len__() == 0:
                            CATEGORY = "3d"
                    except:
                        pass
                    rX = lambda x: " ".join(
                    x.replace("\n", "").replace("\t", "").replace('"','').replace(',','').splitlines())
                    #fp.write('"' + AUCTION_HOUSE.replace(",", ".") + '", "' + AUCTION_LOCATION.replace(",", ".") + '", "' + SALENUMBER.replace(",", ".") + '", "' + AUCTION_DATE.replace(",", ".") + '", "' + AUCTION_END_DATE + '", "' + AUCTION_NAME + '", "' + LOT.replace(",", ".") + '", "' + SUBLOT_NUMBER + '", "' + PRICE_KIND + '", "' + PRICE_EST_MIN + '", "' + PRICE_EST_MAX + '", "' + SOLD_PRICE + '", "' + ARTIST.replace(",", '') + '", "' + rX(BIRTHDATE) + '", "' + rX(DEATHDATE) + '", "' + ARTIST_NATIONALITY + '", "' + rX(TITLE.replace(",", ".")) + '", "' + ART_YEAR_ID + '", "' + rX(YEARFROM.replace(",", ".")) + '", "' + rX(YEARTO.replace(",", ".")) + '", "' + rX(MEDIUM_RAW.replace(",", ".")) + '", "' + ARTWORK_CATEGORY + '", "' + rX(SIGNATURE.replace(",", ".")) + '", "' + rX(EDITIONTYPE.replace(",", ".")) + '", "' + ARTWORK_DESC + '", "' + ART_HEIGHT + '", "' + ART_WIDTH + '", "' + ART_DEPTH + '", "' + rX(SIZE_IMAGE.replace(",", ".")) + '", "' + AUCTION_MEASUREUNIT + '", "' + ART_CONDITION + '", "' + rX(PROVENANCE.replace(",", ".")) + '", "' + rX(EXHIBITION.replace(",", ".")) + '", "' + rX(LITERATURE.replace(",", ".")) + '", "' + ARTWORK_IMAGES1 + '", "' + ARTWORK_IMAGES2 + '", "' + ARTWORK_IMAGES3 + '", "' + ARTWORK_IMAGES4 + '", "' + ARTWORK_IMAGES5 + '", "' + IMAGE1_NAME + '", "' + IMAGE2_NAME + '", "' + IMAGE3_NAME + '", "' + IMAGE4_NAME + '", "' + IMAGE5_NAME + '", "' + rX(LOT_URL.replace(",", ".")) + '"' + "\n")
                    fp.write(AUCTION_HOUSE.replace(",", ".") + ', ' + AUCTION_LOCATION.replace(",", ".") + ', ' + SALENUMBER.replace(",", ".") + ', ' + AUCTION_DATE.replace(",", ".") + ', ' + AUCTION_END_DATE + ', ' + AUCTION_NAME + ', ' + LOT.replace(",", ".") + ', ' + SUBLOT_NUMBER + ', ' + PRICE_KIND + ', ' + rX(PRICE_EST_MIN.replace(",", "")) + ', ' + rX(PRICE_EST_MAX.replace(",", "")) + ', ' + rX(SOLD_PRICE.replace(",", "")) + ', ' + ARTIST.replace(",", '') + ', ' + rX(BIRTHDATE) + ', ' + rX(DEATHDATE) + ', ' + ARTIST_NATIONALITY + ', ' + rX(TITLE.replace(",", ".")) + ', ' + ART_YEAR_ID + ', ' + rX(YEARFROM.replace(",", ".")) + ', ' + rX(YEARTO.replace(",", ".")) + ', ' + rX(MEDIUM_RAW.replace(",", ".")) + ', ' + ARTWORK_CATEGORY + ', ' + rX(SIGNATURE.replace(",", ".").replace("&amp;", "&").replace(";", " ")) + ', ' + rX(EDITIONTYPE.replace(",", ".").replace("&amp;", "&").replace(";", " ")) + ', ' + rX(ARTWORK_DESC.replace(",", ".").replace("&amp;", "&").replace(";", " ")) + ', ' + ART_HEIGHT + ', ' + ART_WIDTH + ', ' + ART_DEPTH + ', ' + rX(SIZE_IMAGE.replace(",", ".")) + ', ' + AUCTION_MEASUREUNIT + ', ' + rX(ART_CONDITION.replace(",", ".").replace("&amp;", "&").replace(";", " ")) + ', ' + rX(PROVENANCE.replace(",", ".").replace("&amp;", "&").replace(";", " ")) + ', ' + rX(EXHIBITION.replace(",", ".").replace("&amp;", "&").replace(";", " ")) + ', ' + rX(LITERATURE.replace(",", ".").replace("&amp;", "&").replace(";", " ")) + ', ' + ARTWORK_IMAGES1 + ', ' + ARTWORK_IMAGES2 + ', ' + ARTWORK_IMAGES3 + ', ' + ARTWORK_IMAGES4 + ', ' + ARTWORK_IMAGES5 + ', ' + IMAGE1_NAME + ', ' + IMAGE2_NAME + ', ' + IMAGE3_NAME + ', ' + IMAGE4_NAME + ', ' + IMAGE5_NAME + ', ' + rX(LOT_URL.replace(",", ".")) + "\n")

            if pagecounter < 10:
                requestURL = mainUrl
                postData = {"seite": "%s"%pagecounter, "objsei": "30"}
                urlencodedData = urlencode(postData)
                try:
                    urlencodeBytes = bytes(urlencodedData).encode('utf-8')
                except:
                    urlencodeBytes = urlencodedData.encode('utf-8')
                # requestUrl = requestUrl[:-1]
                pageRequest = urllib.request.Request(requestURL, urlencodeBytes, headers=httpHeaders)
                try:
                    pageResponse = no_redirect_opener.open(pageRequest)

                except urllib.request.HTTPError as e:
                    print("Could not post the form data to login1 - Error: " + sys.exc_info()[1].__str__())
                    print(e.code)
                    return None
                html = pageResponse.read()
                html = self.__class__._decodeGzippedContent(html)
                pagecounter+=1
                soup=BeautifulSoup(html, features='lxml')
                nextPage = True
                productDetails = soup.findAll('div', {'class': 'result_objekt'})
            else:
                nextPage = False




    def writeHeaders(self, soup):
        auction_name, auction_date, auction_title, auction_location, lotCount, lot_sold_in = "", "", "", "", "", ""
        lot_sold_in = "USD"

        writeHeader(self.fp, auction_name, auction_location, auction_date, auction_title, auctionId, lotCount,
                    lot_sold_in)

    def getTextData(self, All_Data, textName):
        try:
            textData = [item for index, item in enumerate(All_Data) if textName in item.lower()][0]
        except:
            return ""

    def getIndexData(self, All_Data, textName):
        try:
            indexNo = [index for index, item in enumerate(All_Data) if textName in item][0]
        except:
            return ""


def updatestatus(auctionno, auctionurl):
    auctionurl = auctionurl.replace("%3A", ":")
    auctionurl = auctionurl.replace("%2F", "/")
    pageurl = "http://216.137.189.57:8080/scrapers/finish/?scrapername=Ketterer&auctionnumber=%s&auctionurl=%s&scrapertype=2"%(auctionno, urllib.parse.quote(auctionurl))
    pageResponse = None
    try:
        pageResponse = urllib.request.urlopen(pageurl)
    except:
        print ("Error: %s"%sys.exc_info()[1].__str__()) 



if __name__ == "__main__":
    auctionId = sys.argv[2].upper()
    mainUrl = sys.argv[1]
    csvpath = sys.argv[3]
    imagedir = sys.argv[4]
    domainUrl = ''
    scrapperName = "Ketterer"
    downloadImages = True
    if sys.argv.__len__() > 2 and sys.argv[2] == "True":
        downloadImages = "True"
    fp = open(csvpath, "w")
    Scrape(mainUrl, auctionId, csvpath, imagedir, downloadImages, scrapperName,  fp)
    fp.close()
    updatestatus(auctionId, mainUrl)


# Example: python kettererkunst.py "https://www.kettererkunst.com/result.php?shw=1&sortieren=katnr&anr=522&kanrv=400.00&kanrb=476.00" 522 /home/supmit/work/art2/ketterer_522.csv /home/supmit/work/art2/images/ketterer/522 0 0


