# -*- coding: utf-8 -*-
import os, sys, re
import urllib, urllib.request
from urllib.parse import urlparse
import bs4
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


class VanhamBot(object):
    
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
        self.httpHeaders = { 'User-Agent' : r'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:94.0) Gecko/20100101 Firefox/94.0',  'Accept' : 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8', 'Accept-Language' : 'en-US,en;q=0.5', 'Accept-Encoding' : 'gzip,deflate', 'Accept-Charset' : 'ISO-8859-1,utf-8;q=0.7,*;q=0.7', 'Keep-Alive' : '115', 'Connection' : 'keep-alive', }
        self.httpHeaders['Host'] = "auction.van-ham.com"
        self.httpHeaders['cache-control'] = "max-age=0"
        self.httpHeaders['upgrade-insecure-requests'] = "1"
        self.httpHeaders['sec-fetch-dest'] = "document"
        self.httpHeaders['sec-fetch-mode'] = "navigate"
        self.httpHeaders['sec-fetch-site'] = "same-origin"
        self.httpHeaders['sec-fetch-user'] = "?1"
        self.httpHeaders['TE'] = "trailer"
        self.homeDir = os.getcwd()
        self.requestUrl = auctionurl
        #self.requestUrl = self.requestUrl + "&limit=96" # Get 96 lots per page, that way we need to navigate less pages.
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
        if not self.pageResponse:
            return b""
        return(self.pageResponse.read())

    def formatDate(cls, datestr):
        mondict = {'January' : '01', 'February' : '02', 'March' : '03', 'April' : '04', 'May' : '05', 'June' : '06', 'July' : '07', 'August' : '08', 'September' : '09', 'October' : '10', 'November' : '11', 'December' : '12' }
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
                mm = mondict3[datestrcomponents[1]]
            except:
                mm = mondict4[datestrcomponents[1]]
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
        pageContent = self.currentPageContent
        soup = BeautifulSoup(pageContent, features="html.parser")
        alldivtags = soup.find_all("div", {'class' : 'panel-heading'})
        if alldivtags.__len__() > 0:
            title = alldivtags[0].renderContents().decode('utf-8')
            title = title.replace("\n", "").replace("\r", "")
            title = self.__class__.htmltagPattern.sub("", title)
            titleparts = title.split("|")
            title = titleparts[0]
            beginspacePattern = re.compile("^\s+")
            endspacePattern = re.compile("\s+$")
            title = beginspacePattern.sub("", title)
            title = endspacePattern.sub("", title)
            self.auctiontitle = title
            if titleparts.__len__() > 2:
                datecontent = titleparts[2]
                datecontent = self.__class__.htmltagPattern.sub("", datecontent)
                datePattern = re.compile("(\d{1,2})\.(\d{1,2})\.(\d{4})", re.DOTALL)
                dps = re.search(datePattern, datecontent)
                if dps:
                    dpsg = dps.groups()
                    self.auctiondate = dpsg[1] + "/" + dpsg[0] + "/" + dpsg[2]
        if self.auctiontitle == "":
            self.auctiontitle = soup.find_all("title")[0].renderContents().decode('utf-8').split("|")[0]
        lotblocks = soup.find_all("div", {'class' : 'description pad'})
        return lotblocks
        

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


    def encryptFilename(self, filename):
        k = Fernet.generate_key()
        f = Fernet(k)
        encfilename = f.encrypt(filename.encode())
        return encfilename


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


    def parseDetailPage(self, detailsPage, lotno, imagepath, artistname, artworkname, downloadimages):
        baseUrl = "https://auction.van-ham.com"
        detailData = {}
        soup = BeautifulSoup(detailsPage, features="html.parser")
        mediumPattern = re.compile("Technique:\s+(.*)$", re.DOTALL|re.IGNORECASE)
        mediumPattern2 = re.compile("Technik:\s+(.*)$", re.DOTALL|re.IGNORECASE)
        signedPattern = re.compile("(signed)|(signiert)", re.IGNORECASE)
        editionPattern = re.compile("edition", re.IGNORECASE)
        sizePattern = re.compile("Measurement:\s+(.*)", re.IGNORECASE)
        sizePattern1a = re.compile("Depiction\s+Size:\s+(.*)", re.IGNORECASE) 
        sizePattern1b = re.compile("Sheet\s+Size:\s+(.*)", re.IGNORECASE)
        sizePattern1c = re.compile("Darstellungsmaß:\s+(.*)", re.IGNORECASE)
        sizePattern1d = re.compile("Blattmaß:\s+(.*)", re.IGNORECASE)
        sizePattern2 = re.compile("Height:\s+(.*)", re.IGNORECASE)
        sizePattern3 = re.compile("Maße\:\s*(.*?)\.")
        bdPattern = re.compile("(\d{4})\s+–\s+(\d{4})")
        yearPattern = re.compile("(\d{4})")
        provenancePattern = re.compile("Provenance:", re.DOTALL)
        literaturePattern = re.compile("Literature:", re.DOTALL)
        literaturePattern2 = re.compile("Literatur:", re.DOTALL)
        exhibitionPattern = re.compile("Exhibited:", re.DOTALL)
        measureunitPattern = re.compile("([a-zA-Z]{2})")
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
        titledivtags = soup.find_all("div", {'class' : 'itemtab'})
        if titledivtags.__len__() > 0:
            divcontents = titledivtags[0].renderContents().decode('utf-8')
            divcontents = divcontents.replace("\n", "").replace("\r", "")
            divparts = re.split("<br\s*\/?>", divcontents)
            if divparts.__len__() > 0:
                artist = divparts[0]
                artist = self.__class__.htmltagPattern.sub("", artist)
                detailData['artist_name'] = artist
            if divparts.__len__() > 1:
                birthdeathinfo = divparts[1]
                birthdeathinfo = self.__class__.htmltagPattern.sub("", birthdeathinfo)
                bdps = re.search(bdPattern, birthdeathinfo)
                if bdps:
                    detailData['artist_birth'] = bdps.groups()[0]
                    detailData['artist_death'] = bdps.groups()[1]
                else:
                    yps = re.search(yearPattern, birthdeathinfo)
                    if yps:
                        detailData['artist_birth'] = yps.groups()[0]
            divctr = 0
            for divpart in divparts:
                divpart = self.__class__.htmltagPattern.sub("", divpart)
                mps = re.search(mediumPattern, divpart)
                if mps:
                    detailData['artwork_materials'] = mps.groups()[0]
                mps2 = re.search(mediumPattern2, divpart)
                if mps2 and 'artwork_materials' not in detailData.keys():
                    detailData['artwork_materials'] = mps2.groups()[0]
                zps = re.search(sizePattern, divpart)
                if zps and 'artwork_size_notes' not in detailData.keys():
                    detailData['artwork_size_notes'] = zps.groups()[0]
                    sizeparts = detailData['artwork_size_notes'].split("x")
                    detailData['artwork_measurements_height'] = sizeparts[0]
                    if sizeparts.__len__() > 1:
                        detailData['artwork_measurements_width'] = sizeparts[1]
                        mups = re.search(measureunitPattern, detailData['artwork_measurements_width'])
                        if mups:
                            detailData['auction_measureunit'] = mups.groups()[0]
                            detailData['artwork_measurements_width'] = measureunitPattern.sub("", detailData['artwork_measurements_width'])
                    if sizeparts.__len__() > 2:
                        detailData['artwork_measurements_depth'] = sizeparts[2]
                        mups = re.search(measureunitPattern, detailData['artwork_measurements_depth'])
                        if mups:
                            detailData['auction_measureunit'] = mups.groups()[0]
                            detailData['artwork_measurements_depth'] = measureunitPattern.sub("", detailData['artwork_measurements_depth'])
                zps1a = re.search(sizePattern1a, divpart)
                if zps1a and 'artwork_size_notes' not in detailData.keys():
                    detailData['artwork_size_notes'] = zps1a.groups()[0]
                    sizeparts = detailData['artwork_size_notes'].split("x")
                    detailData['artwork_measurements_height'] = sizeparts[0]
                    if sizeparts.__len__() > 1:
                        detailData['artwork_measurements_width'] = sizeparts[1]
                        mups = re.search(measureunitPattern, detailData['artwork_measurements_width'])
                        if mups:
                            detailData['auction_measureunit'] = mups.groups()[0]
                            detailData['artwork_measurements_width'] = measureunitPattern.sub("", detailData['artwork_measurements_width'])
                    if sizeparts.__len__() > 2:
                        detailData['artwork_measurements_depth'] = sizeparts[2]
                        mups = re.search(measureunitPattern, detailData['artwork_measurements_depth'])
                        if mups:
                            detailData['auction_measureunit'] = mups.groups()[0]
                            detailData['artwork_measurements_depth'] = measureunitPattern.sub("", detailData['artwork_measurements_depth'])
                zps1b = re.search(sizePattern1b, divpart)
                if zps1b and 'artwork_size_notes' not in detailData.keys():
                    detailData['artwork_size_notes'] = zps1b.groups()[0]
                    sizeparts = detailData['artwork_size_notes'].split("x")
                    detailData['artwork_measurements_height'] = sizeparts[0]
                    if sizeparts.__len__() > 1:
                        detailData['artwork_measurements_width'] = sizeparts[1]
                        mups = re.search(measureunitPattern, detailData['artwork_measurements_width'])
                        if mups:
                            detailData['auction_measureunit'] = mups.groups()[0]
                            detailData['artwork_measurements_width'] = measureunitPattern.sub("", detailData['artwork_measurements_width'])
                    if sizeparts.__len__() > 2:
                        detailData['artwork_measurements_depth'] = sizeparts[2]
                        mups = re.search(measureunitPattern, detailData['artwork_measurements_depth'])
                        if mups:
                            detailData['auction_measureunit'] = mups.groups()[0]
                            detailData['artwork_measurements_depth'] = measureunitPattern.sub("", detailData['artwork_measurements_depth'])
                zps1c = re.search(sizePattern1c, divpart)
                if zps1c and 'artwork_size_notes' not in detailData.keys():
                    detailData['artwork_size_notes'] = zps1c.groups()[0]
                    sizeparts = detailData['artwork_size_notes'].split("x")
                    detailData['artwork_measurements_height'] = sizeparts[0]
                    if sizeparts.__len__() > 1:
                        detailData['artwork_measurements_width'] = sizeparts[1]
                        mups = re.search(measureunitPattern, detailData['artwork_measurements_width'])
                        if mups:
                            detailData['auction_measureunit'] = mups.groups()[0]
                            detailData['artwork_measurements_width'] = measureunitPattern.sub("", detailData['artwork_measurements_width'])
                    if sizeparts.__len__() > 2:
                        detailData['artwork_measurements_depth'] = sizeparts[2]
                        mups = re.search(measureunitPattern, detailData['artwork_measurements_depth'])
                        if mups:
                            detailData['auction_measureunit'] = mups.groups()[0]
                            detailData['artwork_measurements_depth'] = measureunitPattern.sub("", detailData['artwork_measurements_depth'])
                zps1d = re.search(sizePattern1d, divpart)
                if zps1d and 'artwork_size_notes' not in detailData.keys():
                    detailData['artwork_size_notes'] = zps1d.groups()[0]
                    sizeparts = detailData['artwork_size_notes'].split("x")
                    detailData['artwork_measurements_height'] = sizeparts[0]
                    if sizeparts.__len__() > 1:
                        detailData['artwork_measurements_width'] = sizeparts[1]
                        mups = re.search(measureunitPattern, detailData['artwork_measurements_width'])
                        if mups:
                            detailData['auction_measureunit'] = mups.groups()[0]
                            detailData['artwork_measurements_width'] = measureunitPattern.sub("", detailData['artwork_measurements_width'])
                    if sizeparts.__len__() > 2:
                        detailData['artwork_measurements_depth'] = sizeparts[2]
                        mups = re.search(measureunitPattern, detailData['artwork_measurements_depth'])
                        if mups:
                            detailData['auction_measureunit'] = mups.groups()[0]
                            detailData['artwork_measurements_depth'] = measureunitPattern.sub("", detailData['artwork_measurements_depth'])
                zps3 = re.search(sizePattern3, divpart)
                if zps3 and 'artwork_size_notes' not in detailData.keys():
                    detailData['artwork_size_notes'] = zps3.groups()[0]
                    sizeparts = detailData['artwork_size_notes'].split("x")
                    detailData['artwork_measurements_height'] = sizeparts[0]
                    if sizeparts.__len__() > 1:
                        detailData['artwork_measurements_width'] = sizeparts[1]
                        mups = re.search(measureunitPattern, detailData['artwork_measurements_width'])
                        if mups:
                            detailData['auction_measureunit'] = mups.groups()[0]
                            detailData['artwork_measurements_width'] = measureunitPattern.sub("", detailData['artwork_measurements_width'])
                    if sizeparts.__len__() > 2:
                        detailData['artwork_measurements_depth'] = sizeparts[2]
                        mups = re.search(measureunitPattern, detailData['artwork_measurements_depth'])
                        if mups:
                            detailData['auction_measureunit'] = mups.groups()[0]
                            detailData['artwork_measurements_depth'] = measureunitPattern.sub("", detailData['artwork_measurements_depth'])
                zps2 = re.search(sizePattern2, divpart)
                if zps2 and 'artwork_size_notes' not in detailData.keys():
                    detailData['artwork_size_notes'] = zps2.groups()[0]
                    detailData['artwork_measurements_height'] = zps2.groups()[0]
                    mups = re.search(measureunitPattern, detailData['artwork_measurements_height'])
                    if mups:
                        detailData['auction_measureunit'] = mups.groups()[0]
                        detailData['artwork_measurements_height'] = measureunitPattern.sub("", detailData['artwork_measurements_height'])
                pps = re.search(provenancePattern, divpart)
                if pps:
                    if divparts.__len__() > divctr + 1:
                        provcontent = divparts[divctr + 1]
                        provcontent = provcontent.replace('"', "'")
                        detailData['artwork_provenance'] = provcontent
                lps = re.search(literaturePattern, divpart)
                if lps:
                    if divparts.__len__() > divctr + 1:
                        litcontent = divparts[divctr + 1]
                        litcontent = litcontent.replace('"', "'")
                        detailData['artwork_literature'] = litcontent
                lps2 = re.search(literaturePattern2, divpart)
                if lps2:
                    if divparts.__len__() > divctr + 1:
                        litcontent = divparts[divctr + 1]
                        litcontent = litcontent.replace('"', "'")
                        detailData['artwork_literature'] = litcontent
                eps = re.search(exhibitionPattern, divpart)
                if eps:
                    if divparts.__len__() > divctr + 1:
                        excontent = divparts[divctr + 1]
                        excontent = excontent.replace('"', "'")
                        detailData['artwork_exhibited'] = excontent
                divctr += 1
        detailData['auction_house_name'] = "VAN HAM"
        if 'artwork_size_notes' not in detailData.keys():
            zps3 = re.search(sizePattern, detailsPage)
            if zps3:
                detailData['artwork_size_notes'] = zps.groups()[0]
                sizeparts = detailData['artwork_size_notes'].split("x")
                detailData['artwork_measurements_height'] = sizeparts[0]
                if sizeparts.__len__() > 1:
                    detailData['artwork_measurements_width'] = sizeparts[1]
                    mups = re.search(measureunitPattern, detailData['artwork_measurements_width'])
                    if mups:
                        detailData['auction_measureunit'] = mups.groups()[0]
                        detailData['artwork_measurements_width'] = measureunitPattern.sub("", detailData['artwork_measurements_width'])
                if sizeparts.__len__() > 2:
                    detailData['artwork_measurements_depth'] = sizeparts[2]
                    mups = re.search(measureunitPattern, detailData['artwork_measurements_depth'])
                    if mups:
                        detailData['auction_measureunit'] = mups.groups()[0]
                        detailData['artwork_measurements_depth'] = measureunitPattern.sub("", detailData['artwork_measurements_depth'])
        zps1a = re.search(sizePattern1a, detailsPage)
        if zps1a and 'artwork_size_notes' not in detailData.keys():
            detailData['artwork_size_notes'] = zps1a.groups()[0]
            sizeparts = detailData['artwork_size_notes'].split("x")
            detailData['artwork_measurements_height'] = sizeparts[0]
            if sizeparts.__len__() > 1:
                detailData['artwork_measurements_width'] = sizeparts[1]
                mups = re.search(measureunitPattern, detailData['artwork_measurements_width'])
                if mups:
                    detailData['auction_measureunit'] = mups.groups()[0]
                    detailData['artwork_measurements_width'] = measureunitPattern.sub("", detailData['artwork_measurements_width'])
            if sizeparts.__len__() > 2:
                detailData['artwork_measurements_depth'] = sizeparts[2]
                mups = re.search(measureunitPattern, detailData['artwork_measurements_depth'])
                if mups:
                    detailData['auction_measureunit'] = mups.groups()[0]
                    detailData['artwork_measurements_depth'] = measureunitPattern.sub("", detailData['artwork_measurements_depth'])
        zps1b = re.search(sizePattern1b, detailsPage)
        if zps1b and 'artwork_size_notes' not in detailData.keys():
            detailData['artwork_size_notes'] = zps1b.groups()[0]
            sizeparts = detailData['artwork_size_notes'].split("x")
            detailData['artwork_measurements_height'] = sizeparts[0]
            if sizeparts.__len__() > 1:
                detailData['artwork_measurements_width'] = sizeparts[1]
                mups = re.search(measureunitPattern, detailData['artwork_measurements_width'])
                if mups:
                    detailData['auction_measureunit'] = mups.groups()[0]
                    detailData['artwork_measurements_width'] = measureunitPattern.sub("", detailData['artwork_measurements_width'])
            if sizeparts.__len__() > 2:
                detailData['artwork_measurements_depth'] = sizeparts[2]
                mups = re.search(measureunitPattern, detailData['artwork_measurements_depth'])
                if mups:
                    detailData['auction_measureunit'] = mups.groups()[0]
                    detailData['artwork_measurements_depth'] = measureunitPattern.sub("", detailData['artwork_measurements_depth'])
        zps1c = re.search(sizePattern1c, divpart)
        if zps1c and 'artwork_size_notes' not in detailData.keys():
            detailData['artwork_size_notes'] = zps1c.groups()[0]
            sizeparts = detailData['artwork_size_notes'].split("x")
            detailData['artwork_measurements_height'] = sizeparts[0]
            if sizeparts.__len__() > 1:
                detailData['artwork_measurements_width'] = sizeparts[1]
                mups = re.search(measureunitPattern, detailData['artwork_measurements_width'])
                if mups:
                    detailData['auction_measureunit'] = mups.groups()[0]
                    detailData['artwork_measurements_width'] = measureunitPattern.sub("", detailData['artwork_measurements_width'])
            if sizeparts.__len__() > 2:
                detailData['artwork_measurements_depth'] = sizeparts[2]
                mups = re.search(measureunitPattern, detailData['artwork_measurements_depth'])
                if mups:
                    detailData['auction_measureunit'] = mups.groups()[0]
                    detailData['artwork_measurements_depth'] = measureunitPattern.sub("", detailData['artwork_measurements_depth'])
        zps1d = re.search(sizePattern1d, divpart)
        if zps1d and 'artwork_size_notes' not in detailData.keys():
            detailData['artwork_size_notes'] = zps1d.groups()[0]
            sizeparts = detailData['artwork_size_notes'].split("x")
            detailData['artwork_measurements_height'] = sizeparts[0]
            if sizeparts.__len__() > 1:
                detailData['artwork_measurements_width'] = sizeparts[1]
                mups = re.search(measureunitPattern, detailData['artwork_measurements_width'])
                if mups:
                    detailData['auction_measureunit'] = mups.groups()[0]
                    detailData['artwork_measurements_width'] = measureunitPattern.sub("", detailData['artwork_measurements_width'])
            if sizeparts.__len__() > 2:
                detailData['artwork_measurements_depth'] = sizeparts[2]
                mups = re.search(measureunitPattern, detailData['artwork_measurements_depth'])
                if mups:
                    detailData['auction_measureunit'] = mups.groups()[0]
                    detailData['artwork_measurements_depth'] = measureunitPattern.sub("", detailData['artwork_measurements_depth'])
        zps2 = re.search(sizePattern2, detailsPage)
        if zps2 and 'artwork_size_notes' not in detailData.keys():
            detailData['artwork_size_notes'] = zps2.groups()[0]
            detailData['artwork_measurements_height'] = zps2.groups()[0]
            mups = re.search(measureunitPattern, detailData['artwork_measurements_height'])
            if mups:
                detailData['auction_measureunit'] = mups.groups()[0]
                detailData['artwork_measurements_height'] = measureunitPattern.sub("", detailData['artwork_measurements_height'])
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
        allimageanchortags = soup.find_all("a", {'data-zoom-id' : 'zoom'})
        urlPattern = re.compile("url\('([^']+)'\)")
        actr = 0
        defaultimgurl = ""
        metaimagetags = soup.find_all("a", {'id' : 'zoom'})
        if metaimagetags.__len__() > 0:
            defaultimgurl = baseUrl + "/" + metaimagetags[0]['href']
        imagename1 = self.getImagenameFromUrl(defaultimgurl)
        imagename1 = str(imagename1)
        imagename1 = imagename1.replace("b'", "").replace("'", "")
        auctiontitle = self.auctiontitle.replace(" ", "_")
        processedAuctionTitle = auctiontitle.replace(" ", "_")
        processedArtistName = artistname.replace(" ", "_")
        processedArtistName = unidecode.unidecode(processedArtistName)
        processedArtworkName = artworkname.replace(" ", "_")
        sublot_number = ""
        #newname1 = processedAuctionTitle + "__" + processedArtistName + "__" + processedArtworkName + "__" + self.saleno + "__" + lotno + "__" + sublot_number
        newname1 = self.saleno + "__" + processedArtistName + "__" + str(lotno) + "_a"
        #encryptedFilename = self.encryptFilename(newname1)
        encryptedFilename = newname1
        imagepathparts = defaultimgurl.split("/")
        defimageurl = "/".join(imagepathparts[:-2])
        encryptedFilename = str(encryptedFilename).replace("b'", "")
        encryptedFilename = str(encryptedFilename).replace("'", "")
        detailData['image1_name'] = str(encryptedFilename) + ".jpg"
        detailData['artwork_images1'] = defaultimgurl
        altimages = []
        for anchortag in allimageanchortags:
            anchorstyle = anchortag['style']
            ups = re.search(urlPattern, anchorstyle)
            if ups:
                anchorurl = baseUrl + "/" + ups.groups()[0]
                anchorurl = anchorurl.replace('browse', 'item')
                altimages.append(anchorurl)
                actr += 1
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
            newname1 = self.saleno + "__" + processedArtistName + "__" + str(lotno) + "_b"
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
            newname1 = self.saleno + "__" + processedArtistName + "__" + str(lotno) + "_c"
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
            newname1 = self.saleno + "__" + processedArtistName + "__" + str(lotno) + "_d"
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
            newname1 = self.saleno + "__" + processedArtistName + "__" + str(lotno) + "_e"
            #encryptedFilename = self.encryptFilename(newname1)
            encryptedFilename = newname1
            detailData['image' + str(imgctr) + '_name'] = str(encryptedFilename) + ".jpg"
            detailData['artwork_images' + str(imgctr)] = altimage2
            imgctr += 1
        itemdivtags = soup.find_all("div", {'class' : 'itemtab'})
        if itemdivtags.__len__() > 0:
            itemcontents = itemdivtags[0].renderContents().decode('utf-8')
            itemcontents = itemcontents.replace("\n", "").replace("\r", "")
            itemcontents = self.__class__.htmltagPattern.sub("", itemcontents)
            detailData['artwork_description'] = itemcontents
            detailData['artwork_description'] = detailData['artwork_description'].strip()
            detailData['artwork_description'] = self.__class__.htmltagPattern.sub("", detailData['artwork_description'])
            detailData['artwork_description'] = detailData['artwork_description'].replace("\n", " ")
            detailData['artwork_description'] = detailData['artwork_description'].replace("\r", " ")
            detailData['artwork_description'] = detailData['artwork_description'].replace('"', "'")
            detailData['artwork_description'] = detailData['artwork_description'].replace("Provenance", "<br><strong>Provenance</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("Literature", "<br><strong>Literature</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("Exhibited", "<br><strong>Exhibited</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("Expositions", "<br><strong>Expositions</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("Bibliographie", "<br><strong>Literature</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("Condition Report", "<br><strong>Condition Report</strong><br>")
            detailData['artwork_description'] = detailData['artwork_description'].replace("Notes:", "<br><strong>Notes:</strong><br>")
            detailData['artwork_description'] = "<strong><br>Description<br></strong>" + detailData['artwork_description']
            detailData['artwork_description'] = detailData['artwork_description'].replace('"', "'")
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
        return imagefilename


    def getInfoFromLotsData(self, htmlList, imagepath, downloadimages):
        baseUrl = "https://auction.van-ham.com"
        info = []
        endSpacePattern = re.compile("\s+$", re.DOTALL)
        beginspacePattern = re.compile("^\s+")
        brPattern = re.compile("<br\s*\/?>", re.IGNORECASE)
        for htmldiv in htmlList:
            data = {}
            data['auction_num'] = self.saleno
            data['auction_start_date'] = self.auctiondate
            lotno = ""
            data['artwork_name'] = ""
            data['artist_name'] = ""
            htmlContent = htmldiv.renderContents().decode('utf-8')
            s = BeautifulSoup(htmlContent, features="html.parser")
            data['lot_origin_url'] = ""
            data['artwork_name'] = ""
            allanchors = s.find_all("a")
            if allanchors.__len__() > 1:
                htmlanchor = allanchors[1]
                detailUrl = htmlanchor['href']
                data['lot_origin_url'] = detailUrl
                if type(htmlanchor) == bs4.element.Tag and htmlanchor.has_attr('title'):
                    data['artwork_name'] = htmlanchor['title']
            htmlContent = htmlContent.replace("\n", " ").replace("\r", " ")
            #htmlParts = re.split(brPattern, htmlContent)
            htmlContent = self.__class__.htmltagPattern.sub("", htmlContent)
            htmlContent = htmlContent.replace(data['artwork_name'], "")
            data['lot_num'] = ""
            infoPattern = re.compile("Lo[ts]{1}\s+(\d+)\s+(.*)", re.DOTALL)
            infoPattern2 = re.compile("Lo[ts]{1}\s+(\d+)", re.DOTALL)
            ifs = re.search(infoPattern, htmlContent)
            ifs2 = re.search(infoPattern2, htmlContent)
            if ifs:
                lotno = ifs.groups()[0]
                artist = ifs.groups()[1]
                data['lot_num'] = lotno
                data['artist_name'] = artist
            elif ifs2:
                lotno = ifs2.groups()[0]
                data['lot_num'] = lotno
            if not lotno:
                continue
            estimatediv = htmldiv.findNext("div", {'class' : 'pad estimated'})
            data['price_estimate_min'] = ""
            data['price_estimate_max'] = ""
            if estimatediv:
                estimatecontents = estimatediv.renderContents().decode('utf-8')
                estimatecontents = estimatecontents.replace("\n", " ").replace("\r", "")
                estimatecontents = self.__class__.htmltagPattern.sub("", estimatecontents)
                estimatePattern = re.compile("Estimate:\s+([\d\.,]+)\s+\-\s+([\d\.,]+)\s+(\S)\s*$", re.DOTALL)
                estimatePattern2 = re.compile("Taxe:\s+([\d\.,]+)\s+\-\s+([\d\.,]+)\s+(\S)\s*$", re.DOTALL)
                eps = re.search(estimatePattern, estimatecontents)
                eps2 = re.search(estimatePattern2, estimatecontents)
                if eps:
                    epsg = eps.groups()
                    low = epsg[0]
                    high = epsg[1]
                    low = low.replace(".", "")
                    high = high.replace(".", "")
                    currsymb = epsg[2]
                    currency = "USD"
                    if currsymb == "€":
                        currency = "EUR"
                    elif currsymb == "£":
                        currency = "GBP"
                    else:
                        pass
                    data['price_estimate_min'] = low
                    data['price_estimate_max'] = high
                elif eps2:
                    epsg = eps2.groups()
                    low = epsg[0]
                    high = epsg[1]
                    low = low.replace(".", "")
                    high = high.replace(".", "")
                    currsymb = epsg[2]
                    currency = "USD"
                    if currsymb == "€":
                        currency = "EUR"
                    elif currsymb == "£":
                        currency = "GBP"
                    else:
                        pass
                    data['price_estimate_min'] = low
                    data['price_estimate_max'] = high
            soldspantag = None # Initialize it so that the previous value is removed
            soldspantag = estimatediv.findNext("span", {'class' : 'current_bid'})
            try:
                biddingdiv = htmldiv.findNext("div", {'class' : 'pad bidding'})
            except:
                biddingdiv = None
            data['price_sold'] = "0"
            soldPattern = re.compile("([\d\.,]+)\s+(\S)\s*$", re.DOTALL)
            soldPattern2 = re.compile("Ergebnis\:\s*([\d\.,]+)\s+(\S)", re.DOTALL|re.IGNORECASE)
            soldPattern3 = re.compile("Result\:\s*([\d\.,]+)\s+(\S)", re.DOTALL|re.IGNORECASE)
            if soldspantag:
                soldcontents = soldspantag.renderContents().decode('utf-8')
                soldcontents = soldcontents.replace("\n", "").replace("\r", "")
                soldcontents = self.__class__.htmltagPattern.sub("", soldcontents)
                sps = re.search(soldPattern, soldcontents)
                if sps:
                    spsg = sps.groups()
                    soldprice = spsg[0]
                    soldprice = soldprice.replace(".", "")
                    soldcurr = spsg[1]
                    currency = "USD"
                    if soldcurr == "€":
                        currency = "EUR"
                    elif soldcurr == "£":
                        currency = "GBP"
                    else:
                        pass
                    data['price_sold'] = soldprice
            if biddingdiv and ('price_sold' not in data.keys() or data['price_sold'] == "0"):
                biddingcontents = biddingdiv.renderContents().decode('utf-8')
                biddingcontents = biddingcontents.replace("\n", "").replace("\r", "")
                biddingcontents = self.__class__.htmltagPattern.sub("", biddingcontents)
                sps2 = re.search(soldPattern2, biddingcontents)
                if sps2:
                    spsg = sps2.groups()
                    soldprice = spsg[0]
                    soldprice = soldprice.replace(".", "")
                    soldcurr = spsg[1]
                    currency = "USD"
                    if soldcurr == "€":
                        currency = "EUR"
                    elif soldcurr == "£":
                        currency = "GBP"
                    else:
                        pass
                    data['price_sold'] = soldprice
            if biddingdiv and ('price_sold' not in data.keys() or data['price_sold'] == "0"):
                biddingcontents = biddingdiv.renderContents().decode('utf-8')
                biddingcontents = biddingcontents.replace("\n", "").replace("\r", "")
                biddingcontents = self.__class__.htmltagPattern.sub("", biddingcontents)
                sps3 = re.search(soldPattern3, biddingcontents)
                if sps3:
                    spsg = sps3.groups()
                    soldprice = spsg[0]
                    soldprice = soldprice.replace(".", "")
                    soldcurr = spsg[1]
                    currency = "USD"
                    if soldcurr == "€":
                        currency = "EUR"
                    elif soldcurr == "£":
                        currency = "GBP"
                    else:
                        pass
                    data['price_sold'] = soldprice
            if 'artwork_name' in data.keys():
                data['artwork_name'] = data['artwork_name'].replace('"', "")
            """
            try:
                print(data['lot_num'] + " ## " + data['artwork_name'] + " ## " + data['artist_name'] + " ## " + data['price_estimate_min'] + " ## " + data['price_sold'])
            except:
                print(data['lot_num'] + " ## " + data['artwork_name'])
            """
            detailparts = detailUrl.split("/")
            print("Getting '%s'..."%data['lot_origin_url'])
            detailsPageContent = self.getDetailsPage(detailUrl)
            detailData = self.parseDetailPage(detailsPageContent, lotno, imagepath, data['artist_name'], data['artwork_name'], downloadimages)
            for k in detailData.keys():
                data[k] = detailData[k]
            data['auction_name'] = self.auctiontitle
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
            data['auction_location'] = "Cologne"
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
    pageurl = "http://216.137.189.57:8080/scrapers/finish/?scrapername=Vanham&auctionnumber=%s&auctionurl=%s&scrapertype=2"%(auctionno, urllib.parse.quote(auctionurl))
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
    vanham = VanhamBot(auctionurl, auctionnumber)
    fp = open(csvpath, "w")
    fieldnames = ['auction_house_name', 'auction_location', 'auction_num', 'auction_start_date', 'auction_end_date', 'auction_name', 'lot_num', 'sublot_num', 'price_kind', 'price_estimate_min', 'price_estimate_max', 'price_sold', 'artist_name', 'artist_birth', 'artist_death', 'artist_nationality', 'artwork_name', 'artwork_year_identifier', 'artwork_start_year', 'artwork_end_year', 'artwork_materials', 'artwork_category', 'artwork_markings', 'artwork_edition', 'artwork_description', 'artwork_measurements_height', 'artwork_measurements_width', 'artwork_measurements_depth', 'artwork_size_notes', 'auction_measureunit', 'artwork_condition_in', 'artwork_provenance', 'artwork_exhibited', 'artwork_literature', 'artwork_images1', 'artwork_images2', 'artwork_images3', 'artwork_images4', 'artwork_images5', 'image1_name', 'image2_name', 'image3_name', 'image4_name', 'image5_name', 'lot_origin_url']
    fieldsstr = ",".join(fieldnames)
    fp.write(fieldsstr + "\n")
    pagectr = 1
    while True:
        lotsdata = vanham.getLotsFromPage()
        if lotsdata.__len__() == 0:
            break
        info = vanham.getInfoFromLotsData(lotsdata, imagepath, downloadimages)
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
        nextpageUrl = "https://auction.van-ham.com/en/browse.php?view=grid&block=%s&search_closed=y&search=1&page=%s"%(auctionnumber, str(pagectr))
        vanham.pageRequest = urllib.request.Request(nextpageUrl, headers=vanham.httpHeaders)
        try:
            vanham.pageResponse = vanham.opener.open(vanham.pageRequest)
        except:
            print("Couldn't find the page %s"%str(pagectr))
            break
        vanham.currentPageContent = vanham.__class__._decodeGzippedContent(vanham.getPageContent())
    fp.close()
    updatestatus(auctionnumber, auctionurl)

# Example: python vanham.py "https://auction.van-ham.com/browse.php?search=1&search_closed=y&block=267" 267 /Users/saiswarupsahu/freelanceprojectchetan/vanham_267.csv /Users/saiswarupsahu/freelanceprojectchetan/1-5TNCV9 0 0

# supmit

