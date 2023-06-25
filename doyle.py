# -*- coding: cp1252 -*-
from finefun import *
import subprocess
import os, sys, re, time, gzip
import csv
from tempfile import NamedTemporaryFile
import shutil
import logging
import subprocess
from io import StringIO
import time
from os import path
import urllib
import urllib.parse
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
beginspacePattern = re.compile("^\s+")

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
        self.domainUrl = "https://doyle.com"
        self.imagedir = imagedir
        self.downloadImages = downloadImages
        self.scrapperName = scrapperName
        self.fp = fp
        self.run(auctionId, csvpath, self.imagedir)

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

    def run(self, auctionId, csvpath, imagedir):
        nextPage = True
        AUCTION_LOCATION, AUCTION_END_DATE, AUCTION_DATE, AUCTION_NAME = "", "", "", ""
        httpHeaders = {'Referer' : 'https://doyle.com/auctions/22th01-stage-screen/stage-screen', 'Accept' : 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9', 'Accept-Encoding' : 'gzip, deflate', 'Accept-Language' : 'en-GB,en-US;q=0.9,en;q=0.8', 'Cache-Control' : 'max-age=0', 'sec-ch-ua' : '".Not/A)Brand";v="99", "Google Chrome";v="103", "Chromium";v="103"', 'sec-ch-ua-mobile' : '?0', 'sec-ch-ua-platform' : '"Linux"', 'sec-fetch-dest' : 'document', 'sec-fetch-mode' : 'navigate', 'sec-fetch-site' : 'same-origin', 'sec-fetch-user' : '?1', 'User-Agent' : 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.5060.53 Safari/537.36'}
        soup = get_soup(self.mainUrl, httpHeaders=httpHeaders)
        if not soup:
            return ""
        datespans = soup.find_all("span", {'class' : 'auction-mini-header-date'})
        auctionDate = ""
        if datespans.__len__() > 0:
            datecontents = datespans[0].renderContents().decode('utf-8')
            datePattern = re.compile("(\w{3})\s+(\d{1,2}),\s+(\d{4})\s+")
            dps = re.search(datePattern, datecontents)
            if dps:
                mon = dps.groups()[0]
                dd = dps.groups()[1]
                yyyy = dps.groups()[2]
                mm = '01'
                if mon == "Feb":
                    mm = '02'
                elif mon == "Mar":
                    mm = '03'
                elif mon == "Apr":
                    mm = '04'
                elif mon == "May":
                    mm = '05'
                elif mon == "Jun":
                    mm = '06'
                elif mon == "Jul":
                    mm = '07'
                elif mon == "Aug":
                    mm = '08'
                elif mon == "Sep":
                    mm = '09'
                elif mon == "Oct":
                    mm = '10'
                elif mon == "Nov":
                    mm = '11'
                elif mon == "Dec":
                    mm = '12'
                else:
                    pass
                auctionDate = dd + "-" + mon + "-" + yyyy[2:]
                #print(auctionDate)
        self.writeHeaders(soup)  # Write the header part of csv
        h1tags = soup.find_all("h1")
        if h1tags.__len__() > 0:
            spancontents = h1tags[0].renderContents().decode('utf-8')
            spancontents = htmlTagPattern.sub("", spancontents)
            AUCTION_NAME = spancontents
            AUCTION_NAME = AUCTION_NAME.replace("\n", "").replace("\r", "")
            nextspantag = h1tags[0].find_next_sibling("span")
            if nextspantag is not None:
                spancontents = nextspantag.renderContents().decode('utf-8')
                spancontents = htmlTagPattern.sub("", spancontents)
                spancontents = spancontents.replace("\n", " ").replace("\r", " ")
                datePattern = re.compile("([a-zA-Z]{3}\s+\d{2},\s+\d{4})\s+at\s+\d{1,2}[ap]m\s+[A-Z]{3}\s+(.*)$", re.DOTALL)
                dps = re.search(datePattern, spancontents)
                if dps:
                    AUCTION_DATE = dps.groups()[0]
                    dateparts = AUCTION_DATE.split(" ")
                    if dateparts.__len__() > 2:
                        yy = dateparts[2][2:]
                    else:
                        yy = "22"
                    dd = dateparts[1].replace(",", "")
                    mon = dateparts[0]
                    AUCTION_DATE = "%s-%s-%s"%(dd, mon, yy)
                    AUCTION_LOCATION = dps.groups()[1]
                    AUCTION_LOCATION = AUCTION_LOCATION.replace("|", "")
                    AUCTION_LOCATION = beginspacePattern.sub("", AUCTION_LOCATION)
        total_page_nos = 10
        try:
            next_page_urls = [
                mainUrl + "?keys=&field_lot_catalog_value=&field_lotno_value=&field_receipt_target_id=&field_category_target_id=&sort_by=field_lot_sort_value&sort_order=ASC&items_per_page=60&page=" + str(x) for x in range(0, total_page_nos)]
            #print(next_page_urls)
        except:
            next_page_urls = ""
            pass
        next_page_urls[0] = mainUrl
        matcatdict_en = {}
        matcatdict_fr = {}
        #with open("docs/fineart_materials.csv", newline='') as mapfile:
        with open("/root/artwork/deploydirnew/docs/fineart_materials.csv", newline='') as mapfile:
            mapreader = csv.reader(mapfile, delimiter=",", quotechar='"')
            for maprow in mapreader:
                matcatdict_en[maprow[1]] = maprow[3]
                matcatdict_fr[maprow[2]] = maprow[3]
        mapfile.close()
        natdbPattern1 = re.compile("([a-zA-Z\/,\-]+),\s+(\d{4})\s*\-\s*(\d{4})", re.DOTALL)
        natdbPattern2 = re.compile("([a-zA-Z\/,\-]+),\s+B\.?(\d{4})", re.DOTALL)
        yearPattern = re.compile("\d{4}")
        for page_url in next_page_urls:
            print("Getting Page '%s'"%page_url)
            soup = get_soup(page_url, httpHeaders=httpHeaders)
            productDetails = soup.findAll('h2', {'class': 'lot-title'})
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
                AUCTION_DATE = ''
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
                    detailPageUrl = 'https://doyle.com/'+aTag["href"]
                    try:
                        LOT_URL=detailPageUrl
                    except:
                        pass
                    try:
                        detailPageSoup = get_soup(detailPageUrl, httpHeaders=httpHeaders)
                        details_head=detailPageSoup.find('div',{'class':'page-heading rfc-lot-heading'})
                        head_details=details_head.find('span',{'class':'smallcaps-label'})
                        #print(head_details.getText())
                    except:
                        pass
                    try:
                        LOT = ''.join(re.findall("Lot.*(\s\d+)", head_details.getText()))
                        print(LOT)
                    except:
                        pass
                    try:
                        All_Data = detailPageSoup.findAll('div',{'class':'lot-details-section'})[1].getText(separator=u'@').strip().replace('@@@', '@').replace('@@', '@')
                        All_Data = All_Data.split('@')
                    except:
                        pass
                    alldesctags = detailPageSoup.find_all('div',{'class':'lot-details-section'})
                    ARTWORK_DESC = ""
                    if alldesctags.__len__() > 1:
                        ARTWORK_DESC = alldesctags[1].renderContents().decode('utf-8')
                    ARTWORK_DESC = htmlTagPattern.sub("", ARTWORK_DESC)
                    ARTWORK_DESC = ARTWORK_DESC.replace("\n", "").replace("\r", "")
                    ARTWORK_DESC = ARTWORK_DESC.strip()
                    ARTWORK_DESC = htmlTagPattern.sub("", ARTWORK_DESC)
                    ARTWORK_DESC = ARTWORK_DESC.replace("\n", " ")
                    ARTWORK_DESC = ARTWORK_DESC.replace("\r", " ")
                    ARTWORK_DESC = ARTWORK_DESC.replace('"', "'")
                    ARTWORK_DESC = ARTWORK_DESC.replace("Provenance:", "<br><strong>Provenance</strong><br>")
                    ARTWORK_DESC = ARTWORK_DESC.replace("Literature:", "<br><strong>Literature</strong><br>")
                    ARTWORK_DESC = ARTWORK_DESC.replace("Exhibited:", "<br><strong>Exhibited</strong><br>")
                    ARTWORK_DESC = ARTWORK_DESC.replace("Expositions:", "<br><strong>Expositions</strong><br>")
                    ARTWORK_DESC = ARTWORK_DESC.replace("Bibliographie:", "<br><strong>Literature</strong><br>")
                    ARTWORK_DESC = ARTWORK_DESC.replace("Condition Report", "<br><strong>Condition Report</strong><br>")
                    ARTWORK_DESC = ARTWORK_DESC.replace("Notes:", "<br><strong>Notes:</strong><br>")
                    ARTWORK_DESC = "<strong><br>Description<br></strong>" + ARTWORK_DESC
                    ARTWORK_DESC = ARTWORK_DESC.replace('"', "'")
                    try:
                        ARTIST=detailPageSoup.findAll('div',{'class':'lot-details-section'})[1].find('strong').getText()#details_head.find('h1').getText()
                    except:
                        pass
                    try:
                        years = re.findall("\d{4}", ARTIST)
                        BIRTHDATE, DEATHDATE = ['', '']
                        if len(years) > 1:
                            BIRTHDATE = years[0]
                            DEATHDATE = years[1]
                        elif len(years) == 1:
                            BIRTHDATE = years[0]
                    except:
                        pass
                    if not BIRTHDATE or BIRTHDATE == "":
                        ndbps1 = re.search(natdbPattern1, ARTWORK_DESC)
                        ndbps2 = re.search(natdbPattern2, ARTWORK_DESC)
                        if ndbps1:
                            ARTIST_NATIONALITY = ndbps1.groups()[0]
                            BIRTHDATE = ndbps1.groups()[1]
                            DEATHDATE = ndbps1.groups()[2]
                        elif ndbps2:
                            ARTIST_NATIONALITY = ndbps2.groups()[0]
                            BIRTHDATE = ndbps2.groups()[1]
                    try:
                        ARTIST=re.sub('[(].*','',ARTIST)
                    except:
                        pass
                    try:
                        TITLE =detailPageSoup.findAll('div',{'class':'lot-details-section'})[1].find('i').getText().strip() #All_Data[8].title().strip()
                        TITLE=re.sub('.*inche.*','',TITLE)
                        lotdetailspara = detailPageSoup.find("p", {'class' : 'lot-details-p'})
                        lotdetailscontent = lotdetailspara.renderContents().decode('utf-8')
                        brPattern = re.compile("<br\s*\/?>", re.IGNORECASE)
                        lotdetailsparts = re.split(brPattern, lotdetailscontent)
                        TITLE = lotdetailsparts[2].replace("\n", "").replace("\r", "")
                        TITLE = beginspacePattern.sub("", TITLE)
                        mediumcontent = lotdetailsparts[3].replace("\n", "").replace("\r", "")
                        mediumparts = mediumcontent.split("signed")
                        MEDIUM_RAW = mediumparts[0]
                        endcommaPattern = re.compile(",\s*$")
                        MEDIUM_RAW = endcommaPattern.sub("", MEDIUM_RAW)
                    except:
                        pass
                    try:
                        if len(All_Data) > 1:
                            estimation = [x for x in All_Data if "Estimate" in x.strip()]
                            ESTIMATE = estimation[0]
                            ESTIMATE = ESTIMATE.replace("Estimate:", "").strip().replace("$", "").replace(",","")
                            #print(ESTIMATE)
                            ESTIMATE = ESTIMATE + ' ' + 'USD'
                    except:
                        pass
                    try:
                        if len(All_Data) > 1:
                            priceRealized = [x for x in All_Data if "Sold" in x.strip()]
                            SOLD_PRICE = ''.join(re.findall("\d+",priceRealized[0]))
                            SOLD_PRICE=SOLD_PRICE+' '+'USD'
                    except:
                        pass
                    try:
                        if re.search(yearPattern, TITLE):
                            TITLE = MEDIUM_RAW
                            MEDIUM_RAW = ""
                        if MEDIUM_RAW == "":
                            MEDIUM_RAW = getMaterial(All_Data)
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
                    functionfile = detailPageSoup.findAll('div', {'class': 'lot-details-section'})[1].find('p')
                    functionfile = functionfile.renderContents()
                    functionfile = functionfile.split(b"<br/>")
                    SIGNATURE = getSignature(functionfile)
                    signedPattern = re.compile("signed", re.IGNORECASE)
                    emptyspacePattern = re.compile("^\s*$")
                    for f in functionfile:
                        if re.search(emptyspacePattern, str(SIGNATURE)) and re.search(signedPattern, f.decode('utf-8')):
                            SIGNATURE = f.decode('utf-8')
                    SIGNATURE = SIGNATURE.split(';')[0]
                    SIGNATURE = remove_tags(SIGNATURE).strip()
                    try:
                        PROVENANCE=detailPageSoup.findAll('div',{'class':'lot-details-section'})[1].getText(separator=u'@').strip().replace('@@@', '@').replace('@@', '@').replace('\n','')
                        PROVENANCE=''.join(re.findall('Provenance:@(.*?)@@C',PROVENANCE))
                        PROVENANCE=PROVENANCE.replace('@','.')
                    except:
                        pass
                    try:
                        EXHIBITION=detailPageSoup.findAll('div',{'class':'lot-details-section'})[1].getText(separator=u'@').strip().replace('@@@', '@').replace('@@', '@').replace('\n','')
                        EXHIBITION=''.join(re.findall('Exhibited:@(.*?)@@',EXHIBITION))
                        EXHIBITION=EXHIBITION.replace('@','.')
                    except:
                        pass
                    try:
                        LITERATURE=detailPageSoup.findAll('div',{'class':'lot-details-section'})[1].getText(separator=u'@').strip().replace('@@@', '@').replace('@@', '@').replace('\n','')
                        LITERATURE=''.join(re.findall('Literature:@(.*?)@@',LITERATURE))
                        LITERATURE=LITERATURE.replace('@','.')
                    except:
                        pass
                    try:
                        dimension = [x for x in All_Data if "inches" in x.strip().lower()]
                        dimension = dimension[0]
                        SIZE_IMAGE = dimension.replace('&nbsp;', ' ').strip()
                    except:
                        pass
                    try:
                        SIZE_IMAGE=re.sub('[(].*','',SIZE_IMAGE)
                        numberofcategory = re.findall("\sx\s", SIZE_IMAGE)
                        if numberofcategory.__len__() == 2:
                            CATEGORY = "3d"
                        if numberofcategory.__len__() == 1:
                            CATEGORY = "2d"
                        if numberofcategory.__len__() == 0:
                            CATEGORY = "3d"
                    except:
                        pass


                    def get_image(imageurl, path_name):
                        """
                        Get image based on url.
                        :return: Image name if everything OK, False otherwise
                        """
                        image_name = LOT.strip() + path_name
                        folderImage = 'doyle'
                        try:
                            image = requests.get(imageurl)
                        except:  # Little too wide, but work OK, no additional imports needed. Catch all conection problems
                            print(sys.exc_info()[1].__str__())
                            return False
                        if image.status_code == 200:  # we could have retrieved error page
                            #base_dir = path.join(path.dirname(path.realpath(__file__)), "images")  # Use your own path or "" to use current working directory. Folder must exist.
                            #base_dir = "/home/supmit/work/artwork/images/"
                            #with open(base_dir + folderImage + "/%s/"%auctionId.upper() + image_name, "wb") as f:
                            with open(imagedir + "/" + image_name, "wb") as f:
                                f.write(image.content)
                            return image_name
                    try:
                        defaultimageurl = detailPageSoup.find("div", {"class": "lot-single-image"}).find("img")['src']
                        imgtag = detailPageSoup.find("div", {"class": "lot-single-image"}).find("img")
                        if imgtag.has_attr('xoriginal') and imgtag['xoriginal'] != "":
                            defaultimageurl = self.domainUrl + imgtag['xoriginal']
                        imagename1 = self.getImagenameFromUrl(defaultimageurl)
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
                        imagepathparts = defaultimageurl.split("/")
                        defimageurl = "/".join(imagepathparts[:-2])
                        encryptedFilename = str(encryptedFilename).replace("b'", "")
                        encryptedFilename = str(encryptedFilename).replace("'", "")
                        IMAGE1_NAME = str(encryptedFilename) + ".jpg"
                        ARTWORK_IMAGES1 = defaultimageurl
                    except:
                        print("Error: %s"%sys.exc_info()[1].__str__())
                    try:
                        if defaultimageurl=='':
                            defaultimageurl = detailPageSoup.find("a", {"data-target": "#auction-carousel"}).find("img")['src']
                            imagename1 = self.getImagenameFromUrl(defaultimageurl)
                            imagename1 = str(imagename1)
                            imagename1 = imagename1.replace("b'", "").replace("'", "")
                            processedAuctionTitle = AUCTION_NAME.replace(" ", "_")
                            processedArtistName = ARTIST.replace(" ", "_")
                            processedArtistName = unidecode.unidecode(processedArtistName)
                            processedArtworkName = TITLE.replace(" ", "_")
                            sublot_number = ""
                            #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + self.auctionId + "__" + str(LOT) + "__" + sublot_number
                            newname1 = self.auctionId + "__" + processedArtistName + "__" + str(LOT) + "_b"
                            #encryptedFilename = self.encryptFilename(newname1)
                            encryptedFilename = newname1
                            imagepathparts = defaultimageurl.split("/")
                            defimageurl = "/".join(imagepathparts[:-2])
                            encryptedFilename = str(encryptedFilename).replace("b'", "")
                            encryptedFilename = str(encryptedFilename).replace("'", "")
                            IMAGE1_NAME = str(encryptedFilename) + ".jpg"
                            ARTWORK_IMAGES1 = defaultimageurl
                    except:
                        pass
                    allimages = detailPageSoup.find_all("img", {'typeof' : 'foaf:Image'})
                    altimages = []
                    endjpegPattern = re.compile("\.jpe?g$")
                    for img in allimages:
                        if 'xoriginal' not in img.attrs.keys():
                            continue
                        xorgurl = "https://doyle.com" + img['xoriginal']
                        #print(xorgurl)
                        if re.search(endjpegPattern, xorgurl):
                            altimages.append(xorgurl)
                    imgctr = 2
                    if altimages.__len__() > 0:
                        altimage2 = altimages[0]
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
                        IMAGE2_NAME = str(encryptedFilename) + ".jpg"
                        ARTWORK_IMAGES2 = altimage2
                        imgctr += 1
                    if altimages.__len__() > 1:
                        altimage2 = altimages[1]
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
                        IMAGE3_NAME = str(encryptedFilename) + ".jpg"
                        ARTWORK_IMAGES3 = altimage2
                        imgctr += 1
                    if altimages.__len__() > 2:
                        altimage2 = altimages[2]
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
                        IMAGE4_NAME = str(encryptedFilename) + ".jpg"
                        ARTWORK_IMAGES4 = altimage2
                        imgctr += 1
                    if altimages.__len__() > 3:
                        altimage2 = altimages[3]
                        altimage2parts = altimage2.split("/")
                        altimageurl = "/".join(altimage2parts[:-2])
                        processedAuctionTitle = AUCTION_NAME.replace(" ", "_")
                        processedArtistName = ARTIST.replace(" ", "_")
                        processedArtworkName = TITLE.replace(" ", "_")
                        sublot_number = ""
                        newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + self.auctionId + "__" + str(LOT) + "__" + sublot_number
                        encryptedFilename = self.encryptFilename(newname1)
                        IMAGE5_NAME = str(encryptedFilename) + ".jpg"
                        ARTWORK_IMAGES5 = altimage2
                    try:
                        date = detailPageSoup.find('div', {'class': 'auction-date'}).getText()
                        date = ''.join(re.findall('\s(.*?)\sat', date))
                        date_data = date.replace(',', '').split(' ')
                        date = date_data[1]
                        months = date_data[0]
                        year = date_data[-1][:-2]
                        AUCTION_DATE = date + '-' + months.replace('.', '')[:3] + '-' +  year[2:]
                    except:
                        pass
                    AUCTION_HOUSE='Doyle'
                    SALENUMBER=auctionId.upper()
                    AUCTION_DATE=auctionDate
                    try:
                        years = re.findall("\d{4}", All_Data[6])
                        BIRTHDATE, DEATHDATE = ['', '']
                        if len(years) > 1:
                            BIRTHDATE = years[0]
                            DEATHDATE = years[1]
                        elif len(years) == 1:
                            BIRTHDATE = years[0]
                    except:
                        pass
                    ARTIST = ARTIST.encode('ascii', 'ignore').decode('ascii')
                    if TITLE != "":
                        TITLE = TITLE.encode('ascii', 'ignore').decode('ascii')
                    SHEET_SIZE = ''
                    sizefile=[x for x in All_Data if "sheet"  or "each" or "sight" in x.strip().lower()]
                    SHEET_SIZE=sizefile[0]
                    SIZE_IMAGE=SIZE_IMAGE.replace(SHEET_SIZE,'')
                    if ";" in SIZE_IMAGE or "," in SIZE_IMAGE:
                        sizeparts = re.split("[;\,]+", SIZE_IMAGE)
                        if sizeparts.__len__() > 1:
                            SIZE_IMAGE = sizeparts[0]
                            SHEET_SIZE = sizeparts[1]
                            SHEET_SIZE = beginspacePattern.sub("", SHEET_SIZE)
                        elif sizeparts.__len__() > 0:
                            SIZE_IMAGE = sizeparts[0]
                    #print("Size: " + SIZE_IMAGE)
                    #print("Sheet Size: " + SHEET_SIZE)
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
                    rX = lambda x: " ".join(
                        x.replace("\n", "").replace("\t", "").replace('"', "").splitlines())
                    estimateparts = ESTIMATE.split(" - ")
                    PRICE_EST_MIN = estimateparts[0]
                    PRICE_EST_MAX = ""
                    if estimateparts.__len__() > 1:
                        estimateparts[1] = re.sub(re.compile("[A-Za-z]{3}"), "", estimateparts[1])
                        PRICE_EST_MAX = estimateparts[1]
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
                    PRICE_EST_MIN = PRICE_EST_MIN.replace(",", "").replace(" ", "")
                    PRICE_EST_MAX = PRICE_EST_MAX.replace(",", "").replace(" ", "")
                    SOLD_PRICE = SOLD_PRICE.replace(",", "").replace(" ", "")
                    #print("Title: %s\nMedium: %s"%(TITLE, MEDIUM_RAW))
                    fp.write(AUCTION_HOUSE.replace(",", ".") + ', ' + AUCTION_LOCATION.replace(",", ".") + ', ' + SALENUMBER.replace(",", ".") + ', ' + AUCTION_DATE.replace(",", ".") + ', ' + AUCTION_END_DATE + ', ' + AUCTION_NAME.replace(",", "").replace(";", "") + ', ' + LOT.replace(",", ".") + ', ' + SUBLOT_NUMBER.replace(",", "") + ', ' + PRICE_KIND + ', ' + PRICE_EST_MIN + ', ' + PRICE_EST_MAX + ', ' + SOLD_PRICE.replace(",", ".") + ', ' + ARTIST.replace(",", '') + ', ' + rX(BIRTHDATE) + ', ' + rX(DEATHDATE) + ', ' + ARTIST_NATIONALITY + ', ' + rX(TITLE.replace(",", ".")) + ', ' + ART_YEAR_ID + ', ' + rX(YEARFROM.replace(",", ".")) + ', ' + rX(YEARTO.replace(",", ".")) + ', ' + rX(MEDIUM_RAW.replace(",", ".")) + ', ' + ARTWORK_CATEGORY + ', ' + rX(SIGNATURE.replace(",", ".")) + ', ' + rX(EDITIONTYPE.replace(",", ".")) + ', ' + ARTWORK_DESC.replace(",", ".").replace(";", " ") + ', ' + ART_HEIGHT + ', ' + ART_WIDTH + ', ' + ART_DEPTH + ', ' + rX(SIZE_IMAGE.replace(",", ".")) + ', ' + AUCTION_MEASUREUNIT + ', ' + ART_CONDITION + ', ' + rX(PROVENANCE.replace(",", ".")) + ', ' + rX(EXHIBITION.replace(",", ".")) + ', ' + rX(LITERATURE.replace(",", ".")) + ', ' + ARTWORK_IMAGES1 + ', ' + ARTWORK_IMAGES2 + ', ' + ARTWORK_IMAGES3 + ', ' + ARTWORK_IMAGES4 + ', ' + ARTWORK_IMAGES5 + ', ' + IMAGE1_NAME + ', ' + IMAGE2_NAME + ', ' + IMAGE3_NAME + ', ' + IMAGE4_NAME + ', ' + IMAGE5_NAME + ', ' + rX(LOT_URL.replace(",", ".")) + "\n")
                    


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
    pageurl = "http://216.137.189.57:8080/scrapers/finish/?scrapername=Doyle&auctionnumber=%s&auctionurl=%s&scrapertype=2"%(auctionno, urllib.parse.quote(auctionurl))
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
    scrapperName = "Doyle"
    downloadImages = True
    if sys.argv.__len__() > 2 and sys.argv[2] == "True":
        downloadImages = "True"
    fp = open(csvpath, "w")
    Scrape(mainUrl, auctionId, csvpath, imagedir, downloadImages, scrapperName,  fp)
    fp.close()
    updatestatus(auctionId, mainUrl)


# python doyle.py https://doyle.com/auctions/21fa03-fine-art/catalogue 21fa03 /home/supmit/work/art2/doyle_21fa03.csv /home/supmit/work/art2/images/doyle/21FA03 0 0

# python doyle.py https://doyle.com/auctions/21pt04-20th-century-abstraction/catalogue 21pt04 /home/supmit/work/art2/doyle_21pt04.csv /home/supmit/work/art2/images/doyle/21pt04 0 0


