# -*- coding: utf-8 -*-
import os, sys, re
import urllib, urllib.request
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import unicodedata
import io
import gzip
import time
import simplejson as json
import datetime
import string
import requests
from requests_toolbelt.adapters.source import SourceAddressAdapter
from urllib.parse import urlencode, quote_plus
import html
from cryptography.fernet import Fernet
import csv
import unidecode

partialUrlPattern = re.compile("^/\w+")

def decodeHtmlEntities(content):
    entitiesDict = {'&nbsp;' : ' ', '&quot;' : '"', '&lt;' : '<', '&gt;' : '>', '&amp;' : '&', '&apos;' : "'", '&#160;' : ' ', '&#60;' : '<', '&#62;' : '>', '&#38;' : '&', '&#34;' : '"', '&#39;' : "'"}
    for entity in entitiesDict.keys():
        content = content.replace(entity, entitiesDict[entity])
    return(content)


# Implement signal handler for ctrl+c here.
def setSignal():
    pass

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


def unicodefraction_to_decimal(v):
    fracPattern = re.compile("(\d*)\s*([^\s\.\,;a-zA-Z]+)")
    fps = re.search(fracPattern, v)
    if fps:
        fpsg = fps.groups()
        wholenumber = fpsg[0]
        fraction = fpsg[1]
        decimal = round(unicodedata.numeric(fraction), 3)
        if wholenumber:
            decimalstr = str(decimal).replace("0.", ".")
        else:
            decimalstr = str(decimal)
        value = wholenumber + decimalstr
        return value
    return v


