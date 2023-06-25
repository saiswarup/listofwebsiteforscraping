# -*- coding: utf-8 -*-
"""
Christies scraper version 2.0 - Added multiprocessing for downloading additional images.

"""
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
from multiprocessing import Process, Pool, Queue
from cryptography.fernet import Fernet
import csv
import unidecode

partialUrlPattern = re.compile("^/\w+")
beginspacePattern = re.compile("\w{}")

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


def handleimagedownloads(obj, mappedurllist, altimageurl, imagepath, lotno, baseImagePath, downloadimages, suffixval):
    #print("Downloading image from '%s'"%altimageurl)
    imagefilename = obj.getImage(altimageurl, imagepath, downloadimages)
    mappedUrl = obj.mapImageUrl(imagefilename, lotno, baseImagePath, downloadimages, suffix=suffixval)
    mappedurllist.put(mappedUrl)

def ispartialURL(url):
    urlPattern = re.compile("^https?:\/\/", re.IGNORECASE)
    if re.search(urlPattern, url):
        return False
    return True


class ChristiesBot(object):

    htmltagPattern = re.compile("\<\/?[^\<\>]*\/?\>", re.DOTALL)
    pathEndingWithSlashPattern = re.compile(r"\/$")
    onlineChristiesPattern = re.compile("onlineonly\.christies\.com", re.IGNORECASE)
    htmlEntitiesDict = {'&nbsp;' : ' ', '&#160;' : ' ', '&amp;' : '&', '&#38;' : '&', '&lt;' : '<', '&#60;' : '<', '&gt;' : '>', '&#62;' : '>', '&apos;' : '\'', '&#39;' : '\'', '&quot;' : '"', '&#34;' : '"'}

    """
    Initialization would include fetching the login page of the email service.
    """
    def __init__(self, auctionurl, saleno=""):
        # Create the opener object(s). Might need more than one type if we need to get pages with unwanted redirects.
        self.opener = urllib.request.build_opener(urllib.request.HTTPHandler(), urllib.request.HTTPSHandler()) # This is my normal opener....
        self.no_redirect_opener = urllib.request.build_opener(urllib.request.HTTPHandler(), urllib.request.HTTPSHandler(), NoRedirectHandler()) # ... and this one won't handle redirects.
        #self.debug_opener = urllib.request.build_opener(urllib.request.HTTPHandler(debuglevel=1))
        # Initialize some object properties.
        self.sessionCookies = ""
        self.httpHeaders = { 'User-Agent' : r'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36',  'Accept' : 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8', 'Accept-Language' : 'en-us,en;q=0.5', 'Accept-Encoding' : 'gzip,deflate', 'Accept-Charset' : 'ISO-8859-1,utf-8;q=0.7,*;q=0.7', 'Keep-Alive' : '115', 'Connection' : 'keep-alive', }
        self.online = False
        onlinePattern = re.compile("onlineonly\.christies\.com")
        ons = re.search(onlinePattern, auctionurl)
        if ons:
            self.online = True
        self.httpHeaders['cache-control'] = "max-age=0"
        self.httpHeaders['upgrade-insecure-requests'] = "1"
        self.httpHeaders['sec-fetch-dest'] = "document"
        self.httpHeaders['sec-fetch-mode'] = "navigate"
        self.httpHeaders['sec-fetch-site'] = "none"
        self.httpHeaders['sec-fetch-user'] = "?1"
        self.homeDir = os.getcwd()
        #self.requestUrl = self.__class__.startUrl
        self.auctionurl = auctionurl
        self.requestUrl = auctionurl +"?filters=&page=10&searchphrase=&sortby=LotNumber"
        parsedUrl = urlparse(self.requestUrl)
        self.baseUrl = parsedUrl.scheme + "://" + parsedUrl.netloc + "/"
        #print(self.requestUrl)
        self.pageRequest = urllib.request.Request(self.requestUrl, headers=self.httpHeaders)
        self.pageResponse = None
        self.requestMethod = "GET"
        self.postData = {}
        try:
            self.pageResponse = self.opener.open(self.pageRequest)
            headers = self.pageResponse.getheaders()
            #print(dict(headers).keys())
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
        self.data = {'auction_house_name' : '', 'auction_location' : '', 'auction_num' : '', 'auction_start_date' : '', 'auction_end_date' : '', 'auction_name' : '', 'lot_num' : '', 'sublot_num' : '', 'price_kind' : '', 'price_estimate_min' : '', 'price_estimate_max' : '', 'price_sold' : '', 'artist_name' : '', 'artist_birth' : '', 'artist_death' : '', 'artist_nationality' : '', 'artwork_name' : '', 'artwork_year_identifier' : '', 'artwork_start_year' : '', 'artwork_end_year' : '', 'artwork_materials' : '', 'artwork_category' : '', 'artwork_markings' : '', 'artwork_edition' : '', 'artwork_description' : '', 'artwork_measurements_height' : '', 'artwork_measurements_width' : '', 'artwork_measurements_depth' : '', 'artwork_size_notes' : '', 'auction_measureunit' : '', 'artwork_condition_in' : '', 'artwork_provenance' : '', 'artwork_exhibited' : '', 'artwork_literature' : '', 'artwork_images1' : '', 'artwork_images2' : '', 'artwork_images3' : '', 'artwork_images4' : '', 'artwork_images5' : '', 'image1_name' : '', 'image2_name' : '', 'image3_name' : '', 'image4_name' : '', 'image5_name' : '', 'lot_origin_url' : ''}
        self.saleno = saleno
        self.auctiontitle = ""
        self.auctiondate = ""
        locationdict = {'nyr' : 'NewYork', 'cks' : 'London', 'ams' : 'Amsterdam', 'par' : 'Paris'}
        locationPattern = re.compile("\-([a-z]{3})\/", re.IGNORECASE)
        lps = re.search(locationPattern, auctionurl)
        self.auctionlocation = ""
        if lps:
            loccode = lps.groups()[0]
            try:
                self.auctionlocation = locationdict[loccode]
            except:
                self.auctionlocation = "Online"


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
            content = self.pageResponse.read()
            return(content)
        except:
            return bytes("".encode())

    def formatDate(cls, datestr):
        mondict = {'January' : '01', 'February' : '02', 'March' : '03', 'April' : '04', 'May' : '05', 'June' : '06', 'July' : '07', 'August' : '08', 'September' : '09', 'October' : '10', 'November' : '11', 'December' : '12' }
        mondict3 = {'jan.' : '01', 'fév.' : '02', 'mar.' : '03', 'avr.' : '04', 'mai.' : '05', 'jui.' : '06', 'jul.' : '07', 'aoû.' : '08', 'sep.' : '09', 'oct.' : '10', 'nov.' : '11', 'déc.' : '12' }
        datestrcomponents = datestr.split(" ")
        dd = datestrcomponents[0]
        mm = '01'
        if datestrcomponents[1] in mondict.keys():
            mm = mondict[datestrcomponents[1]]
        else:
            mm = mondict3[datestrcomponents[1]]
        yyyy = datestrcomponents[2]
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
        baseUrl = "https://www.christies.com"
        pageContent = self.currentPageContent
        soup = BeautifulSoup(self.currentPageContent, features="html.parser")
        auctiontitleh1tags = soup.find_all("h1", {'class' : 'chr-auction-header__auction-title'})
        if auctiontitleh1tags.__len__() > 0:
            self.auctiontitle = auctiontitleh1tags[0].renderContents().decode('utf-8')
            self.auctiontitle = self.__class__.htmltagPattern.sub("", self.auctiontitle)
        lotnoPattern = re.compile('"lots":(\[\{.*\}\])\,;"', re.DOTALL)
        onlineonlysearch = re.search(self.__class__.onlineChristiesPattern, self.baseUrl)
        if onlineonlysearch:
            lotnoPattern = re.compile('"lots":(\[\{.*\}\])\,"ui_state"', re.IGNORECASE|re.DOTALL)
        lotjsonsearch = re.search(lotnoPattern, pageContent)
       
        lotjson = {}
        lotsdata = []
        if lotjsonsearch:
            ljsg = lotjsonsearch.groups()[0]
            lotjson = json.loads(ljsg)
            
            if type(lotjson) == dict and 'data' in lotjson.keys():
                self.saleno = lotjson['data']['lot_search_api_endpoint']['parameters']['salenumber']
                if 'lots' in lotjson['data'].keys():
                    lotsdata = lotjson['data']['lots']
                    return lotsdata
            elif onlineonlysearch:
                lotsdata = lotjson
                return lotsdata
            print(lotsdata)
        return lotsdata


    def getDetailsPage(self, detailUrl):
        self.requestUrl = detailUrl
        self.pageRequest = urllib.request.Request(self.requestUrl, headers=self.httpHeaders)
        self.pageResponse = None
        self.postData = {}
        try:
            self.pageResponse = self.opener.open(self.pageRequest)
            headers = self.pageResponse.getheaders()
        except:
            print ("Couldn't fetch page due to limited connectivity. Please check your internet connection and try again. %s"%sys.exc_info()[1].__str__())
        self.currentPageContent = self.__class__._decodeGzippedContent(self.getPageContent())
        return self.currentPageContent


    def renameImagefile(self, basepath, imagefilename, mappedImagename):
        oldfilename = basepath + "/" + imagefilename
        newfilename = basepath + "/" + mappedImagename
        os.rename(oldfilename, newfilename)


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


    def parseDetailPage(self, detailsPage, lotno, imagepath, artistname, artworkname, downloadimages):
        baseUrl = "https://www.christies.com"
        detailData = {}
        beginSpacePattern = re.compile("^\s+", re.DOTALL)
        newlinesPattern = re.compile("\\r?\\n|\\r", re.DOTALL)
        imagesPattern = re.compile('\)\.images\s*=\s*(\[\{"[^\]]+\}\]);', re.DOTALL|re.IGNORECASE)
        soup = BeautifulSoup(detailsPage, features="html.parser")
        addlimagesdivtags = soup.find_all("div", {'class' : 'chr-lot-header__thumbnails'})
        jpgPattern = re.compile("\.jpg", re.IGNORECASE)
        additionalimages = []
        if addlimagesdivtags.__len__() > 0:
            addlimagesdiv = addlimagesdivtags[0]
            imgtags = addlimagesdiv.findChildren("img", recursive=True)
            for imgtag in imgtags:
                altsrcset = imgtag['data-srcset']
                altsrcsetparts = altsrcset.split(" ")
                for i in range(altsrcsetparts.__len__() - 1, 0, -1):
                    if re.search(jpgPattern, altsrcsetparts[i]):
                        additionalimages.append(altsrcsetparts[i])
                #additionalimages.append(imgtag['src'])
        #print(additionalimages)
        if re.search(self.__class__.onlineChristiesPattern, self.baseUrl):
            additionalimages = []
            ams = re.search(imagesPattern, detailsPage)
            if ams:
                amsg = ams.groups()
                imageslist = json.loads(amsg[0])
                entryctr = 0
                for imgentry in imageslist:
                    if entryctr < 1:
                        entryctr += 1
                        continue
                    imgurl = imgentry['image_src']
                    additionalimages.append(imgurl)
                    entryctr += 1
        auctiontitle = self.auctiontitle.replace(" ", "_")
        processedAuctionTitle = auctiontitle.replace(" ", "_")
        imgctr = 2
        if additionalimages.__len__() > 0:
            altimage2 = additionalimages[0]
            altimage2parts = altimage2.split("/")
            altimageurl = "/".join(altimage2parts[:-2])
            processedArtistName = artistname.replace(" ", "_")
            processedArtistName = unidecode.unidecode(processedArtistName)
            processedArtworkName = artworkname.replace(" ", "_")
            processedArtworkName = unidecode.unidecode(processedArtworkName)
            sublot_number = ""
            #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + self.saleno + "__" + lotno + "__" + sublot_number
            newname1 = self.saleno + "__" + processedArtistName + "__" + lotno + "_b"
            #encryptedFilename = self.encryptFilename(newname1)
            encryptedFilename = newname1
            encryptedFilename = encryptedFilename.replace("b'", "").replace("'", "")
            detailData['image' + str(imgctr) + '_name'] = str(encryptedFilename) + ".jpg"
            detailData['artwork_images' + str(imgctr)] = altimage2
            """
            if downloadimages == "1":
                encryptedFilename = str(encryptedFilename) + "-b.jpg"
                self.renameImageFile(imagepath, imagename1, encryptedFilename)
            """
            imgctr += 1
        if additionalimages.__len__() > 1:
            altimage3 = additionalimages[1]
            altimage3parts = altimage3.split("/")
            altimageurl = "/".join(altimage3parts[:-2])
            detailData['image' + str(imgctr) + '_name'] = self.getImagenameFromUrl(altimage3)
            processedArtistName = artistname.replace(" ", "_")
            processedArtistName = unidecode.unidecode(processedArtistName)
            processedArtworkName = artworkname.replace(" ", "_")
            processedArtworkName = unidecode.unidecode(processedArtworkName)
            sublot_number = ""
            #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + self.saleno + "__" + lotno + "__" + sublot_number
            newname1 = self.saleno + "__" + processedArtistName + "__" + lotno + "_c"
            #encryptedFilename = self.encryptFilename(newname1)
            encryptedFilename = newname1
            encryptedFilename = encryptedFilename.replace("b'", "").replace("'", "")
            detailData['image' + str(imgctr) + '_name'] = str(encryptedFilename) + ".jpg"
            detailData['artwork_images' + str(imgctr)] = altimage3
            """
            if downloadimages == "1":
                encryptedFilename = str(encryptedFilename) + "-c.jpg"
                self.renameImageFile(imagepath, imagename1, encryptedFilename)
            """
            imgctr += 1
        if additionalimages.__len__() > 2:
            altimage4 = additionalimages[2]
            altimage4parts = altimage4.split("/")
            altimageurl = "/".join(altimage4parts[:-2])
            detailData['image' + str(imgctr) + '_name'] = self.getImagenameFromUrl(altimage4)
            processedArtistName = artistname.replace(" ", "_")
            processedArtistName = unidecode.unidecode(processedArtistName)
            processedArtworkName = artworkname.replace(" ", "_")
            processedArtworkName = unidecode.unidecode(processedArtworkName)
            sublot_number = ""
            #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + self.saleno + "__" + lotno + "__" + sublot_number
            newname1 = self.saleno + "__" + processedArtistName + "__" + lotno + "_d"
            #encryptedFilename = self.encryptFilename(newname1)
            encryptedFilename = newname1
            encryptedFilename = encryptedFilename.replace("b'", "").replace("'", "")
            detailData['image' + str(imgctr) + '_name'] = str(encryptedFilename) + ".jpg"
            detailData['artwork_images' + str(imgctr)] = altimage4
            """
            if downloadimages == "1":
                encryptedFilename = str(encryptedFilename) + "-d.jpg"
                self.renameImageFile(imagepath, imagename1, encryptedFilename)
            """
            imgctr += 1
        if additionalimages.__len__() > 3:
            altimage5 = additionalimages[3]
            altimage5parts = altimage5.split("/")
            altimageurl = "/".join(altimage5parts[:-2])
            detailData['image' + str(imgctr) + '_name'] = self.getImagenameFromUrl(altimage5)
            processedArtistName = artistname.replace(" ", "_")
            processedArtistName = unidecode.unidecode(processedArtistName)
            processedArtworkName = artworkname.replace(" ", "_")
            processedArtworkName = unidecode.unidecode(processedArtworkName)
            sublot_number = ""
            #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + self.saleno + "__" + lotno + "__" + sublot_number
            newname1 = self.saleno + "__" + processedArtistName + "__" + lotno + "_e"
            #encryptedFilename = self.encryptFilename(newname1)
            encryptedFilename = newname1
            encryptedFilename = encryptedFilename.replace("b'", "").replace("'", "")
            detailData['image' + str(imgctr) + '_name'] = str(encryptedFilename) + ".jpg"
            detailData['artwork_images' + str(imgctr)] = altimage5
            imgctr += 1
        infotags = soup.find_all("chr-accordion")
        provenancePattern = re.compile("provenance", re.DOTALL|re.IGNORECASE)
        literaturePattern = re.compile("literature", re.DOTALL|re.IGNORECASE)
        exhibitionPattern = re.compile("exhibited", re.DOTALL|re.IGNORECASE)
        sizePattern = re.compile("([\d\.]+\s*x?\s*[\d\.]*\s*x?\s*[\d\.]*\s*cm\.?)\s*", re.DOTALL|re.IGNORECASE)
        mediumPattern = re.compile("\s+on\s+", re.DOTALL)
        mediumPattern2 = re.compile("(albumen)|(\s+gold)|(silver)|(brass)|(bronze)|(wood)|(porcelain)|(stone)|(marble)|(metal)|(steel)|(iron)|(glass)|(plexiglas)|(chromogenic)|(paper)|(canvas)|(masonite)|(newsprint)|(silkscreen)|(parchment)|(linen)|(inkjet)|(ink\s+jet)|(pigment)|(\stin\s)|(photogravure)|(^oil\s+)|(oil\s+)|(\s+panel\s+)|(terracotta)|(ivory)|(\s+oak\s+)|(^oak\s+)|(\s+oak$)|(alabaster)|(chalk)|(\s+ink\s+)|(ceramic)|(acrylic)|(aluminium)|(aquatint)|(linoleum)|(etching)|(collotype)|(lithograph)|(drypoint)|(arches\s+wove)|(pochoir)|(screenprint)|(digital\s+print)|(print\s+in\s+colou?rs)", re.DOTALL|re.IGNORECASE)
        signedPattern = re.compile("(signed[^,\(]+)\(?.*?,", re.IGNORECASE|re.DOTALL)
        signedPattern2 = re.compile("(signé[^;]+)\;?", re.IGNORECASE|re.DOTALL) # Signed pattern for foreign language.
        editionPattern = re.compile(",([^,]+édition\s.*)\.", re.IGNORECASE|re.DOTALL) # Edition pattern for foreign language.
        decimalnumberPattern = re.compile("([\d\.,\/\s]+)")
        measureunitPattern = re.compile("\s([a-zA-Z]{2,})")
        for infotag in infotags:
            infocontent = infotag.renderContents().decode('utf-8')
            provenanceitem = infotag.find("chr-accordion-item", {'accordion-id' : '1'})
            literatureitem = infotag.find("chr-accordion-item", {'accordion-id' : '2'})
            exhibitionitem = infotag.find("chr-accordion-item", {'accordion-id' : '3'})
            if re.search(self.__class__.onlineChristiesPattern, self.baseUrl):
                if not re.search(provenancePattern, infocontent) and not re.search(literaturePattern, infocontent) and not re.search(exhibitionPattern, infocontent):
                    infocontentparts = re.split("<br\s*\/?>", infocontent)
                    for infopart in infocontentparts:
                        infopart = infopart.replace('"', "'")
                        spc = re.search(sizePattern, infopart)
                        if not 'artwork_measurements_height' in detailData.keys() and spc:
                            size = spc.groups()[0]
                            mups = re.search(measureunitPattern, size)
                            if mups:
                                detailData['auction_measureunit'] = mups.groups()[0]
                            sizeparts = size.split("x")
                            detailData['artwork_size_notes'] = size
                            dnpsh = re.search(decimalnumberPattern, sizeparts[0])
                            if dnpsh:
                                detailData['artwork_measurements_height'] = dnpsh.groups()[0]
                            else:
                                detailData['artwork_measurements_height'] = sizeparts[0]
                            if sizeparts.__len__() > 1:
                                dnpsw = re.search(decimalnumberPattern, sizeparts[1])
                                if dnpsw:
                                    detailData['artwork_measurements_width'] = dnpsw.groups()[0]
                                else:
                                    detailData['artwork_measurements_width'] = sizeparts[1]
                            if sizeparts.__len__() > 2:
                                dnpsd = re.search(decimalnumberPattern, sizeparts[2])
                                if dnpsd:
                                    detailData['artwork_measurements_depth'] = dnpsd.groups()[0]
                                else:
                                    detailData['artwork_measurements_depth'] = sizeparts[2]
                        mps = re.search(mediumPattern, infopart)
                        if not 'artwork_materials' in detailData.keys() and mps:
                            detailData['artwork_materials'] = infopart
                            detailData['artwork_materials'] = detailData['artwork_materials'].replace(";", " ")
                            detailData['artwork_materials'] = detailData['artwork_materials'].replace('"', "'")
                        mps2 = re.search(mediumPattern2, infopart)
                        if not 'artwork_materials' in detailData.keys() and mps2:
                            detailData['artwork_materials'] = infopart
                            detailData['artwork_materials'] = detailData['artwork_materials'].replace(";", " ")
                            detailData['artwork_materials'] = detailData['artwork_materials'].replace('"', "'")
                        if 'artwork_materials' in detailData.keys():
                            exclusionPattern = re.compile("\s(stamp)|(sign)|(annotate)|(publish)|(printed)|(number)", re.IGNORECASE|re.DOTALL)
                            mediumparts =detailData['artwork_materials'].split(",")
                            mediumlist = []
                            for expart in mediumparts:
                                if re.search(exclusionPattern, expart):
                                    continue
                                else:
                                    mediumlist.append(expart)
                            detailData['artwork_materials'] = ",".join(mediumlist)
                        sps = re.search(signedPattern, infopart)
                        if not 'artwork_markings' in detailData.keys() and sps:
                            detailData['artwork_markings'] = infopart
                            detailData['artwork_markings'] = detailData['artwork_markings'].replace('"', "'")
                            inclusionPattern = re.compile("\ssigned", re.IGNORECASE|re.DOTALL)
                            signparts =detailData['artwork_markings'].split(",")
                            signlist = []
                            for signpart in signparts:
                                if not re.search(inclusionPattern, signpart):
                                    continue
                                else:
                                    signlist.append(signpart)
                            detailData['artwork_markings'] = ",".join(signlist)
                            detailData['artwork_markings'] = beginSpacePattern.sub("", detailData['artwork_markings'])
            infocontent = infocontent.replace("<br/>", ", ")
            infocontent = self.__class__.htmltagPattern.sub("", infocontent)
            infocontent = infocontent.replace('"', "'")
            infocontent = beginSpacePattern.sub("", infocontent)
            infocontent = newlinesPattern.sub("", infocontent)
            sps1 = re.search(signedPattern, infocontent)
            if 'artwork_markings' not in detailData.keys() and sps1:
                spsg1 = sps1.groups()
                detailData['artwork_markings'] = spsg1[0]
                detailData['artwork_markings'] = beginSpacePattern.sub("", detailData['artwork_markings'])
                #print(detailData['artwork_markings'] + " ======================")
            sps2 = re.search(signedPattern2, infocontent)
            if 'artwork_markings' not in detailData.keys() and sps2:
                spsg2 = sps2.groups()
                detailData['artwork_markings'] = spsg2[0]
                sigparts = detailData['artwork_markings'].split("image")
                if sigparts.__len__() > 0:
                    detailData['artwork_markings'] = sigparts[0]
                    endcommaPattern = re.compile(",\s*$")
                    endbracketPattern = re.compile("\(\s*$")
                    detailData['artwork_markings'] = endcommaPattern.sub("", detailData['artwork_markings'])
                    detailData['artwork_markings'] = endbracketPattern.sub("", detailData['artwork_markings'])
                    detailData['artwork_markings'] = beginSpacePattern.sub("", detailData['artwork_markings'])
            edps = re.search(editionPattern, infocontent)
            if 'artwork_edition' not in detailData.keys() and edps:
                edpsg = edps.groups()
                detailData['artwork_edition'] = edpsg[0]
            """
            pvs = re.search(provenancePattern, infocontent)
            if pvs:
                infocontent = provenancePattern.sub("", infocontent)
                detailData['artwork_provenance'] = infocontent
            lps = re.search(literaturePattern, infocontent)
            if lps:
                infocontent = literaturePattern.sub("", infocontent)
                detailData['artwork_literature'] = infocontent
            eps = re.search(exhibitionPattern, infocontent)
            if eps:
                infocontent = exhibitionPattern.sub("", infocontent)
                detailData['artwork_exhibited'] = infocontent
            """
            if provenanceitem is not None and 'artwork_provenance' not in detailData.keys():
                provenancecontents = provenanceitem.renderContents().decode('utf-8')
                provenancecontents = self.__class__.htmltagPattern.sub("", provenancecontents)
                provenancecontents = provenancecontents.replace("\n", "").replace("\r", "")
                provenancecontents = provenancePattern.sub("", provenancecontents)
                detailData['artwork_provenance'] = provenancecontents
                #print(detailData['artwork_provenance'])
            if literatureitem is not None and 'artwork_literature' not in detailData.keys():
                literaturecontents = literatureitem.renderContents().decode('utf-8')
                literaturecontents = self.__class__.htmltagPattern.sub("", literaturecontents)
                literaturecontents = literaturecontents.replace("\n", "").replace("\r", "")
                literaturecontents = literaturePattern.sub("", literaturecontents)
                detailData['artwork_literature'] = literaturecontents
            if exhibitionitem is not None and 'artwork_exhibited' not in detailData.keys():
                exhibitioncontents = exhibitionitem.renderContents().decode('utf-8')
                exhibitioncontents = self.__class__.htmltagPattern.sub("", exhibitioncontents)
                exhibitioncontents = exhibitioncontents.replace("\n", "").replace("\r", "")
                exhibitioncontents = exhibitionPattern.sub("", exhibitioncontents)
                detailData['artwork_exhibited'] = exhibitioncontents
        if str(self.saleno) == "19834":
            item5tags = soup.find_all("chr-accordion-item", {'accordion-id' : '5'})
            if item5tags.__len__() > 0:
                item5contents = item5tags[0].renderContents().decode('utf-8')
                item5contents = item5contents.replace("\n", "").replace("\r", "")
                item5contents = self.__class__.htmltagPattern.sub("", item5contents)
                item5contents = beginSpacePattern.sub("", item5contents)
                item5contents = item5contents.replace("Post Lot Text", "")
                detailData['artwork_materials'] = item5contents
        # clean up the medium information
        if 'artwork_materials' in detailData.keys():
            nonmediumPattern = re.compile("(titled)|(intialed)|(dated)|(blindstamp)", re.IGNORECASE)
            editionPattern2 = re.compile("edition", re.IGNORECASE)
            mediumparts = detailData['artwork_materials'].split(",")
            mediumlist = []
            for medium in mediumparts:
                nmps = re.search(nonmediumPattern, medium)
                eps2 = re.search(editionPattern2, medium)
                if eps2:
                    detailData['artwork_edition'] = medium
                    detailData['artwork_edition'] = detailData['artwork_edition'].replace("(", "").replace(")", "")
                    detailData['artwork_edition'] = beginSpacePattern.sub("", detailData['artwork_edition'])
                    continue
                if nmps:
                    continue
                mediumlist.append(medium)
            detailData['artwork_materials'] = ", ".join(mediumlist)
            commenttagPattern = re.compile("<!--[^>]+-->", re.DOTALL)
            detailData['artwork_materials'] = self.__class__.htmltagPattern.sub("", detailData['artwork_materials'])
            detailData['artwork_materials'] = commenttagPattern.sub("", detailData['artwork_materials'])
            detailData['artwork_materials'] = beginSpacePattern.sub("", detailData['artwork_materials'])
        descsectiontags = soup.find_all("section", {'class' : 'chr-lot-details'})
        if descsectiontags.__len__() > 0:
            desctext = descsectiontags[0].renderContents().decode('utf-8')
            desctext = self.__class__.htmltagPattern.sub("", desctext)
            desctext = desctext.replace("\n", "").replace("\r", "")
            detailData['artwork_description'] = desctext
            detailData['artwork_description'] = detailData['artwork_description'].replace('"', "'")
            detailData['artwork_description'] = detailData['artwork_description'].replace("Provenance", "<br><strong>Provenance</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("Literature", "<br><strong>Literature</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("Exhibited", "<br><strong>Exhibited</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("EXPOSITIONS", "<br><strong>Expositions</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("BIBLIOGRAPHIE", "<br><strong>Literature</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("Condition Report", "<br><strong>Condition Report</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("Special notice", "<br><strong>Notes:</strong><br>")
            detailData['artwork_description'] = "<strong><br>Description<br></strong>" + detailData['artwork_description']
        return detailData


    def getImage(self, imageUrl, imagepath, downloadimages):
        imageUrlParts = imageUrl.split("/")
        imagefilename = imageUrlParts[-2] + "_" + imageUrlParts[-1]
        imagedir = imageUrlParts[-2]
        if downloadimages == "1":
            pageRequest = urllib.request.Request(imageUrl, headers=self.httpHeaders)
            pageResponse = None
            try:
                pageResponse = self.opener.open(pageRequest)
            except:
                print ("Error: %s"%sys.exc_info()[1].__str__())
            try:
                imageContent = pageResponse.read()
                ifp = open(imagepath + os.path.sep + imagefilename, "wb")
                ifp.write(imageContent)
                ifp.close()
            except:
                print("Error: %s"%sys.exc_info()[1].__str__())
        #print("GOT IMAGE '%s'"%imagefilename)
        return imagefilename


    def getInfoFromLotsData(self, datalist, imagepath, downloadimages):
        baseUrl = "https://www.christies.com"
        info = []
        brPattern = re.compile("<br\s*\/?>", re.IGNORECASE)
        endSpacePattern = re.compile("\s+$", re.DOTALL)
        sizePattern0 = re.compile("(\d+\,\d+\s+x\s+\d+\,?\d*\s*x?\s*\d*\,?\d*\s*cm\.)", re.DOTALL|re.IGNORECASE)
        sizePattern = re.compile("\(([\d\.]+\s*x?\s*[\d\.]*\s*x?\s*[\d\.]*\s*cm\.?)\s*\)", re.DOTALL|re.IGNORECASE)
        sizePattern2 = re.compile("([\d\.]+\s*x?\s*[\d\.]*\s*x?\s*[\d\.]*\s*cm\.?)\s*", re.DOTALL|re.IGNORECASE)
        sizePattern3 = re.compile("([\d\.]+\s*x?\s*[\d\.]*\s*x?\s*[\d\.]*\s*mm\.?)\s*", re.DOTALL|re.IGNORECASE)
        sizePattern4 = re.compile("(in\.?\s+high)|(in\.?\s+wide)|(in\.?\s+deep)", re.DOTALL|re.IGNORECASE)
        signedPattern = re.compile("signed", re.IGNORECASE|re.DOTALL)
        mediumPattern = re.compile("\s+on\s+", re.DOTALL)
        mediumPattern2 = re.compile("(gold)|(silver)|(brass)|(bronze)|(\s+wood\s+)|(porcelain)|(marble)|(metal)|(steel)|(iron)|(glass)|(plexiglas)|(chromogenic)|(paper)|(canvas)|(pearls)|(jersey)|(crepe)|(\s+oil\s+)|(^oil\s+)|(\s+oil$)|(terracotta)|(graphite)|(pastel)|(gouache)|(watercolor)|(watercolour)|(acrylic)|(charcoal)|(ceramic)", re.DOTALL|re.IGNORECASE)
        nonenglishmediumPattern = re.compile("(huile)|(d'or)|(bronze)|(panneau)|(patine)|(papier)|(terre\s+cuite)|(En\s+plomb)|(marbre)|(pearls)|(jersey)|(crêpe)|(\s+robe\s+)|(graphite)|(pastel)|(gouache)|(aquarelle)|(acrylique)|(chromogénique)|(argentique)|(Cibachrome)|(lithographies)|(c\-print)|(inkjet)|(aluminium)|(dibond)", re.DOTALL|re.IGNORECASE)
        createdDatePattern = re.compile("in\s+(\d{4})", re.DOTALL)
        estimatePattern = re.compile("(\w{3})\s*([\d\,]+)\s*\-\s*\w{3}\s*([\d\,]*)", re.DOTALL)
        estimatePattern2 = re.compile("(\w{3})\s*([\d\,]+)\s*\-\s*([\d\,]*)", re.DOTALL)
        conceptionPattern = re.compile("conceived\s+in\s+(\d{4})", re.DOTALL|re.IGNORECASE)
        #printedPattern = re.compile("printed\s+in\s+(\d{4})", re.DOTALL|re.IGNORECASE)
        editionPattern = re.compile("\s+([\w\-]*)\s+from\s+an\s+edition\s+", re.DOTALL|re.IGNORECASE)
        birthdeathdatePattern = re.compile("(\d{4})\-?(\d{0,4})")
        decimalnumberPattern = re.compile("([\d\.,\/\s]+)")
        measureunitPattern = re.compile("\s([a-zA-Z]{2,})")
        nyrPattern = re.compile("nyr", re.IGNORECASE)
        yearPattern = re.compile("(\d{4})")
        matcatdict_en = {}
        matcatdict_fr = {}
        #with open("docs/fineart_materials.csv", newline='') as mapfile:
        with open("/Users/saiswarupsahu/freelanceprojectchetan/docs/fineart_materials.csv", newline='') as mapfile:
            mapreader = csv.reader(mapfile, delimiter=",", quotechar='"')
            for maprow in mapreader:
                matcatdict_en[maprow[1]] = maprow[3]
                matcatdict_fr[maprow[2]] = maprow[3]
        mapfile.close()
        for lotdata in datalist:
            data = {}
            data['lot_num'] = lotdata['lot_id_txt']
            lotno = data['lot_num']
            data['auction_house_name'] = "Christie's"
            #data['artist_name'] = "Anonymous"
            artistname = ""
            detailUrl = lotdata['url']
            artistnamedates = lotdata['title_primary_txt']
            artistnamedates = artistnamedates.replace("\n", "")
            artistdetailPattern = re.compile("([a-z\.\-\séáóùšíúñúüÉÈÎ\(\)']*)\s+\([\w\.\s]*(\d{4})\s*\-?\s*(\d{0,4})\)", re.DOTALL|re.IGNORECASE)
            aps = re.search(artistdetailPattern, artistnamedates)
            if aps:
                apsg = aps.groups()
                data['artist_name'] = apsg[0]
                data['artist_birth'] = apsg[1]
                data['artist_death'] = apsg[2]
            else:
                altPattern = re.compile("([\w&#;\.\-\s]*)\s+\([\w\.\s]*(\d{4})\s*\-?\s*(\d{0,4})\s+and\s+.*\)", re.DOTALL|re.IGNORECASE)
                altPattern3 = re.compile("([a-z\.\-\séáóùšíúñúüÉÈÎ\(\)']*)\s+\([\w\.\s]*(\d{4})\s*\-?\s*(\d{0,4})\s*\w+\)", re.DOTALL|re.IGNORECASE)
                altPattern4 = re.compile("([a-z\.\-\séáóùšíúñúüÉÈÎ\(\)']*)\s+\([\w\.\s]*(\d{4})\s*\-?[\wÈ\s]*(\d{4})\s*\)", re.DOTALL|re.IGNORECASE)
                aps2 = re.search(altPattern, artistnamedates)
                if aps2:
                    apsg2 = aps2.groups()
                    data['artist_name'] = apsg2[0]
                    data['artist_birth'] = apsg2[1]
                    data['artist_death'] = apsg2[2]
                aps3 = re.search(altPattern3, artistnamedates)
                if aps3:
                    apsg3 = aps3.groups()
                    data['artist_name'] = apsg3[0]
                    data['artist_birth'] = apsg3[1]
                    data['artist_death'] = apsg3[2]
                aps4 = re.search(altPattern4, artistnamedates)
                if aps4:
                    apsg4 = aps4.groups()
                    data['artist_name'] = apsg4[0]
                    data['artist_birth'] = apsg4[1]
                    data['artist_death'] = apsg4[2]
                if 'artist_name' not in data.keys() or data['artist_name'] == "": # This needs to be verified.
                    data['artist_name'] = artistnamedates
                if 'artist_name' in data.keys():
                    bddps = re.search(birthdeathdatePattern, data['artist_name'])
                    if bddps:
                        bddpsg = bddps.groups()
                        if 'artist_birth' not in data.keys() or data['artist_birth'] == "":
                            data['artist_birth'] = bddpsg[0]
                        if 'artist_death' not in data.keys() or data['artist_death'] == "":
                            data['artist_death'] = bddpsg[1]
                        disposablePattern = re.compile("\([^\)]+\)")
                        data['artist_name'] = disposablePattern.sub("", data['artist_name'])
            if 'artist_name' in data.keys():
                beginspacePattern = re.compile("^\s+")
                data['artist_name'] = beginspacePattern.sub("", data['artist_name'])
                artistname = data['artist_name']
            else:
                artistname = ""
            data['artwork_name'] = lotdata['title_secondary_txt']
            if 'title_tertiary_txt' in lotdata.keys():
                titleAnnex = lotdata['title_tertiary_txt']
                if titleAnnex:
                    data['artwork_name'] += ", " + titleAnnex
            data['artwork_name'] = data['artwork_name'].replace("\n", "")
            data['artwork_name'] = data['artwork_name'].replace('"', "'")
            auctionDate = lotdata['start_date']
            auctionDateParts = auctionDate.split("T")
            auctionDateComponents = auctionDateParts[0].split("-")
            #auctionDateStr = auctionDateComponents[1] + "/" + auctionDateComponents[2] + "/" + auctionDateComponents[0]
            mondict = {'01' : 'Jan', '02' : 'Feb', '03' : 'Mar', '04' : 'Apr', '05' : 'May', '06' : 'Jun', '07' : 'Jul', '08' : 'Aug', '09' : 'Sep', '10' : 'Oct', '11' : 'Nov', '12' : 'Dec'}
            auctionDateStr = auctionDateComponents[1] + "-" + mondict[auctionDateComponents[2]] + "-" + auctionDateComponents[0]
            data['auction_start_date'] = auctionDateStr
            lotdesc = lotdata['description_txt']
            lotdescParts = re.split(brPattern, lotdesc)
            fyps = re.search(yearPattern, lotdesc)
            if fyps and 'artwork_start_year' not in data.keys():
                data['artwork_start_year'] = fyps.groups()[0]
            for ldpart in lotdescParts:
                ldpart = ldpart.replace("\n", "")
                ldpart = ldpart.replace("\\", "")
                ldpart = ldpart.replace('"', "'")
                ldpart = self.__class__.htmltagPattern.sub("", ldpart)
                zps0 = re.search(sizePattern0, ldpart)
                if zps0 and ('artwork_measurements_height' not in data.keys() or data['artwork_measurements_height'] == ""):
                    zpsg0 = zps0.groups()
                    size = zpsg0[0]
                    size = size.replace(",", ".")
                    mups = re.search(measureunitPattern, size)
                    if mups:
                        data['auction_measureunit'] = mups.groups()[0]
                    data['artwork_size_notes'] = size
                    sizeparts = size.split("x")
                    dnpsh = re.search(decimalnumberPattern, sizeparts[0])
                    if dnpsh:
                        data['artwork_measurements_height'] = dnpsh.groups()[0]
                    else:
                        data['artwork_measurements_height'] = sizeparts[0]
                    if sizeparts.__len__() > 1:
                        dnpsw = re.search(decimalnumberPattern, sizeparts[1])
                        if dnpsw:
                            data['artwork_measurements_width'] = dnpsw.groups()[0]
                        else:
                            data['artwork_measurements_width'] = sizeparts[1]
                    if sizeparts.__len__() > 2:
                        dnpsd = re.search(decimalnumberPattern, sizeparts[2])
                        if dnpsd:
                            data['artwork_measurements_depth'] = dnpsd.groups()[0]
                        else:
                            data['artwork_measurements_depth'] = sizeparts[2]
                zps = re.search(sizePattern, ldpart)
                if zps and ('artwork_measurements_height' not in data.keys() or data['artwork_measurements_height'] == ""):
                    zpsg = zps.groups()
                    size = zpsg[0]
                    mups = re.search(measureunitPattern, size)
                    if mups:
                        data['auction_measureunit'] = mups.groups()[0]
                    data['artwork_size_notes'] = size
                    sizeparts = size.split("x")
                    dnpsh = re.search(decimalnumberPattern, sizeparts[0])
                    if dnpsh:
                        data['artwork_measurements_height'] = dnpsh.groups()[0]
                    else:
                        data['artwork_measurements_height'] = sizeparts[0]
                    if sizeparts.__len__() > 1:
                        dnpsw = re.search(decimalnumberPattern, sizeparts[1])
                        if dnpsw:
                            data['artwork_measurements_width'] = dnpsw.groups()[0]
                        else:
                            data['artwork_measurements_width'] = sizeparts[1]
                    if sizeparts.__len__() > 2:
                        dnpsd = re.search(decimalnumberPattern, sizeparts[2])
                        if dnpsd:
                            data['artwork_measurements_depth'] = dnpsd.groups()[0]
                        else:
                            data['artwork_measurements_depth'] = sizeparts[2]
                zps2 = re.search(sizePattern2, ldpart)
                if zps2 and ('artwork_measurements_height' not in data.keys() or data['artwork_measurements_height'] == ""):
                    zpsg2 = zps2.groups()
                    size = zpsg2[0]
                    mups = re.search(measureunitPattern, size)
                    if mups:
                        data['auction_measureunit'] = mups.groups()[0]
                    data['artwork_size_notes'] = size
                    sizeparts = size.split("x")
                    dnpsh = re.search(decimalnumberPattern, sizeparts[0])
                    if dnpsh:
                        data['artwork_measurements_height'] = dnpsh.groups()[0]
                    else:
                        data['artwork_measurements_height'] = sizeparts[0]
                    if sizeparts.__len__() > 1:
                        dnpsw = re.search(decimalnumberPattern, sizeparts[1])
                        if dnpsw:
                            data['artwork_measurements_width'] = dnpsw.groups()[0]
                        else:
                            data['artwork_measurements_width'] = sizeparts[1]
                    if sizeparts.__len__() > 2:
                        dnpsd = re.search(decimalnumberPattern, sizeparts[2])
                        if dnpsd:
                            data['artwork_measurements_depth'] = dnpsd.groups()[0]
                        else:
                            data['artwork_measurements_depth'] = sizeparts[2]
                zps3 = re.search(sizePattern3, ldpart)
                if zps3 and ('artwork_measurements_height' not in data.keys() or data['artwork_measurements_height'] == ""):
                    zpsg3 = zps3.groups()
                    size = zpsg3[0]
                    mups = re.search(measureunitPattern, size)
                    if mups:
                        data['auction_measureunit'] = mups.groups()[0]
                    data['artwork_size_notes'] = size
                    sizeparts = size.split("x")
                    dnpsh = re.search(decimalnumberPattern, sizeparts[0])
                    if dnpsh:
                        data['artwork_measurements_height'] = dnpsh.groups()[0]
                    else:
                        data['artwork_measurements_height'] = sizeparts[0]
                    if sizeparts.__len__() > 1:
                        dnpsw = re.search(decimalnumberPattern, sizeparts[1])
                        if dnpsw:
                            data['artwork_measurements_width'] = dnpsw.groups()[0]
                        else:
                            data['artwork_measurements_width'] = sizeparts[1]
                    if sizeparts.__len__() > 2:
                        dnpsd = re.search(decimalnumberPattern, sizeparts[2])
                        if dnpsd:
                            data['artwork_measurements_depth'] = dnpsd.groups()[0]
                        else:
                            data['artwork_measurements_depth'] = sizeparts[2]
                zps4 = re.search(sizePattern4, ldpart)
                if zps4 and ('artwork_measurements_height' not in data.keys() or data['artwork_measurements_height'] == ""):
                    size = ldpart
                    mups = re.search(measureunitPattern, size)
                    if mups:
                        data['auction_measureunit'] = mups.groups()[0]
                    data['artwork_size_notes'] = size
                    sizeparts = size.split("x")
                    dnpsh = re.search(decimalnumberPattern, sizeparts[0])
                    if dnpsh:
                        data['artwork_measurements_height'] = dnpsh.groups()[0]
                    else:
                        data['artwork_measurements_height'] = sizeparts[0]
                    if sizeparts.__len__() > 1:
                        dnpsw = re.search(decimalnumberPattern, sizeparts[1])
                        if dnpsw:
                            data['artwork_measurements_width'] = dnpsw.groups()[0]
                        else:
                            data['artwork_measurements_width'] = sizeparts[1]
                    if sizeparts.__len__() > 2:
                        dnpsd = re.search(decimalnumberPattern, sizeparts[2])
                        if dnpsd:
                            data['artwork_measurements_depth'] = dnpsd.groups()[0]
                        else:
                            data['artwork_measurements_depth'] = sizeparts[2]
                sps = re.search(signedPattern, ldpart)
                if sps:
                    data['artwork_markings'] = ldpart
                    data['artwork_markings'] = data['artwork_markings'].replace('"', "'")
                cdps = re.search(createdDatePattern, ldpart)
                if cdps:
                    cdpsg = cdps.groups()
                    data['artwork_start_year'] = cdpsg[0]
                """
                mps = re.search(mediumPattern, ldpart)
                if mps and 'artwork_materials' not in data.keys():
                    data['artwork_materials'] = ldpart
                    data['artwork_materials'] = data['artwork_materials'].replace('"', "'")
                """
                mps2 = re.search(mediumPattern2, ldpart)
                if mps2 and 'artwork_materials' not in data.keys():
                    data['artwork_materials'] = ldpart
                    data['artwork_materials'] = data['artwork_materials'].replace('"', "'")
                nemps = re.search(nonenglishmediumPattern, ldpart)
                if nemps and 'artwork_materials' not in data.keys():
                    data['artwork_materials'] = ldpart
                    data['artwork_materials'] = data['artwork_materials'].replace('"', "'")
                if 'artwork_materials' in data.keys():
                    exclusionPattern = re.compile("\s+(stamp)|(sign)|(annotate)|(publish)|(printed)|(number)", re.IGNORECASE|re.DOTALL)
                    mediumparts =data['artwork_materials'].split(",")
                    mediumlist = []
                    for expart in mediumparts:
                        if re.search(exclusionPattern, expart):
                            continue
                        else:
                            mediumlist.append(expart)
                    data['artwork_materials'] = ",".join(mediumlist)
                if 'artwork_markings' in data.keys():
                    inclusionPattern = re.compile("\ssigned", re.IGNORECASE|re.DOTALL)
                    signparts =data['artwork_markings'].split(",")
                    signlist = []
                    for signpart in signparts:
                        if not re.search(inclusionPattern, signpart):
                            continue
                        else:
                            signlist.append(signpart)
                    data['artwork_markings'] = ",".join(signlist)
                ccps = re.search(conceptionPattern, ldpart)
                if ccps:
                    data['CONCEPTIONYEARFROM'] = ccps.groups()[0]
                edps = re.search(editionPattern, ldpart)
                if edps:
                    editionNumber = edps.groups()[0]
                    data['artwork_edition'] = editionNumber
                    ldpartsections = ldpart.split(". ")
                    for ldpartsection in ldpartsections:
                        edps2 = re.search(editionPattern, ldpartsection)
                        if edps2:
                            data['artwork_edition'] = ldpartsection
            image = lotdata['image']['image_src']
            if re.search(partialUrlPattern, image):
                onlineonlysearch = re.search(self.__class__.onlineChristiesPattern, self.baseUrl)
                if onlineonlysearch:
                    image = "https://onlineonly.christies.com" + image
                else:
                    image = baseUrl + image
            imagename1 = self.getImagenameFromUrl(image)
            imagename1 = str(imagename1)
            imagename1 = imagename1.replace("b'", "").replace("'", "")
            auctiontitle = self.auctiontitle.replace(" ", "_")
            processedAuctionTitle = auctiontitle.replace(" ", "_")
            processedArtistName = artistname.replace(" ", "_")
            processedArtistName = unidecode.unidecode(processedArtistName)
            processedArtworkName = data['artwork_name'].replace(" ", "_")
            processedArtworkName = unidecode.unidecode(processedArtworkName)
            sublot_number = ""
            #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + self.saleno + "__" + lotno + "__" + sublot_number
            newname1 = self.saleno + "__" + processedArtistName + "__" + lotno + "_a"
            #encryptedFilename = self.encryptFilename(newname1)
            encryptedFilename = newname1
            imagepathparts = image.split("/")
            defimageurl = "/".join(imagepathparts[:-2])
            encryptedFilename = str(encryptedFilename).replace("b'", "")
            encryptedFilename = str(encryptedFilename).replace("'", "")
            data['image1_name'] = str(encryptedFilename) + ".jpg"
            data['artwork_images1'] = image
            """
            if downloadimages == "1":
                encryptedFilename = str(encryptedFilename) + "-a.jpg"
                self.renameImageFile(imagepath, imagename1, encryptedFilename)
            """
            #data['DefaultImageUrl'] = image
            estimatetext = lotdata['estimate_txt']
            etps2 = re.search(estimatePattern2, estimatetext)
            etps = re.search(estimatePattern, estimatetext)
            if etps2:
                etpsg = etps2.groups()
                low = etpsg[1]
                high = etpsg[2]
                currency = etpsg[0]
                data['price_estimate_min'] = low
                data['price_estimate_max'] = high
            elif etps:
                etpsg = etps.groups()
                low = etpsg[1]
                high = etpsg[2]
                currency = etpsg[0]
                data['price_estimate_min'] = low
                data['price_estimate_max'] = high
            pricerealized = lotdata['price_realised_txt']
            pricerealizedparts = pricerealized.split(" ")
            if pricerealizedparts.__len__() > 1:
                data['price_sold'] = pricerealizedparts[1] + " " + pricerealizedparts[0]
            if ispartialURL(detailUrl):
                if self.online:
                    detailUrl = "https://onlineonly.christies.com" + detailUrl
                else:
                    detailUrl = baseUrl + detailUrl
            data['lot_origin_url'] = detailUrl
            data['auction_num'] = self.saleno
            data['auction_name'] = self.auctiontitle
            print("Getting '%s'..."%detailUrl)
            detailsPageContent = self.getDetailsPage(detailUrl)
            detailData = self.parseDetailPage(detailsPageContent, lotno, imagepath, artistname, data['artwork_name'], downloadimages)
            for k in detailData.keys():
                if k == 'artwork_materials' and k not in data.keys():
                    data[k] = detailData[k]
                    continue
                data[k] = detailData[k]
            if 'price_sold' not in data.keys() or data['price_sold'] == "":
                data['price_sold'] = "0"
            if self.saleno == "20689":
                if 'artwork_materials' not in data.keys() or data['artwork_materials'] == "":
                    data['artwork_materials'] = data['artist_name'].lower()
                    artist = data['artist_name']
                    data['artist_name'] = data['artwork_name']
                    data['artwork_name'] = artist
            if 'artwork_materials' in data.keys() and 'artwork_category' not in data.keys():
                materials = data['artwork_materials']
                materialparts = materials.split(" ")
                catfound = 0
                for matpart in materialparts:
                    if matpart in ['in', 'on', 'of', 'the', 'from']:
                        continue
                    try:
                        matPattern = re.compile(matpart, re.IGNORECASE|re.DOTALL)
                        for enkey in matcatdict_en.keys():
                            if re.search(matPattern, enkey):
                                data['artwork_category'] = matcatdict_en[enkey]
                                catfound = 1
                                break
                        for frkey in matcatdict_fr.keys():
                            if re.search(matPattern, frkey):
                                data['artwork_category'] = matcatdict_fr[frkey]
                                catfound = 1
                                break
                        if catfound:
                            break
                    except:
                        pass
            withdrawnPattern = re.compile("withdrawn", re.IGNORECASE|re.DOTALL)
            data['price_kind'] = "unknown"
            if ('price_sold' in data.keys() and re.search(withdrawnPattern, data['price_sold'])) or ('price_estimate_max' in data.keys() and re.search(withdrawnPattern, data['price_estimate_max'])):
                data['price_kind'] = "withdrawn"
            elif 'price_sold' in data.keys() and data['price_sold'] != "" and data['price_sold'] != "0":
                data['price_kind'] = "price realized"
            elif 'price_estimate_max' in data.keys() and data['price_estimate_max'] != "":
                data['price_kind'] = "estimate"
            else:
                pass
            nyrps = re.search(nyrPattern, self.auctionurl)
            if nyrps:
                data['auction_location'] = "New York"
            if self.online is True:
                data['auction_location'] = "Online"
            if 'auction_location' not in data.keys():
                data['auction_location'] = ""
            if 'artwork_name' in data.keys():
                yearPattern = re.compile("(\d{4})")
                endcommaPattern = re.compile(",\s*$")
                yaps = re.search(yearPattern, data['artwork_name'])
                if yaps:
                    data['artwork_start_year'] = yaps.groups()[0]
                    data['artwork_name'] = yearPattern.sub("", data['artwork_name'])
                    data['artwork_name'] = endcommaPattern.sub("", data['artwork_name'])
            if 'auction_location' not in data.keys() or data['auction_location'] == "":
                data['auction_location'] = self.auctionlocation
            if 'price_estimate_min' in data.keys():
                data['price_estimate_min'] = data['price_estimate_min'].replace(",", "").replace(" ", "")
            if 'price_estimate_max' in data.keys():
                data['price_estimate_max'] = data['price_estimate_max'].replace(",", "").replace(" ", "")
            if 'price_sold' in data.keys():
                data['price_sold'] = data['price_sold'].replace(",", "").replace(" ", "")
            info.append(data)
        return info

"""
['auction_house_name', 'auction_location', 'auction_num', 'auction_start_date', 'auction_end_date', 'auction_name', 'lot_num', 'sublot_num', 'price_kind', 'price_estimate_min', 'price_estimate_max', 'price_sold', 'artist_name', 'artist_birth', 'artist_death', 'artist_nationality', 'artwork_name', 'artwork_year_identifier', 'artwork_start_year', 'artwork_end_year', 'artwork_materials', 'artwork_category', 'artwork_markings', 'artwork_edition', 'artwork_description', 'artwork_measurements_height', 'artwork_measurements_width', 'artwork_measurements_depth', 'artwork_size_notes', 'auction_measureunit', 'artwork_condition_in', 'artwork_provenance', 'artwork_exhibited', 'artwork_literature', 'artwork_images1', 'artwork_images2', 'artwork_images3', 'artwork_images4', 'artwork_images5', 'image1_name', 'image2_name', 'image3_name', 'image4_name', 'image5_name', 'lot_origin_url']
 """
 
# That's it.... 

def updatestatus(auctionno, auctionurl):
    auctionurl = auctionurl.replace("%3A", ":")
    auctionurl = auctionurl.replace("%2F", "/")
    pageurl = "http://216.137.189.57:8080/scrapers/finish/?scrapername=Christies&auctionnumber=%s&auctionurl=%s&scrapertype=2"%(auctionno, urllib.parse.quote(auctionurl))
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
    christies = ChristiesBot(auctionurl, auctionnumber)
    fp = open(csvpath, "w")
    fieldnames = ['auction_house_name', 'auction_location', 'auction_num', 'auction_start_date', 'auction_end_date', 'auction_name', 'lot_num', 'sublot_num', 'price_kind', 'price_estimate_min', 'price_estimate_max', 'price_sold', 'artist_name', 'artist_birth', 'artist_death', 'artist_nationality', 'artwork_name', 'artwork_year_identifier', 'artwork_start_year', 'artwork_end_year', 'artwork_materials', 'artwork_category', 'artwork_markings', 'artwork_edition', 'artwork_description', 'artwork_measurements_height', 'artwork_measurements_width', 'artwork_measurements_depth', 'artwork_size_notes', 'auction_measureunit', 'artwork_condition_in', 'artwork_provenance', 'artwork_exhibited', 'artwork_literature', 'artwork_images1', 'artwork_images2', 'artwork_images3', 'artwork_images4', 'artwork_images5', 'image1_name', 'image2_name', 'image3_name', 'image4_name', 'image5_name', 'lot_origin_url']
    fieldsstr = ",".join(fieldnames)
    fp.write(fieldsstr + "\n")
    pagectr = 1
    auctionurlparts = auctionurl.split("/")
    saleid = auctionurlparts[-1]
    print(saleid)
    idPattern = re.compile("^\d+$") # this should be a 4 digit number
    lotsdata = christies.getLotsFromPage()
    
    while True:
        info = christies.getInfoFromLotsData(lotsdata, imagepath, downloadimages)
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
        if re.search(idPattern, saleid):
            requestUrl = "https://onlineonly.christies.com/sale/searchLots?action=paging&geocountrycode=&language=en&page=%s&pagesize=30&saleid=%s&salenumber=&saletype=&sid=&sortby=LotNumber"%(str(pagectr), str(saleid))
        else:
            break
        httpHeaders = {}
        httpHeaders['Host'] = "onlineonly.christies.com"
        httpHeaders['Origin'] = "https://onlineonly.christies.com"
        httpHeaders['Referer'] = auctionurl
        httpHeaders['Sec-Fetch-Mode'] = "cors"
        httpHeaders['Sec-Fetch-Dest'] = "empty"
        httpHeaders['Sec-Fetch-Site'] = "same-origin"
        httpHeaders['Content-Length'] = 0
        httpHeaders['Accept'] = "*/*"
        httpHeaders['Connection'] = "keep-alive"
        httpHeaders['Accept-Language'] = "en-US,en;q=0.5"
        httpHeaders['Accept-Encoding'] = "gzip, deflate"
        httpHeaders['User-Agent'] = "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:94.0) Gecko/20100101 Firefox/94.0"
        christies.pageRequest = urllib.request.Request(requestUrl, data=b"", headers=httpHeaders)
        try:
            christies.pageResponse = christies.opener.open(christies.pageRequest)
            christies.currentPageContent = christies.__class__._decodeGzippedContent(christies.getPageContent())
            #print(christies.currentPageContent)
            jsondata = json.loads(christies.currentPageContent)
            lotsdata = jsondata['lots']
            if lotsdata.__len__() == 0:
                break
        except:
            print ("Couldn't fetch page due to limited connectivity. Please check your internet connection and try again. %s"%sys.exc_info()[1].__str__())
            sys.exit()
    fp.close()
    updatestatus(auctionnumber, auctionurl)

# Example: python christies.py https://onlineonly.christies.com/s/moma-bill-brandt/lots/421   421   /Users/saiswarupsahu/freelanceprojectchetan/christies_421.csv /Users/saiswarupsahu/freelanceprojectchetan/254 0 0
# Christies scraper (christies2.py) version 2.0 - Following enhancements have been made over version 1.0
# 1. Multiprocessing over additional image downloads - version 1.0 was very slow due to lack of this.
# supmit

