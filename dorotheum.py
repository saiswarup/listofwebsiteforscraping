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


class DorotheumBot(object):
    
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
        self.auctionlocation = ""



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
        alltitletags = soup.find_all("title")
        if alltitletags.__len__() > 0:
            title = alltitletags[0].renderContents().decode('utf-8')
            dorotheumPattern = re.compile("\s*\-?\s*dorotheum", re.IGNORECASE)
            countPattern = re.compile("\(.*?\)")
            datePattern = re.compile("\d+\/\d+\/\d+\s*")
            title = dorotheumPattern.sub("", title)
            title = countPattern.sub("", title)
            title = datePattern.sub("", title)
            self.auctiontitle = title
        auctiondetailboxPattern = re.compile("^auction-detail-box")
        allbluedivtags = soup.find_all("div", {'class' : auctiondetailboxPattern})
        if allbluedivtags.__len__() > 0:
            auctiondatePattern = re.compile("Auction\s+Date\:\s+(\d{2}\.\d{2}\.\d{4})\,?", re.DOTALL)
            locationPattern = re.compile("Location\:\s*(.*)$", re.DOTALL|re.IGNORECASE)
            allptags = allbluedivtags[0].find_all("p")
            for ptag in allptags:
                pcontent = ptag.renderContents().decode('utf-8')
                pcontent = pcontent.replace("\n", "").replace("\r", "")
                pcontent = self.__class__.htmltagPattern.sub("", pcontent)
                adps = re.search(auctiondatePattern, pcontent)
                if adps:
                    auctiondate = adps.groups()[0]
                    self.auctiondate = auctiondate
                    continue
                lps = re.search(locationPattern, pcontent)
                if lps:
                    auctionlocation = lps.groups()[0]
                    self.auctionlocation = auctionlocation
                    #print(self.auctionlocation)
        lotblocks = soup.find_all("li", {'class' : 'flex-row table-row no-list-style'})
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


    def parseDetailPage(self, detailsPage, lotno, imagepath, artistname, downloadimages):
        baseUrl = "https://www.dorotheum.com"
        detailData = {}
        soup = BeautifulSoup(detailsPage, features="html.parser")
        detailsdivlist = soup.find_all("div", {'class' : 'bodytext-html'})
        if detailsdivlist.__len__() == 0:
            return detailData
        brPattern = re.compile("<br\s*\/?>", re.IGNORECASE)
        mediumPattern = re.compile("(gold)|(silver)|(brass)|(bronze)|(wood)|(porcelain)|(stone)|(marble)|(metal)|(steel)|(iron)|(glass)|(plexiglas)|(chromogenic)|(paper)|(canvas)|(masonite)|(newsprint)|(silkscreen)|(parchment)|(linen)|(inkjet)|(ink\s+jet)|(pigment)|(\stin\s)|(photogravure)|(\s+oil\s+)|(\s+panel)|(terracotta)|(ivory)|(\s+oak\s+)|(^oak\s+)|(\s+oak$)|(alabaster)|(c-print)|(Acryl\-Nitryl\-Butadien\-Styro)|(methacrylate)|(\s+PVC\s+)|(tempera)", re.DOTALL|re.IGNORECASE)
        nonenglishmediumPattern = re.compile("(crayon)|(encre)|(plume)|(plume\s+et\s+encre)|(papier)|(pastel)|(craie)|(gouachée)|(aquarelle)|(lithographique)|(plomb)|(huile)|(cuivre)|(toile)|(bronze)|(Plâtre)|(en\s+terre\s+de\s+faïence)|(Öl)|(holz)|(leinwand)", re.IGNORECASE|re.DOTALL)
        signedPattern = re.compile("signed", re.IGNORECASE)
        signedPattern2 = re.compile("signiert", re.IGNORECASE)
        datedPattern = re.compile("dated\s+[\w\s,\-\']+(\d{4})", re.IGNORECASE|re.DOTALL)
        datedPattern2 = re.compile("dated\s+[\w\s,\-\']+", re.IGNORECASE|re.DOTALL)
        editionPattern = re.compile("édition", re.IGNORECASE)
        sizePattern = re.compile("([\d,\.]+\s*x\s*[\d,\.]+\s*cm)", re.IGNORECASE)
        sizePattern2 = re.compile("([\d,\.]+\s*cm)", re.IGNORECASE)
        untitledPattern = re.compile("untitled", re.IGNORECASE|re.DOTALL)
        exhibitedPattern = re.compile("exhibited\:", re.IGNORECASE|re.DOTALL)
        provenancePattern = re.compile("provenance\:", re.IGNORECASE|re.DOTALL)
        provenancePattern2 = re.compile("provenienz\:", re.IGNORECASE|re.DOTALL)
        literaturePattern = re.compile("Literature\:", re.IGNORECASE|re.DOTALL)
        publisherPattern = re.compile("published\s+by\s+", re.IGNORECASE|re.DOTALL)
        bornPattern = re.compile("\s+in\s+(\d{4})", re.IGNORECASE|re.DOTALL)
        birthdeathPattern = re.compile("(\d{4})\s*\-\s*(\d{4})")
        nationalityPattern = re.compile("\([\w\s+,\/\.]+\d{4}–?\d{0,4}\s+(.*)\)")
        beginspacePattern = re.compile("^\s+")
        numericPattern = re.compile("(\d{4})")
        measureunitPattern = re.compile("([a-zA-Z]{2})")
        matcatdict_en = {}
        matcatdict_fr = {}
        #with open("docs/fineart_materials.csv", newline='') as mapfile:
        with open("/root/artwork/deploydirnew/docs/fineart_materials.csv", newline='') as mapfile:
            mapreader = csv.reader(mapfile, delimiter=",", quotechar='"')
            for maprow in mapreader:
                matcatdict_en[maprow[1]] = maprow[3]
                matcatdict_fr[maprow[2]] = maprow[3]
        ctr = 1
        artworkname = ""
        for detailsdiv in detailsdivlist:
            if ctr == 1:
                divcontent = detailsdiv.renderContents().decode('utf-8')
                divcontent = divcontent.replace("\n", "").replace("\r", "")
                contentparts = re.split(brPattern, divcontent)
                bornpart = contentparts[0]
                bps = re.search(bornPattern, bornpart)
                if bps:
                    detailData['artist_birth'] = bps.groups()[0]
                bdps = re.search(birthdeathPattern, bornpart)
                if bdps:
                    detailData['artist_birth'] = bdps.groups()[0]
                    detailData['artist_death'] = bdps.groups()[1]
                if contentparts.__len__() > 1:
                    if contentparts.__len__() > 2:
                        infocontent = contentparts[1]
                    else:
                        infocontent = contentparts[0]
                    infoparts = infocontent.split(",")
                    if contentparts.__len__() > 2:
                        detailData['artwork_name'] = infoparts[0]
                    else:
                        if "(" in infocontent or re.search(numericPattern, infocontent):
                            titlecontent = contentparts[1]
                            titleparts = titlecontent.split(",")
                            detailData['artwork_name'] = titleparts[0]
                            yps = re.search(numericPattern, titlecontent)
                            if yps:
                                detailData['YEARFROM'] = yps.groups()[0]
                            infocontent = infocontent.replace("–", "-")
                            bdps = re.search(birthdeathPattern, infocontent)
                            if bdps:
                                detailData['artist_birth'] = bdps.groups()[0]
                                detailData['artist_death'] = bdps.groups()[1]
                        else:
                            detailData['artwork_name'] = infocontent
                    detailData['artwork_name'] = self.__class__.htmltagPattern.sub("", detailData['artwork_name'])
                    detailData['artwork_name'] = beginspacePattern.sub("", detailData['artwork_name'])
                    detailData['artwork_name'] = detailData['artwork_name'].replace('"', "'")
                    artworkname = detailData['artwork_name']
                    #print(detailData['artwork_name'])
                    """
                    if not re.search(untitledPattern, infoparts[0]):
                        detailData['artwork_name'] = contentparts[0]
                        detailData['artwork_name'] = self.__class__.htmltagPattern.sub("", detailData['artwork_name'])
                    """
                    if contentparts.__len__() > 2:
                        infocontent = contentparts[2]
                    else:
                        infocontent = contentparts[1]
                    if not re.search(mediumPattern, infocontent) and contentparts.__len__() > 3:
                        infocontent = contentparts[3]
                    infoparts = infocontent.split(",")
                    detailData['CATEGORY'] = '2d'
                    mediumlist = []
                    for infopart in infoparts:
                        sps = re.search(signedPattern, infopart)
                        if sps:
                            detailData['artwork_markings'] = infopart
                            detailData['artwork_markings'] = self.__class__.htmltagPattern.sub("", detailData['artwork_markings'])
                            detailData['artwork_markings'] = beginspacePattern.sub("", detailData['artwork_markings'])
                        dps = re.search(datedPattern, infopart)
                        if dps and 'artwork_markings' in detailData.keys():
                            detailData['artwork_markings'] = detailData['artwork_markings'] + ", " + infopart
                            detailData['artwork_markings'] = self.__class__.htmltagPattern.sub("", detailData['artwork_markings'])
                            detailData['artwork_start_year'] = dps.groups()[0]
                        dps2 = re.search(datedPattern2, infopart)
                        if dps2 and not dps and 'artwork_markings' in detailData.keys():
                            detailData['artwork_markings'] = detailData['artwork_markings'] + ", " + infopart
                            detailData['artwork_markings'] = self.__class__.htmltagPattern.sub("", detailData['artwork_markings'])
                        sps2 = re.search(signedPattern2, infopart)
                        if sps2 and 'artwork_markings' not in detailData.keys():
                            detailData['artwork_markings'] = infopart
                            detailData['artwork_markings'] = self.__class__.htmltagPattern.sub("", detailData['artwork_markings'])
                            detailData['artwork_markings'] = beginspacePattern.sub("", detailData['artwork_markings'])
                            detailData['artwork_markings'] = detailData['artwork_markings'].replace('"', "'")
                        mps = re.search(mediumPattern, infopart)
                        if mps:
                            mediumlist.append(infopart)
                        if mps and 'artwork_materials' not in detailData.keys():
                            detailData['artwork_materials'] = infopart
                            detailData['artwork_materials'] = self.__class__.htmltagPattern.sub("", detailData['artwork_materials'])
                            detailData['artwork_materials'] = beginspacePattern.sub("", detailData['artwork_materials'])
                            #print(detailData['artwork_materials'])
                        nemps = re.search(nonenglishmediumPattern, infopart)
                        if nemps and 'artwork_materials' not in detailData.keys():
                            detailData['artwork_materials'] = infopart
                            detailData['artwork_materials'] = self.__class__.htmltagPattern.sub("", detailData['artwork_materials'])
                            detailData['artwork_materials'] = beginspacePattern.sub("", detailData['artwork_materials'])
                        zps = re.search(sizePattern, divcontent)
                        #print(divcontent)
                        if zps and 'artwork_size_notes' not in detailData.keys():
                            detailData['artwork_size_notes'] = zps.groups()[0]
                            detailData['artwork_size_notes'] = self.__class__.htmltagPattern.sub("", detailData['artwork_size_notes'])
                            detailData['artwork_size_notes'] = beginspacePattern.sub("", detailData['artwork_size_notes'])
                            #print(detailData['artwork_size_notes'])
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
                        zps2 = re.search(sizePattern2, divcontent)
                        if zps2 and 'artwork_size_notes' not in detailData.keys():
                            detailData['artwork_size_notes'] = zps2.groups()[0]
                            detailData['artwork_size_notes'] = self.__class__.htmltagPattern.sub("", detailData['artwork_size_notes'])
                            detailData['artwork_size_notes'] = beginspacePattern.sub("", detailData['artwork_size_notes'])
                            #print(detailData['artwork_size_notes'])
                            sizeparts = detailData['artwork_size_notes'].split("x")
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
                    if 'artwork_materials' not in detailData.keys() and mediumlist.__len__() > 0:
                        detailData['artwork_materials'] = ", ".join(mediumlist)
                    #if 'artwork_materials' in detailData.keys():
                    #    print(detailData['artwork_materials'])
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
            if ctr == 2:
                divcontent = detailsdiv.renderContents().decode('utf-8')
                divcontent = divcontent.replace("\n", "").replace("\r", "")
                doublebrPattern = re.compile("<br\/>\s*<br\/>", re.IGNORECASE|re.DOTALL)
                divcontentparts = re.split(doublebrPattern, divcontent)
                for infopart in divcontentparts:
                    eps = re.search(exhibitedPattern, infopart)
                    if eps and 'artwork_exhibited' not in detailData.keys():
                        detailData['artwork_exhibited'] = infopart
                        detailData['artwork_exhibited'] = self.__class__.htmltagPattern.sub("", detailData['artwork_exhibited'])
                        detailData['artwork_exhibited'] = detailData['artwork_exhibited'].replace('"', "'")
                        detailData['artwork_exhibited'] = detailData['artwork_exhibited'].replace('Exhibited:', "")
                        detailData['artwork_exhibited'] = detailData['artwork_exhibited'].replace(',', ";")
                        detailData['artwork_exhibited'] = beginspacePattern.sub("", detailData['artwork_exhibited'])
                    pps = re.search(provenancePattern, infopart)
                    if pps and 'artwork_provenance' not in detailData.keys():
                        detailData['artwork_provenance'] = infopart
                        detailData['artwork_provenance'] = self.__class__.htmltagPattern.sub("", detailData['artwork_provenance'])
                        detailData['artwork_provenance'] = detailData['artwork_provenance'].replace('"', "'")
                        detailData['artwork_provenance'] = detailData['artwork_provenance'].replace(',', ";")
                        detailData['artwork_provenance'] = detailData['artwork_provenance'].replace('Provenance:', "")
                        detailData['artwork_provenance'] = beginspacePattern.sub("", detailData['artwork_provenance'])
                    pps2 = re.search(provenancePattern2, infopart)
                    if pps2 and 'artwork_provenance' not in detailData.keys():
                        detailData['artwork_provenance'] = infopart
                        detailData['artwork_provenance'] = self.__class__.htmltagPattern.sub("", detailData['artwork_provenance'])
                        detailData['artwork_provenance'] = detailData['artwork_provenance'].replace('"', "'")
                        detailData['artwork_provenance'] = detailData['artwork_provenance'].replace(',', ";")
                        detailData['artwork_provenance'] = detailData['artwork_provenance'].replace('Provenienz:', "")
                        detailData['artwork_provenance'] = beginspacePattern.sub("", detailData['artwork_provenance'])
                    lps = re.search(literaturePattern, infopart)
                    if lps and 'artwork_literature' not in detailData.keys():
                        detailData['artwork_literature'] = infopart
                        detailData['artwork_literature'] = self.__class__.htmltagPattern.sub("", detailData['artwork_literature'])
                        detailData['artwork_literature'] = detailData['artwork_literature'].replace('"', "'")
                        detailData['artwork_literature'] = detailData['artwork_literature'].replace('Literature:', "")
                        detailData['artwork_literature'] = detailData['artwork_literature'].replace(',', ";")
                        detailData['artwork_literature'] = beginspacePattern.sub("", detailData['artwork_literature'])
            ctr += 1
        imagesdivtags = soup.find_all("div", {'class' : 'zoomify'})
        if imagesdivtags.__len__() > 0:
            imagesdiv = imagesdivtags[0]
            imagesjson = imagesdiv['data-json']
            imagesjson = imagesjson.replace("&quot;", "'")
            imagesdata = json.loads(imagesjson)
            counter = 0
            altimages = []
            defaultimage = ""
            for imgdict in imagesdata:
                if counter == 0:
                    if 'hires' in imgdict.keys():
                        defaultimage = imgdict['hires']
                        defaultimage = defaultimage.replace("\/", "/")
                        defaultimage = self.baseUrl + defaultimage
                else:
                    if 'hires' in imgdict.keys():
                        altimg = imgdict['hires']
                        altimg = altimg.replace("\/", "/")
                        altimg = self.baseUrl + altimg
                        altimages.append(altimg)
                counter += 1
            imagename1 = self.getImagenameFromUrl(defaultimage)
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
            imagepathparts = defaultimage.split("/")
            defimageurl = "/".join(imagepathparts[:-2])
            encryptedFilename = str(encryptedFilename).replace("b'", "")
            encryptedFilename = str(encryptedFilename).replace("'", "")
            detailData['image1_name'] = str(encryptedFilename) + ".jpg"
            detailData['artwork_images1'] = defaultimage
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
                imgctr += 1
        detailData['auction_house_name'] = "DOROTHEUM"
        if 'artwork_markings' in detailData.keys():
            detailData['artwork_markings'] = detailData['artwork_markings'].replace('"', "'")
        if 'artwork_materials' in detailData.keys():
            detailData['artwork_materials'] = detailData['artwork_materials'].replace('"', "'")
        """
        metatags = soup.find_all("meta", {'name' : 'description'})
        if metatags.__len__() > 0:
            metacontent = metatags[0]['content']
            mps = re.search(nationalityPattern, metacontent)
            if mps:
                detailData['artist_nationality'] = mps.groups()[0]
        """
        descdivtags = soup.find_all("div", {'class' : 'bodytext-html'})
        detailData['artwork_description'] = ""
        desclist = []
        for descdivtag in descdivtags:
            descdivcontents = descdivtag.renderContents().decode('utf-8')
            descdivcontents = descdivcontents.replace("\n", "").replace("\r", "")
            descdivcontents = self.__class__.htmltagPattern.sub("", descdivcontents)
            desclist.append(descdivcontents)
        detailData['artwork_description'] = " ".join(desclist)
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
        baseUrl = "https://www.dorotheum.com"
        info = []
        endSpacePattern = re.compile("\s+$", re.DOTALL)
        enddotPattern = re.compile("\.\s*$")
        for htmlli in htmlList:
            data = {}
            data['auction_num'] = self.saleno
            htmlContent = htmlli.renderContents().decode('utf-8')
            s = BeautifulSoup(htmlContent, features="html.parser")
            allanchors = s.find_all("a")
            htmlanchor = allanchors[0]
            detailUrl = baseUrl + htmlanchor['href']
            data['lot_origin_url'] = detailUrl
            allparas = s.find_all("p")
            lotnoPattern = re.compile("Lot\s+No\.\s+(\d+)", re.IGNORECASE|re.DOTALL)
            estimatePattern = re.compile("(\w{3})\s+([\d,]+)\.?\-\s+to\s+\w{3}\s+([\d,]+)\.?", re.DOTALL)
            datePattern = re.compile("(\d{1,2})\.(\d{1,2})\.(\d{4})\s+\-\s+\d{2}\:\d{2}", re.DOTALL)
            soldpricePattern = re.compile("\w+\s+price:\s*(\w{3})\s+([\d\.,]+)\.?", re.IGNORECASE|re.DOTALL)
            lotno = ""
            for paratag in allparas:
                para = paratag.renderContents().decode('utf-8')
                para = self.__class__.htmltagPattern.sub("", para)
                para = para.replace("\n", "").replace("\r", "")
                lps = re.search(lotnoPattern, para)
                if lps:
                    lotno = lps.groups()[0]
                    data['lot_num'] = lotno
                eps = re.search(estimatePattern, para)
                if eps:
                    epsg = eps.groups()
                    currency = epsg[0]
                    lowestimate = epsg[1]
                    highestimate = epsg[2]
                    data['price_estimate_min'] = lowestimate
                    data['price_estimate_max'] = highestimate
                dps = re.search(datePattern, para)
                if dps:
                    dpsg = dps.groups()
                    dd = dpsg[0]
                    mm = dpsg[1]
                    yyyy = dpsg[2]
                    data['auction_start_date'] = mm + "/" + dd + "/" + yyyy
                sps = re.search(soldpricePattern, para)
                if sps:
                    spsg = sps.groups()
                    currency = spsg[0]
                    soldprice = spsg[1]
                    data['price_sold'] = soldprice
                    print(data['price_sold'])
            artisth3 = s.find_all("h3", {'class' : 'headline'})
            if artisth3.__len__() > 0:
                artistcontent = artisth3[0].renderContents().decode('utf-8')
                artistcontent = artistcontent.replace("\n", "").replace("\r", "").replace(" *", "")
                data['artist_name'] = artistcontent
            #print(data['lot_num'] + " ## " + data['artist_name'] + " ## " + data['auction_start_date'])
            print("Getting '%s'..."%data['lot_origin_url'])
            detailsPageContent = self.getDetailsPage(detailUrl)
            detailData = self.parseDetailPage(detailsPageContent, lotno, imagepath, data['artist_name'], downloadimages)
            for k in detailData.keys():
                data[k] = detailData[k]
            if 'price_sold' not in data.keys() or data['price_sold'] == "":
                data['price_sold'] = ""
            withdrawnPattern = re.compile("withdrawn", re.IGNORECASE|re.DOTALL)
            data['price_kind'] = "unknown"
            if ('price_sold' in data.keys() and re.search(withdrawnPattern, data['price_sold'])) or ('price_estimate_max' in data.keys() and  re.search(withdrawnPattern, data['price_estimate_max'])):
                data['price_kind'] = "withdrawn"
            elif 'price_sold' in data.keys() and 'price_sold' in data.keys() and data['price_sold'] != "":
                data['price_kind'] = "price realized"
            elif 'price_estimate_max' in data.keys() and data['price_estimate_max'] != "":
                data['price_kind'] = "estimate"
            else:
                pass
            if 'price_sold' in data.keys():
                data['price_sold'] = enddotPattern.sub("", data['price_sold'])
            data['auction_name'] = self.auctiontitle
            if not 'auction_start_date' in data.keys() or data['auction_start_date'] == "": 
                data['auction_start_date'] = self.auctiondate
            data['auction_location'] = self.auctionlocation
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
    pageurl = "http://216.137.189.57:8080/scrapers/finish/?scrapername=Dorotheum&auctionnumber=%s&auctionurl=%s&scrapertype=2"%(auctionno, urllib.parse.quote(auctionurl))
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
    dorotheum = DorotheumBot(auctionurl, auctionnumber)
    fp = open(csvpath, "w")
    fieldnames = ['auction_house_name', 'auction_location', 'auction_num', 'auction_start_date', 'auction_end_date', 'auction_name', 'lot_num', 'sublot_num', 'price_kind', 'price_estimate_min', 'price_estimate_max', 'price_sold', 'artist_name', 'artist_birth', 'artist_death', 'artist_nationality', 'artwork_name', 'artwork_year_identifier', 'artwork_start_year', 'artwork_end_year', 'artwork_materials', 'artwork_category', 'artwork_markings', 'artwork_edition', 'artwork_description', 'artwork_measurements_height', 'artwork_measurements_width', 'artwork_measurements_depth', 'artwork_size_notes', 'auction_measureunit', 'artwork_condition_in', 'artwork_provenance', 'artwork_exhibited', 'artwork_literature', 'artwork_images1', 'artwork_images2', 'artwork_images3', 'artwork_images4', 'artwork_images5', 'image1_name', 'image2_name', 'image3_name', 'image4_name', 'image5_name', 'lot_origin_url']
    fieldsstr = ",".join(fieldnames)
    fp.write(fieldsstr + "\n")
    pagectr = 1
    soup = BeautifulSoup(dorotheum.currentPageContent, features="html.parser")
    lotsdata = dorotheum.getLotsFromPage()
    info = dorotheum.getInfoFromLotsData(lotsdata, imagepath, downloadimages)
    lotctr = 0 
    for d in info:
        lotctr += 1
        for f in fieldnames:
            if f in d and d[f] is not None:
                fp.write('"' + str(d[f]) + '",')
            else:
                fp.write('"",')
        fp.write("\n")
    fp.close()
    updatestatus(auctionnumber, auctionurl)

# Example: python dorotheum.py https://www.dorotheum.com/en/a/78262/ 78262 /home/supmit/work/art2/dorotheum_78262.csv /home/supmit/work/art2/images/dorotheum/78262 0 0

# Example: python dorotheum.py https://www.dorotheum.com/en/a/78298/ 78298 /home/supmit/work/art2/dorotheum_78298.csv /home/supmit/work/art2/images/dorotheum/78298 0 0

# supmit