class SwannBot(object):
    
    htmltagPattern = re.compile("\<\/?[^\<\>]*\/?\>", re.DOTALL)
    pathEndingWithSlashPattern = re.compile(r"\/$")

    htmlEntitiesDict = {'&nbsp;' : ' ', '&#160;' : ' ', '&amp;' : '&', '&#38;' : '&', '&lt;' : '<', '&#60;' : '<', '&gt;' : '>', '&#62;' : '>', '&apos;' : '\'', '&#39;' : '\'', '&quot;' : '"', '&#34;' : '"'}

    def __init__(self, auctionurl, auctionnumber):
        # Create the opener object(s). Might need more than one type if we need to get pages with unwanted redirects.
        self.opener = urllib.request.build_opener(urllib.request.HTTPHandler(), urllib.request.HTTPSHandler()) # This is my normal opener....
        self.no_redirect_opener = urllib.request.build_opener(urllib.request.HTTPHandler(), urllib.request.HTTPSHandler(), NoRedirectHandler()) # ... and this one won't handle redirects.
        #self.debug_opener = urllib.request.build_opener(urllib.request.HTTPHandler(debuglevel=1))
        # Initialize some object properties.
        self.sessionCookies = ""
        self.httpHeaders = { 'User-Agent' : r'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36',  'Accept' : 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8', 'Accept-Language' : 'en-us,en;q=0.5', 'Accept-Encoding' : 'gzip,deflate', 'Accept-Charset' : 'ISO-8859-1,utf-8;q=0.7,*;q=0.7', 'Keep-Alive' : '115', 'Connection' : 'keep-alive', }
        self.httpHeaders['cache-control'] = "max-age=0"
        self.httpHeaders['upgrade-insecure-requests'] = "1"
        self.httpHeaders['sec-fetch-dest'] = "document"
        self.httpHeaders['sec-fetch-mode'] = "navigate"
        self.httpHeaders['sec-fetch-site'] = "same-origin"
        self.httpHeaders['sec-fetch-user'] = "?1"
        self.homeDir = os.getcwd()
        self.requestUrl = auctionurl
        parsedUrl = urlparse(self.requestUrl)
        self.baseUrl = parsedUrl.scheme + "://" + parsedUrl.netloc
        #print(self.requestUrl)
        self.pageRequest = urllib.request.Request(self.requestUrl, headers=self.httpHeaders)
        self.pageResponse = None
        self.requestMethod = "GET"
        self.postData = {}
        try:
            self.pageResponse = self.opener.open(self.pageRequest)
            headers = self.pageResponse.getheaders()
            #print(headers)
            if "Location" in headers:
                self.requestUrl = headers["Location"]
                self.pageRequest = urllib.request.Request(self.requestUrl, headers=self.httpHeaders)
                try:
                    self.pageResponse = self.no_redirect_opener.open(self.pageRequest)
                except:
                    print ("Couldn't fetch page due to limited connectivity. Please check your internet connection and try again. %s"%sys.exc_info()[1].__str__())
                    sys.exit()
        except:
            print ("Couldn't fetch page due to limited connectivity. Please check your internet connection and try again. %s"%sys.exc_info()[1].__str__())
            sys.exit()
        self.httpHeaders["Referer"] = self.requestUrl
        self.sessionCookies = self.__class__._getCookieFromResponse(self.pageResponse)
        self.httpHeaders["Cookie"] = self.sessionCookies
        # Initialize the account related variables...
        self.currentPageContent = self.__class__._decodeGzippedContent(self.getPageContent())
        self.currentPageNumber = 1 # Page number of the page that is currently being read.
        self.data = {'auction_house_name': '', 'auction_location' : '', 'auction_num' : '', 'auction_start_date' : '', 'auction_end_date' : '', 'auction_name' : '', 'lot_num' : '', 'sublot_num' : '', 'price_kind' : '', 'price_estimate_min' : '', 'price_estimate_max' : '', 'price_sold' : '', 'artist_name' : '', 'artist_birth' : '', 'artist_death' : '', 'artist_nationality' : '', 'artwork_name' : '', 'artwork_year_identifier' : '', 'artwork_start_year' : '', 'artwork_end_year' : '', 'artwork_materials' : '', 'artwork_category' : '', 'artwork_markings' : '', 'artwork_edition' : '', 'artwork_description' : '', 'artwork_measurements_height' : '', 'artwork_measurements_width' : '', 'artwork_measurements_depth' : '', 'artwork_size_notes' : '', 'auction_measureunit' : '', 'artwork_condition_in' : '', 'artwork_provenance' : '', 'artwork_exhibited' : '', 'artwork_literature' : '', 'artwork_images1' : '', 'artwork_images2' : '', 'artwork_images3' : '', 'artwork_images4' : '', 'artwork_images5' : '', 'image1_name' : '', 'image2_name' : '', 'image3_name' : '', 'image4_name' : '', 'image5_name' : '', 'lot_origin_url' : ''}
        self.saleno = auctionnumber
        self.auctiondate = ""
        self.auctiontitle = ""



    def _decodeGzippedContent(cls, encoded_content):
        response_stream = io.BytesIO(encoded_content)
        decoded_content = ""
        try:
            gzipper = gzip.GzipFile(fileobj=response_stream)
            decoded_content = gzipper.read()
        except: # Maybe this isn't gzipped content after all....
            decoded_content = encoded_content
        decoded_content = decoded_content.decode('utf-8')
        return(decoded_content)

    _decodeGzippedContent = classmethod(_decodeGzippedContent)


    def _getCookieFromResponse(cls, lastHttpResponse):
        cookies = ""
        responseCookies = lastHttpResponse.getheader("Set-Cookie")
        pathPattern = re.compile(r"Path=/;", re.IGNORECASE)
        domainPattern = re.compile(r"Domain=[^;,]+(;|,)", re.IGNORECASE)
        expiresPattern = re.compile(r"Expires=[^;]+;", re.IGNORECASE)
        maxagePattern = re.compile(r"Max-Age=[^;]+;", re.IGNORECASE)
        samesitePattern = re.compile(r"SameSite=[^;]+;", re.IGNORECASE)
        securePattern = re.compile(r"secure;?", re.IGNORECASE)
        httponlyPattern = re.compile(r"HttpOnly;?", re.IGNORECASE)
        if responseCookies and responseCookies.__len__() > 1:
            cookieParts = responseCookies.split("Path=/")
            for i in range(cookieParts.__len__()):
                cookieParts[i] = re.sub(domainPattern, "", cookieParts[i])
                cookieParts[i] = re.sub(expiresPattern, "", cookieParts[i])
                cookieParts[i] = re.sub(maxagePattern, "", cookieParts[i])
                cookieParts[i] = re.sub(samesitePattern, "", cookieParts[i])
                cookieParts[i] = re.sub(securePattern, "", cookieParts[i])
                cookieParts[i] = re.sub(pathPattern, "", cookieParts[i])
                cookieParts[i] = re.sub(httponlyPattern, "", cookieParts[i])
                cookieParts[i] = cookieParts[i].replace(",", "")
                cookieParts[i] = re.sub(re.compile("\s+", re.DOTALL), "", cookieParts[i])
                cookies += cookieParts[i]
        cookies = cookies.replace(";;", ";")
        return(cookies)

    _getCookieFromResponse = classmethod(_getCookieFromResponse)


    def getPageContent(self):
        try:
            return(self.pageResponse.read())
        except:
            return(b"")

    def formatDate(cls, datestr):
        mondict = {'January' : '01', 'February' : '02', 'March' : '03', 'April' : '04', 'May' : '05', 'June' : '06', 'July' : '07', 'August' : '08', 'September' : '09', 'October' : '10', 'November' : '11', 'December' : '12' }
        mondict2 = {'Jan' : '01', 'Feb' : '02', 'Mar' : '03', 'Apr' : '04', 'May' : '05', 'Jun' : '06', 'Jul' : '07', 'Aug' : '08', 'Sep' : '09', 'Oct' : '10', 'Nov' : '11', 'Dec' : '12' }
        mondict3 = {'jan.' : '01', 'fév.' : '02', 'mar.' : '03', 'avr.' : '04', 'mai.' : '05', 'jui.' : '06', 'jul.' : '07', 'aoû.' : '08', 'sep.' : '09', 'oct.' : '10', 'nov.' : '11', 'déc.' : '12' }
        mondict4 = {'Janvier' : '01', 'Février' : '02', 'Mars' : '03', 'Avril' : '04', 'Mai' : '05', 'Juin' : '06', 'Juillet' : '07', 'Août' : '08', 'Septembre' : '09', 'Octobre' : '10', 'Novembre' : '11', 'Décembre' : '12'}
        datestrcomponents = datestr.split(" ")
        if not datestr:
            return ""
        dd = datestrcomponents[0]
        mm = '01'
        datestrcomponents[1] = datestrcomponents[1].capitalize()
        if datestrcomponents[1] in mondict.keys():
            mm = mondict[datestrcomponents[1]]
        else:
            try:
                mm = mondict2[datestrcomponents[1]]
            except:
                pass
        yyyy = datestrcomponents[2]
        yearPattern = re.compile("\d{4}")
        if not re.search(yearPattern, yyyy):
            yyyy = "2021"
        retdate = mm + "/" + dd + "/" + yyyy
        return retdate

    formatDate = classmethod(formatDate)


    def fractionToDecimalSize(self, sizestring):
        sizestringparts = sizestring.split("x")
        if sizestringparts.__len__() < 1:
            sizestringparts = sizestring.split("by")
        unitPattern = re.compile("(\s*(in)|(cm)\s*$)", re.IGNORECASE)
        ups = re.search(unitPattern, sizestringparts[-1])
        unit = ""
        if ups:
            upsg = ups.groups()
            unit = upsg[0]
        sizestringparts[-1] = unitPattern.sub("", sizestringparts[-1])
        decimalsizeparts = []
        beginspacePattern = re.compile("^\s+")
        endspacePattern = re.compile("\s+$")
        for szpart in sizestringparts:
            szpart = beginspacePattern.sub("", szpart)
            szpart = endspacePattern.sub("", szpart)
            d_szpart = unicodefraction_to_decimal(szpart)
            decimalsizeparts.append(d_szpart)
        decimalsize = " x ".join(decimalsizeparts)
        decimalsize += " " + unit
        return decimalsize


    def getLotsFromPage(self):
        pageContent = self.currentPageContent
        soup = BeautifulSoup(pageContent, features="html.parser")
        timingdivtags = soup.find_all("div", {'class' : 'feature_detail--timing'})
        if timingdivtags.__len__() > 0:
            timingcontents = timingdivtags[0].renderContents().decode('utf-8')
            datePattern = re.compile("([a-zA-Z]{3}\s+\d{1,2},\s+\d{4})")
            dps = re.search(datePattern, timingcontents)
            if dps:
                self.auctiondate = dps.groups()[0]
        alltitletags = soup.find_all("title")
        if alltitletags.__len__() > 0:
            title = alltitletags[0].renderContents().decode('utf-8')
            titleparts = title.split("|")
            if titleparts.__len__() > 0:
                self.auctiontitle = titleparts[0]
                trailingspacePattern = re.compile("\s+$")
                self.auctiontitle = trailingspacePattern.sub("", self.auctiontitle)
        ulblocks = soup.find_all("ul", {'id' : 'ullist'})
        if ulblocks.__len__() > 0:
            ulcontent = ulblocks[0].renderContents().decode('utf-8')
            s = BeautifulSoup(ulcontent, features="html.parser")
            lotblocks = s.find_all("li")
            return lotblocks
        return []
        

    def getDetailsPage(self, detailUrl):
        self.requestUrl = detailUrl
        self.pageRequest = urllib.request.Request(self.requestUrl, headers=self.httpHeaders)
        self.pageResponse = None
        self.postData = {}
        try:
            self.pageResponse = self.opener.open(self.pageRequest)
        except:
            print ("Error: %s"%sys.exc_info()[1].__str__())
        self.currentPageContent = self.__class__._decodeGzippedContent(self.getPageContent())
        return self.currentPageContent


    def encryptFilename(self, filename):
        k = Fernet.generate_key()
        f = Fernet(k)
        encfilename = f.encrypt(filename.encode())
        return encfilename


    def renameImagefile(self, basepath, imagefilename, mappedImagename):
        oldfilename = basepath + "/" + imagefilename
        newfilename = basepath + "/" + mappedImagename
        try:
            os.rename(oldfilename, newfilename)
        except:
            print(oldfilename)


    def getImagenameFromUrl(self, imageUrl):
        urlparts = imageUrl.split("/")
        imagefilepart = urlparts[-1]
        imagefilenameparts = imagefilepart.split("?")
        imagefilename = imagefilenameparts[0]
        return imagefilename


    def parseDetailPage(self, detailsPage, lotno, imagepath, artistname, artworkname, downloadimages):
        baseUrl = "https://catalogue.swanngalleries.com"
        detailData = {}
        soup = BeautifulSoup(detailsPage, features="html.parser")
        detailsdivlist = soup.find_all("div", {'class' : 'lot-detail_description'})
        if detailsdivlist.__len__() == 0:
            return detailData
        mediumPattern = re.compile("(gold)|(silver)|(brass)|(bronze)|(wood)|(porcelain)|(stone)|(marble)|(metal)|(steel)|(iron)|(glass)|(plexiglas)|(chromogenic)|(paper)|(canvas)|(masonite)|(newsprint)|(silkscreen)|(parchment)|(linen)|(inkjet)|(ink\s+jet)|(pigment)|(\stin\s)|(photogravure)|(^oil\s+)|(\s+panel\s+)|(terracotta)|(ivory)|(\s+oak\s+)|(^oak\s+)|(\s+oak$)|(alabaster)|(\s+ink\s+)|(pencil)|(albumen)|(oil\s+)|(\s+oil)|(panel)", re.DOTALL|re.IGNORECASE)
        nonenglishmediumPattern = re.compile("(crayon)|(encre)|(plume)|(plume\s+et\s+encre)|(papier)|(pastel)|(craie)|(gouachée)|(aquarelle)|(lithographique)|(plomb)|(huile)|(cuivre)|(toile)|(bronze)|(Plâtre)|(en\s+terre\s+de\s+faïence)", re.IGNORECASE|re.DOTALL)
        signedPattern = re.compile("signed\s+", re.IGNORECASE)
        editionPattern = re.compile("edition", re.IGNORECASE)
        sizePattern = re.compile("([\d\.]+\s*x\s*[\d\.]+\s*x?\s*[\d\.]*\s+mm);", re.IGNORECASE)
        sizePattern2 = re.compile("([\d,\.]+\s*x\s*[\d,\.]+\s*cm)", re.IGNORECASE)
        sizePattern3 = re.compile("([\d,]+\s*cm)", re.IGNORECASE)
        sizePattern4 = re.compile("([\d,]+\s*mm)", re.IGNORECASE)
        yearPattern = re.compile("(\d{4})\s*\-?\s*(\d{0,4})", re.DOTALL)
        measureunitPattern = re.compile("([a-zA-Z]{2})")
        multispacePattern = re.compile("\s+")
        beginspacePattern = re.compile("^\s+")
        matcatdict_en = {}
        matcatdict_fr = {}
        #with open("docs/fineart_materials.csv", newline='') as mapfile:
        with open("/Users/saiswarupsahu/freelanceprojectchetan/docs/fineart_materials.csv", newline='') as mapfile:
            mapreader = csv.reader(mapfile, delimiter=",", quotechar='"')
            for maprow in mapreader:
                matcatdict_en[maprow[1]] = maprow[3]
                matcatdict_fr[maprow[2]] = maprow[3]
        mapfile.close()
        divcontent = detailsdivlist[0].renderContents().decode('utf-8')
        divcontent = self.__class__.htmltagPattern.sub("", divcontent)
        divcontent = divcontent.replace("\n", "").replace("\r", "")
        divparts = divcontent.split(".")
        ctr = 0
        for div in divparts:
            div = multispacePattern.sub(" ", div)
            div = div.replace('"', "'")
            sps = re.search(signedPattern, div)
            if sps and 'artwork_markings' not in detailData.keys():
                detailData['artwork_markings'] = div
                detailData['artwork_markings'] = beginspacePattern.sub("", detailData['artwork_markings'])
            zps = re.search(sizePattern, div)
            if zps and 'artwork_size_notes' not in detailData.keys():
                detailData['artwork_size_notes'] = zps.groups()[0]
                sizeparts = detailData['artwork_size_notes'].split("x")
                detailData['artwork_measurements_height'] = sizeparts[0]
                if sizeparts.__len__() > 1:
                    mups = re.search(measureunitPattern, sizeparts[1])
                    if mups:
                        detailData['auction_measureunit'] = mups.groups()[0]
                        sizeparts[1] = measureunitPattern.sub("", sizeparts[1])
                    detailData['artwork_measurements_width'] = sizeparts[1]
                if sizeparts.__len__() > 2:
                    mups = re.search(measureunitPattern, sizeparts[2])
                    if mups:
                        detailData['auction_measureunit'] = mups.groups()[0]
                        sizeparts[2] = measureunitPattern.sub("", sizeparts[2])
                    detailData['artwork_measurements_depth'] = sizeparts[2]
            zps2 = re.search(sizePattern2, div)
            if zps2 and 'artwork_size_notes' not in detailData.keys():
                detailData['artwork_size_notes'] = zps2.groups()[0]
                sizeparts = detailData['artwork_size_notes'].split("x")
                detailData['artwork_measurements_height'] = sizeparts[0]
                if sizeparts.__len__() > 1:
                    mups = re.search(measureunitPattern, sizeparts[1])
                    if mups:
                        detailData['auction_measureunit'] = mups.groups()[0]
                        sizeparts[1] = measureunitPattern.sub("", sizeparts[1])
                    detailData['artwork_measurements_width'] = sizeparts[1]
            zps3 = re.search(sizePattern3, div)
            if zps3 and 'artwork_size_notes' not in detailData.keys():
                detailData['artwork_size_notes'] = zps3.groups()[0]
                detailData['artwork_measurements_height'] = zps3.groups()[0]
                mups = re.search(measureunitPattern, detailData['artwork_measurements_height'])
                if mups:
                    detailData['auction_measureunit'] = mups.groups()[0]
                    detailData['artwork_measurements_height'] = measureunitPattern.sub("", detailData['artwork_measurements_height'])
            zps4 = re.search(sizePattern4, div)
            if zps4 and 'artwork_size_notes' not in detailData.keys():
                detailData['artwork_size_notes'] = zps4.groups()[0]
                detailData['artwork_measurements_height'] = zps4.groups()[0]
                mups = re.search(measureunitPattern, detailData['artwork_measurements_height'])
                if mups:
                    detailData['auction_measureunit'] = mups.groups()[0]
                    detailData['artwork_measurements_height'] = measureunitPattern.sub("", detailData['artwork_measurements_height'])
            mps = re.search(mediumPattern, div)
            if mps and 'artwork_materials' not in detailData.keys():
                detailData['artwork_materials'] = div
                detailData['artwork_materials'] = beginspacePattern.sub("", detailData['artwork_materials'])
        if not 'artwork_size_notes' not in detailData.keys():
            zps4 = re.search(sizePattern, divcontent)
            if zps4:
                detailData['artwork_size_notes'] = zps4.groups()[0]
        if 'artwork_materials' in detailData.keys():
            yps = re.search(yearPattern, detailData['artwork_materials'])
            if yps:
                detailData['artwork_start_year'] = yps.groups()[0]
                detailData['artwork_end_year'] = yps.groups()[1]
                detailData['artwork_materials'] = yearPattern.sub("", detailData['artwork_materials'])
                detailData['artwork_materials'] = detailData['artwork_materials'].replace("circa", "")
                endcommaPattern = re.compile(",\s*$")
                detailData['artwork_materials'] = endcommaPattern.sub("", detailData['artwork_materials'])
            if "," in detailData['artwork_materials']:
                mediumparts = detailData['artwork_materials'].split(",")
                detailData['artwork_materials'] = mediumparts[0]
        doublebrPattern = re.compile("<br\s*\/?>\s*<br\s*\/?>", re.IGNORECASE|re.DOTALL)
        divcomponents = re.split(doublebrPattern, detailsdivlist[0].renderContents().decode('utf-8'))
        provenancePattern = re.compile("ex\-collection", re.IGNORECASE|re.DOTALL)
        begincommaPattern = re.compile("^,")
        for div in divcomponents:
            div = self.__class__.htmltagPattern.sub("", div)
            pps = re.search(provenancePattern, div)
            if pps and 'artwork_provenance' not in detailData.keys():
                detailData['artwork_provenance'] = div
        if 'artwork_provenance' not in detailData.keys():
            detailData['artwork_provenance'] = divparts[-2]
        if 'artwork_provenance' in detailData.keys():
            detailData['artwork_provenance'] = beginspacePattern.sub("", detailData['artwork_provenance'])
            detailData['artwork_provenance'] = begincommaPattern.sub("", detailData['artwork_provenance'])
        imagesultags = soup.find_all("ul", {'class' : 'slides'})
        defaultimageurl = ""
        altimages = []
        if imagesultags.__len__() > 0:
            imagesultag = imagesultags[0]
            allimagetags = imagesultag.find_all("img", {'class' : 'pli_image'})
            if allimagetags.__len__() > 0:
                defaultimageurl = allimagetags[0]['src']    
            if allimagetags.__len__() > 1:
                ictr = 0
                for ictr in range(1, allimagetags.__len__()):
                    altimg = allimagetags[ictr]['src']
                    altimages.append(altimg)
        imagename1 = self.getImagenameFromUrl(defaultimageurl)
        imagename1 = str(imagename1)
        imagename1 = imagename1.replace("b'", "").replace("'", "")
        auctiontitle = self.auctiontitle.replace(" ", "_")
        processedAuctionTitle = auctiontitle.replace(" ", "_")
        processedArtistName = artistname.replace(" ", "_")
        processedArtistName = unidecode.unidecode(processedArtistName)
        processedArtworkName = artworkname.replace(" ", "_")
        sublot_number = ""
        #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + self.saleno + "__" + lotno + "__" + sublot_number
        newname1 = self.saleno + "__" + processedArtistName + "__" + lotno + "_a"
        #encryptedFilename = self.encryptFilename(newname1)
        encryptedFilename = newname1
        imagepathparts = defaultimageurl.split("/")
        defimageurl = "/".join(imagepathparts[:-2])
        encryptedFilename = str(encryptedFilename).replace("b'", "")
        encryptedFilename = str(encryptedFilename).replace("'", "")
        detailData['image1_name'] = str(encryptedFilename) + ".jpg"
        detailData['artwork_images1'] = defaultimageurl
        imgctr = 2
        if altimages.__len__() > 0:
            altimage2 = altimages[0]
            altimage2parts = altimage2.split("/")
            altimageurl = "/".join(altimage2parts[:-2])
            processedArtistName = artistname.replace(" ", "_")
            processedArtistName = unidecode.unidecode(processedArtistName)
            processedArtworkName = artworkname.replace(" ", "_")
            sublot_number = ""
            #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + self.saleno + "__" + lotno + "__" + sublot_number
            newname1 = self.saleno + "__" + processedArtistName + "__" + lotno + "_b"
            #encryptedFilename = self.encryptFilename(newname1)
            encryptedFilename = newname1
            detailData['image' + str(imgctr) + '_name'] = str(encryptedFilename) + ".jpg"
            detailData['artwork_images' + str(imgctr)] = altimage2
            imgctr += 1
        if altimages.__len__() > 1:
            altimage2 = altimages[1]
            altimage2parts = altimage2.split("/")
            altimageurl = "/".join(altimage2parts[:-2])
            processedArtistName = artistname.replace(" ", "_")
            processedArtistName = unidecode.unidecode(processedArtistName)
            processedArtworkName = artworkname.replace(" ", "_")
            sublot_number = ""
            #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + self.saleno + "__" + lotno + "__" + sublot_number
            newname1 = self.saleno + "__" + processedArtistName + "__" + lotno + "_c"
            #encryptedFilename = self.encryptFilename(newname1)
            encryptedFilename = newname1
            detailData['image' + str(imgctr) + '_name'] = str(encryptedFilename) + ".jpg"
            detailData['artwork_images' + str(imgctr)] = altimage2
            imgctr += 1
        if altimages.__len__() > 2:
            altimage2 = altimages[2]
            altimage2parts = altimage2.split("/")
            altimageurl = "/".join(altimage2parts[:-2])
            processedArtistName = artistname.replace(" ", "_")
            processedArtistName = unidecode.unidecode(processedArtistName)
            processedArtworkName = artworkname.replace(" ", "_")
            sublot_number = ""
            #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + self.saleno + "__" + lotno + "__" + sublot_number
            newname1 = self.saleno + "__" + processedArtistName + "__" + lotno + "_d"
            #encryptedFilename = self.encryptFilename(newname1)
            encryptedFilename = newname1
            detailData['image' + str(imgctr) + '_name'] = str(encryptedFilename) + ".jpg"
            detailData['artwork_images' + str(imgctr)] = altimage2
            imgctr += 1
        if altimages.__len__() > 3:
            altimage2 = altimages[3]
            altimage2parts = altimage2.split("/")
            altimageurl = "/".join(altimage2parts[:-2])
            processedArtistName = artistname.replace(" ", "_")
            processedArtistName = unidecode.unidecode(processedArtistName)
            processedArtworkName = artworkname.replace(" ", "_")
            sublot_number = ""
            #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + self.saleno + "__" + lotno + "__" + sublot_number
            newname1 = self.saleno + "__" + processedArtistName + "__" + lotno + "_e"
            #encryptedFilename = self.encryptFilename(newname1)
            encryptedFilename = newname1
            detailData['image' + str(imgctr) + '_name'] = str(encryptedFilename) + ".jpg"
            detailData['artwork_images' + str(imgctr)] = altimage2
        if 'artwork_materials' in detailData.keys() and 'artwork_category' not in detailData.keys():
            materials = detailData['artwork_materials']
            materialparts = materials.split(" ")
            catfound = 0
            for matpart in materialparts:
                if matpart in ['in', 'on', 'of', 'the', 'from']:
                    continue
                try:
                    matPattern = re.compile(matpart, re.IGNORECASE|re.DOTALL)
                    for enkey in matcatdict_en.keys():
                        if re.search(matPattern, enkey):
                            detailData['artwork_category'] = matcatdict_en[enkey]
                            catfound = 1
                            break
                    for frkey in matcatdict_fr.keys():
                        if re.search(matPattern, frkey):
                            detailData['artwork_category'] = matcatdict_fr[frkey]
                            catfound = 1
                            break
                    if catfound:
                        break
                except:
                    pass
        descdivtags = soup.find_all("div", {'class' : 'lot-detail_description'})
        if descdivtags.__len__() > 0:
            desccontents = descdivtags[0].renderContents().decode('utf-8')
            desccontents = desccontents.replace("\n", "").replace("\r", "")
            desccontents = self.__class__.htmltagPattern.sub("", desccontents)
            detailData['artwork_description'] = desccontents
            detailData['artwork_description'] = detailData['artwork_description'].strip()
            detailData['artwork_description'] = self.__class__.htmltagPattern.sub("", detailData['artwork_description'])
            detailData['artwork_description'] = detailData['artwork_description'].replace("\n", " ")
            detailData['artwork_description'] = detailData['artwork_description'].replace("\r", " ")
            detailData['artwork_description'] = detailData['artwork_description'].replace('"', "'")
            detailData['artwork_description'] = detailData['artwork_description'].replace("PROVENANCE", "<br><strong>Provenance</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("LITERATURE", "<br><strong>Literature</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("EXHIBITED", "<br><strong>Exhibited</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("EXPOSITIONS", "<br><strong>Expositions</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("BIBLIOGRAPHIE", "<br><strong>Literature</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("Condition Report", "<br><strong>Condition Report</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("Notes:", "<br><strong>Notes:</strong><br>")
            detailData['artwork_description'] = "<strong><br>Description<br></strong>" + detailData['artwork_description']
            detailData['artwork_description'] = detailData['artwork_description'].replace('"', "'")
        auctiondateSpanTags = soup.find_all("span", {'class' : 'sale_datetime'})
        if auctiondateSpanTags.__len__() > 0:
            auctiondateSpan = auctiondateSpanTags[0]
            auctiondate = auctiondateSpan.renderContents().decode('utf-8')
            auctiondate = beginspacePattern.sub("", auctiondate)
            auctiondateparts = auctiondate.split(" ") # 16 juin 2021 19:00 CEST
            if auctiondateparts.__len__() > 2:
                auctiondate = auctiondateparts[1] + " " + auctiondateparts[0] + " " + auctiondateparts[2]
                if not self.auctiondate:
                    self.auctiondate = auctiondate
                detailData['auction_start_date'] = self.__class__.formatDate(auctiondate)
            elif auctiondateparts.__len__() > 1:
                auctiondate = auctiondateparts[1] + " " + auctiondateparts[0] + " 2022"
                if not self.auctiondate:
                    self.auctiondate = auctiondate
                detailData['auction_start_date'] = self.__class__.formatDate(auctiondate)
        detailData['auction_house_name'] = "SWANN"
        return detailData


    def getImage(self, imageUrl, imagepath, downloadimages):
        imageUrlParts = imageUrl.split("/")
        imagefilename = imageUrlParts[-2] + "_" + imageUrlParts[-1]
        imagedir = imageUrlParts[-2]
        backslashPattern = re.compile(r"\\")
        if downloadimages == "1":
            pageRequest = urllib.request.Request(imageUrl, headers=self.httpHeaders)
            pageResponse = None
            try:
                pageResponse = self.opener.open(pageRequest)
            except:
                print ("Error: %s"%sys.exc_info()[1].__str__())
            try:
                imageContent = pageResponse.read()
                imagefilename = backslashPattern.sub("_", imagefilename)
                ifp = open(imagepath + os.path.sep + imagefilename, "wb")
                ifp.write(imageContent)
                ifp.close()
                return imagefilename
            except:
                print("Error: %s"%sys.exc_info()[1].__str__())
        return imagefilename


    def getInfoFromLotsData(self, htmlList, imagepath, downloadimages):
        baseUrl = "https://catalogue.swanngalleries.com"
        info = []
        endSpacePattern = re.compile("\s+$", re.DOTALL)
        beginspacePattern = re.compile("^\s+")
        emptyspacePattern = re.compile("^\s*$")
        for htmlli in htmlList:
            data = {}
            data['auction_num'] = self.saleno
            detailUrl = ""
            lotno = ""
            data['price_estimate_min'] = ""
            data['price_estimate_max'] = ""
            data['artist_name'] = ""
            data['artwork_name'] = ""
            data['lot_num'] = ""
            data['lot_origin_url'] = ""
            htmlContent = htmlli.renderContents().decode('utf-8')
            s = BeautifulSoup(htmlContent, features="html.parser")
            anchortags = s.find_all("a")
            if anchortags.__len__() > 0:
                anchortag = anchortags[0]
                detailUrl = self.baseUrl + anchortag['href']
                data['lot_origin_url'] = detailUrl
            artisttitledivtags = s.find_all("div", {'class' : 'product-listing_description'})
            if artisttitledivtags.__len__() > 0:
                artisttitlediv = artisttitledivtags[0]
                artisttitlecontent = artisttitlediv.renderContents().decode('utf-8')
                artisttitlecontent = artisttitlecontent.replace("\n", "").replace("\r", "")
                artisttitlecontent = beginspacePattern.sub("", artisttitlecontent)
                artisttitlePattern1 = re.compile("([A-Z\s\.\-ÉÈ]+)\s+\((\d{4})\s*\-\s*(\d{0,4})\)\s+(.*)$", re.DOTALL)
                artisttitlePattern1a = re.compile("([A-Z\s\.\-ÉÈ]+)\s+\((\d{4})\s*\-\s*(\d{0,4}),\s*[\w\/]+\)\s+(.*)$", re.DOTALL)
                artisttitlePattern2 = re.compile("([A-Z\s\.\-ÉÈ]+)\s+([\w\s\,]+)", re.DOTALL)
                artisttitlePattern3 = re.compile("([A-Z\s\.\-ÉÈ]+)\s+\((\d{4})\s*\-\s*(\d{0,4}),\s+([\w\s\/\-]+)\)\s+(.*)\.?")
                artisttitlePattern4 = re.compile("([A-Z\s\.\-ÉÈ]+)\s+\(B\.\s*(\d{4}),\s+([\w\s\/\-]+)\)[\s,]*(.*)\.?")
                atps1 = re.search(artisttitlePattern1, artisttitlecontent)
                atps1a = re.search(artisttitlePattern1a, artisttitlecontent)
                atps2 = re.search(artisttitlePattern2, artisttitlecontent)
                atps3 = re.search(artisttitlePattern3, artisttitlecontent)
                atps4 = re.search(artisttitlePattern4, artisttitlecontent)
                #print(artisttitlecontent)
                if atps1:
                    data['artist_name'] = atps1.groups()[0]
                    data['artist_name'] = beginspacePattern.sub("", data['artist_name'])
                    data['artwork_name'] = atps1.groups()[3]
                    data['artist_birth'] = atps1.groups()[1]
                    data['artist_death'] = atps1.groups()[2]
                if atps4 and ('artist_name' not in data.keys() or re.search(emptyspacePattern, data['artist_name'])):
                    data['artist_name'] = atps4.groups()[0]
                    data['artist_name'] = beginspacePattern.sub("", data['artist_name'])
                    data['artwork_name'] = atps4.groups()[3]
                    data['artist_nationality'] = atps4.groups()[2]
                    data['artist_birth'] = atps4.groups()[1]
                if atps1a and ('artist_name' not in data.keys() or re.search(emptyspacePattern, data['artist_name'])):
                    data['artist_name'] = atps1a.groups()[0]
                    data['artist_name'] = beginspacePattern.sub("", data['artist_name'])
                    data['artwork_name'] = atps1a.groups()[3]
                    data['artist_birth'] = atps1a.groups()[1]
                    data['artist_death'] = atps1a.groups()[2]
                if atps2 and ('artist_name' not in data.keys() or re.search(emptyspacePattern, data['artist_name'])):
                    data['artist_name'] = atps2.groups()[0]
                    data['artwork_name'] = atps2.groups()[1]
                if atps3 and ('artist_name' not in data.keys() or re.search(emptyspacePattern, data['artist_name'])):
                    data['artist_name'] = atps3.groups()[0]
                    data['artist_name'] = beginspacePattern.sub("", data['artist_name'])
                    data['artwork_name'] = atps3.groups()[4]
                    data['artist_nationality'] = atps3.groups()[3]
                    data['artist_birth'] = atps3.groups()[1]
                    data['artist_death'] = atps3.groups()[2]
                #print(data['artist_name'])
            lotnodivtags = s.find_all("div", {'class' : 'product-listing_title'})
            if lotnodivtags.__len__() > 0:
                lotnodiv = lotnodivtags[0]
                lotnocontent = lotnodiv.renderContents().decode('utf-8')
                lotnocontent = lotnocontent.replace("\n", "").replace("\r", "")
                lotnocontent = self.__class__.htmltagPattern.sub("", lotnocontent)
                lotnoPattern = re.compile("Lot\s+(\d+)\s*$", re.IGNORECASE|re.DOTALL)
                lnps = re.search(lotnoPattern, lotnocontent)
                if lnps:
                    lotno = lnps.groups()[0]
                    data['lot_num'] = lotno
            estimatedivtags = s.find_all("div", {'class' : 'product-listing_estimate'})
            if estimatedivtags.__len__() > 0:
                estimatediv = estimatedivtags[0].renderContents().decode('utf-8')
                estimatediv = self.__class__.htmltagPattern.sub("", estimatediv)
                estimatediv = estimatediv.replace("\n", "").replace("\r", "")
                estimatePattern = re.compile("Estimate\s+\$\s+([\d\,\.]+)\s+\-\s+\$\s+([\d\,\.]+)", re.IGNORECASE|re.DOTALL)
                eps = re.search(estimatePattern, estimatediv)
                if eps:
                    epsg = eps.groups()
                    data['price_estimate_min'] = epsg[0]
                    data['price_estimate_max'] = epsg[1]
            if estimatedivtags.__len__() > 1:
                soldpricediv = estimatedivtags[1].renderContents().decode('utf-8')
                soldpricediv = self.__class__.htmltagPattern.sub("", soldpricediv)
                soldpricediv = soldpricediv.replace("\n", "").replace("\r", "")
                soldpricePattern = re.compile("Price\s+Realized\s+\$\s+([\d\,\.]+)", re.IGNORECASE|re.DOTALL)
                spps = re.search(soldpricePattern, soldpricediv)
                if spps:
                    sppsg = spps.groups()
                    soldprice = sppsg[0]
                    data['price_sold'] = soldprice
            #print(data['lot_num'] + " ## " + data['artist_name'] + " ## " + data['artwork_name'] + " ## " + data['price_estimate_min'])
            print("Getting '%s'..."%data['lot_origin_url'])
            if detailUrl == "":
                break
            detailsPageContent = self.getDetailsPage(detailUrl)
            detailData = self.parseDetailPage(detailsPageContent, lotno, imagepath, data['artist_name'], data['artwork_name'], downloadimages)
            for k in detailData.keys():
                data[k] = detailData[k]
            withdrawnPattern = re.compile("withdrawn", re.IGNORECASE|re.DOTALL)
            data['price_kind'] = "unknown"
            if ('price_sold' in data.keys() and re.search(withdrawnPattern, data['price_sold'])) or ('price_estimate_max' in data.keys() and re.search(withdrawnPattern, data['price_estimate_max'])):
                data['price_kind'] = "withdrawn"
            elif 'price_sold' in data.keys() and data['price_sold'] != "":
                data['price_kind'] = "price realized"
            elif 'price_estimate_max' in data.keys() and data['price_estimate_max'] != "":
                data['price_kind'] = "estimate"
            else:
                pass
            if 'price_sold' not in data.keys():
                data['price_sold'] = ""
            data['auction_name'] = self.auctiontitle
            data['auction_location'] = "New York"
            info.append(data)
        return info

"""
[
'auction_house_name', 'auction_location', 'auction_num', 'auction_start_date', 'auction_end_date', 'auction_name', 'lot_num', 'sublot_num', 'price_kind', 'price_estimate_min', 'price_estimate_max', 'price_sold', 'artist_name', 'artist_birth', 'artist_death', 'artist_nationality', 'artwork_name', 'artwork_year_identifier', 'artwork_start_year', 'artwork_end_year', 'artwork_materials', 'artwork_category', 'artwork_markings', 'artwork_edition', 'artwork_description', 'artwork_measurements_height', 'artwork_measurements_width', 'artwork_measurements_depth', 'artwork_size_notes', 'auction_measureunit', 'artwork_condition_in', 'artwork_provenance', 'artwork_exhibited', 'artwork_literature', 'artwork_images1', 'artwork_images2', 'artwork_images3', 'artwork_images4', 'artwork_images5', 'image1_name', 'image2_name', 'image3_name', 'image4_name', 'image5_name', 'lot_origin_url'
]
 """
 
# That's it.... 

def updatestatus(auctionno, auctionurl):
    auctionurl = auctionurl.replace("%3A", ":")
    auctionurl = auctionurl.replace("%2F", "/")
    pageurl = "http://216.137.189.57:8080/scrapers/finish/?scrapername=Swann&auctionnumber=%s&auctionurl=%s&scrapertype=2"%(auctionno, urllib.parse.quote(auctionurl))
    pageResponse = None
    try:
        pageResponse = urllib.request.urlopen(pageurl)
    except:
        print ("Error: %s"%sys.exc_info()[1].__str__())  




if __name__ == "__main__":
    if sys.argv.__len__() < 5:
        print("Insufficient parameters")
        sys.exit()
    auctionurl = sys.argv[1]
    auctionnumber = sys.argv[2]
    csvpath = sys.argv[3]
    imagepath = sys.argv[4]
    downloadimages = 0
    convertfractions = 0
    if sys.argv.__len__() > 5:
        downloadimages = sys.argv[5]
    if sys.argv.__len__() > 6:
        convertfractions = sys.argv[6]
    auctionurl = auctionurl + "&pg=10"
    swann = SwannBot(auctionurl, auctionnumber)
    fp = open(csvpath, "w")
    fieldnames = ['auction_house_name', 'auction_location', 'auction_num', 'auction_start_date', 'auction_end_date', 'auction_name', 'lot_num', 'sublot_num', 'price_kind', 'price_estimate_min', 'price_estimate_max', 'price_sold', 'artist_name', 'artist_birth', 'artist_death', 'artist_nationality', 'artwork_name', 'artwork_year_identifier', 'artwork_start_year', 'artwork_end_year', 'artwork_materials', 'artwork_category', 'artwork_markings', 'artwork_edition', 'artwork_description', 'artwork_measurements_height', 'artwork_measurements_width', 'artwork_measurements_depth', 'artwork_size_notes', 'auction_measureunit', 'artwork_condition_in', 'artwork_provenance', 'artwork_exhibited', 'artwork_literature', 'artwork_images1', 'artwork_images2', 'artwork_images3', 'artwork_images4', 'artwork_images5', 'image1_name', 'image2_name', 'image3_name', 'image4_name', 'image5_name', 'lot_origin_url']
    fieldsstr = ",".join(fieldnames)
    fp.write(fieldsstr + "\n")
    pagectr = 1
    soup = BeautifulSoup(swann.currentPageContent, features="html.parser")
    while True:
        lotsdata = swann.getLotsFromPage()
        info = swann.getInfoFromLotsData(lotsdata, imagepath, downloadimages)
        lotctr = 0 
        for d in info:
            lotctr += 1
            for f in fieldnames:
                if f in d and d[f] is not None:
                    fp.write('"' + str(d[f]) + '",')
                else:
                    fp.write('"",')
            fp.write("\n")
        pagectr += 1
        nextpageanchors = soup.find_all("a", {'id' : 'pagination-nav-%s'%str(pagectr)})
        if nextpageanchors.__len__() > 0:
            nextpageUrl = swann.baseUrl[:-1] + nextpageanchors[0]['href']
            swann.pageRequest = urllib.request.Request(nextpageUrl, headers=swann.httpHeaders)
            try:
                swann.pageResponse = swann.opener.open(swann.pageRequest)
            except:
                print("Couldn't find the page %s"%str(pagectr))
                break
            swann.currentPageContent = swann.__class__._decodeGzippedContent(swann.getPageContent())
        else:
            break
    fp.close()
    updatestatus(auctionnumber, auctionurl)

# Example: python swann.py "https://catalogue.swanngalleries.com/auction-catalogs/CONTEMPORARY-ART?saleno=2604&filter_value=%20&view=&viewby=Lot_asc" 2604 /Users/saiswarupsahu/freelanceprojectchetan/swann_2604.csv /Users/saiswarupsahu/freelanceprojectchetan/1-5TNCV9 0 0
# supmit


