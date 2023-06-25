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


class ImkinskyBot(object):
    
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
        self.auctionstate = "online-catalogue"



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
            return self.pageResponse.read()
        except:
            return b""

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
        titledivtags = soup.find_all("div", {'id' : 'block-ikt-page-title'})
        if titledivtags.__len__() > 0:
            h1tags = titledivtags[0].find_all("h1")
            if h1tags.__len__() > 0:
                self.auctiontitle = h1tags[0].renderContents().decode('utf-8')
        ultags = soup.find_all("ul", {'class' : 'nostyle'})
        lotblocks = []
        if ultags.__len__() > 0:
            lotblocks = ultags[0].find_all("li")
        return lotblocks
        

    def getDetailsPage(self, detailUrl):
        self.requestUrl = detailUrl
        self.pageRequest = urllib.request.Request(self.requestUrl, headers=self.httpHeaders)
        self.pageResponse = None
        self.postData = {}
        try:
            self.pageResponse = self.opener.open(self.pageRequest)
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
        baseUrl = "https://imkinsky.com"
        detailData = {}
        soup = BeautifulSoup(detailsPage, features="html.parser")
        mediumPattern = re.compile("(gold)|(silver)|(brass)|(bronze)|(\s+wood\s+)|(^wood\s+)|(\s+wood$)|(porcelain)|(stone)|(marble)|(metal)|(steel)|(iron)|(glass)|(plexiglas)|(chromogenic)|(paper)|(canvas)|(masonite)|(newsprint)|(silkscreen)|(parchment)|(linen)|(inkjet)|(ink\s+jet)|(pigment)|(\stin\s)|(photogravure)|(^oil\s+)|(\s+panel\s+)|(terracotta)|(ivory)|(\s+oak\s+)|(^oak\s+)|(\s+oak$)|(alabaster)|(lithograph)|(varnish)|(mixed\s+media)|(paintbrush)|(enamel)", re.DOTALL|re.IGNORECASE)
        nonenglishmediumPattern = re.compile("(crayon)|(encre)|(plume)|(plume\s+et\s+encre)|(papier)|(pastel)|(craie)|(gouachée)|(aquarelle)|(lithographique)|(plomb)|(huile)|(cuivre)|(toile)|(bronze)|(Plâtre)|(en\s+terre\s+de\s+faïence)", re.IGNORECASE|re.DOTALL)
        signedPattern = re.compile("signed", re.IGNORECASE)
        signedPattern2 = re.compile("label\s+on", re.IGNORECASE)
        editionPattern = re.compile("edition", re.IGNORECASE)
        sizePattern = re.compile("(Haut\.?\s*\d+\s*cm)", re.IGNORECASE)
        sizePattern2 = re.compile("([\d,\.]+\s*x\s*[\d,\.]+\s*cm)", re.IGNORECASE)
        sizePattern3 = re.compile("([\d,]+\s*cm)", re.IGNORECASE)
        birthdeathPattern = re.compile("(\d{4})\s*\-?\s*(\d{0,4})")
        provenancePattern = re.compile("provenance", re.IGNORECASE|re.DOTALL)
        literaturePattern = re.compile("literature", re.IGNORECASE|re.DOTALL)
        exhibitionPattern = re.compile("exhibition", re.IGNORECASE|re.DOTALL)
        yearPattern = re.compile("^(\d{4})$")
        beginspacePattern = re.compile("^\s+")
        brPattern = re.compile("<br\s*\/?>", re.IGNORECASE|re.DOTALL)
        measureunitPattern = re.compile("([a-zA-Z]{2})")
        matcatdict_en = {}
        matcatdict_fr = {}
        #with open("docs/fineart_materials.csv", newline='') as mapfile:
        with open("/Users/saiswarupsahu/freelanceprojectchetan/docs/fineart_materials.csv", newline='') as mapfile:
            mapreader = csv.reader(mapfile, delimiter=",", quotechar='"')
            for maprow in mapreader:
                matcatdict_en[maprow[1]] = maprow[3]
                matcatdict_fr[maprow[2]] = maprow[3]
        mapfile.close()
        auctiondateparatags = soup.find_all("p", {'class' : 'intro'})
        if auctiondateparatags.__len__() > 0:
            auctiondatecontents = auctiondateparatags[0].renderContents().decode()
            auctiondatecontents = self.__class__.htmltagPattern.sub("", auctiondatecontents)
            auctiondatecontents = auctiondatecontents.replace("\n", "").replace("\r", "").replace(".", "")
            auctiondateparts = auctiondatecontents.split(",")
            if auctiondateparts.__len__() > 0:
                auctiondate = auctiondateparts[0]
                self.auctiondate = auctiondate
                detailData['auction_start_date'] = self.__class__.formatDate(auctiondate)
        artistdivtags = soup.find_all("div", {'class' : 'artist'})
        if artistdivtags.__len__() > 0:
            artistdivcontents = artistdivtags[0].renderContents().decode('utf-8')
            artistdivcontents = self.__class__.htmltagPattern.sub("", artistdivcontents)
            artistdivcontents = artistdivcontents.replace("\n", "").replace("\r", "")
            bdps = re.search(birthdeathPattern, artistdivcontents)
            if bdps:
                bdpsg = bdps.groups()
                detailData['artist_birth'] = bdpsg[0]
                detailData['artist_death'] = bdpsg[1]
            nextptag = artistdivtags[0].find_next_sibling("p")
            if nextptag:
                nextpcontent = nextptag.renderContents().decode('utf-8')
                nextpparts = re.split(brPattern, nextpcontent)
                for ppart in nextpparts:
                    mps = re.search(mediumPattern, ppart)
                    if mps and 'artwork_materials' not in detailData.keys():
                        detailData['artwork_materials'] = ppart
                        detailData['artwork_materials'] = detailData['artwork_materials'].replace("\n", "").replace("\r", "")
                        detailData['artwork_materials'] = detailData['artwork_materials'].replace('"', "'")
                        detailData['artwork_materials'] = detailData['artwork_materials'].replace('„', "'")
                        detailData['artwork_materials'] = detailData['artwork_materials'].replace('“', "'")
                        mediumparts = detailData['artwork_materials'].split(";")
                        detailData['artwork_materials'] = mediumparts[0]
                    nemps = re.search(nonenglishmediumPattern, ppart)
                    if nemps and 'artwork_materials' not in detailData.keys():
                        detailData['artwork_materials'] = ppart
                        detailData['artwork_materials'] = detailData['artwork_materials'].replace("\n", "").replace("\r", "")
                        detailData['artwork_materials'] = detailData['artwork_materials'].replace('"', "'")
                        detailData['artwork_materials'] = detailData['artwork_materials'].replace('„', "'")
                        detailData['artwork_materials'] = detailData['artwork_materials'].replace('“', "'")
                        mediumparts = detailData['artwork_materials'].split(";")
                        detailData['artwork_materials'] = mediumparts[0]
                    zps = re.search(sizePattern, ppart)
                    if zps and 'artwork_size_notes' not in detailData.keys():
                        detailData['artwork_size_notes'] = zps.groups()[0]
                        mups = re.search(measureunitPattern, detailData['artwork_size_notes'])
                        if mups:
                            detailData['auction_measureunit'] = mups.groups()[0]
                            detailData['artwork_measurements_height'] = detailData['artwork_size_notes']
                    zps2 = re.search(sizePattern2, ppart)
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
                        if sizeparts.__len__() > 2:
                            mups = re.search(measureunitPattern, sizeparts[2])
                            if mups:
                                detailData['auction_measureunit'] = mups.groups()[0]
                                sizeparts[2] = measureunitPattern.sub("", sizeparts[2])
                            detailData['artwork_measurements_depth'] = sizeparts[2]
                    zps3 = re.search(sizePattern3, ppart)
                    if zps3 and 'artwork_size_notes' not in detailData.keys():
                        detailData['artwork_size_notes'] = zps3.groups()[0]
                        mups = re.search(measureunitPattern, detailData['artwork_size_notes'])
                        if mups:
                            detailData['auction_measureunit'] = mups.groups()[0]
                            detailData['artwork_measurements_height'] = detailData['artwork_size_notes']
                            detailData['artwork_measurements_height'] = measureunitPattern.sub("", detailData['artwork_measurements_height'])
                    sps = re.search(signedPattern, ppart)
                    if sps and 'artwork_markings' not in detailData.keys():
                        detailData['artwork_markings'] = ppart
                        detailData['artwork_markings'] = detailData['artwork_markings'].replace('"', "'")
                        detailData['artwork_markings'] = detailData['artwork_markings'].replace("\n", "").replace("\r", "")
                    sps2 = re.search(signedPattern2, ppart)
                    if sps2 and 'artwork_markings' not in detailData.keys():
                        detailData['artwork_markings'] = ppart
                        detailData['artwork_markings'] = detailData['artwork_markings'].replace('"', "'")
                        detailData['artwork_markings'] = detailData['artwork_markings'].replace("\n", "").replace("\r", "")
                    yps = re.search(yearPattern, ppart)
                    if yps and 'artwork_start_year' not in detailData.keys():
                        detailData['artwork_start_year'] = yps.groups()[0]
                nexth3 = nextptag.find_next_sibling("h3")
                if nexth3:
                    h3contents = nexth3.renderContents().decode('utf-8')
                    if re.search(provenancePattern, h3contents):
                        provptag = nextptag.find_next_sibling("p")
                        if provptag:
                            provcontents = provptag.renderContents().decode('utf-8')
                            provcontents = self.__class__.htmltagPattern.sub("", provcontents)
                            provcontents = provcontents.replace("\n", "").replace("\r", "")
                            provcontents = provcontents.replace('"', "'")
                            detailData['artwork_provenance'] = provcontents
                    lith3tag = nexth3.find_next_sibling("h3")
                    if lith3tag:
                        lith3contents = lith3tag.renderContents().decode('utf-8')
                        lps = re.search(literaturePattern, lith3contents)
                        if lps:
                            litptag = lith3tag.find_next_sibling("p")
                            if litptag:
                                litcontents = litptag.renderContents().decode('utf-8')
                                litcontents = self.__class__.htmltagPattern.sub("", litcontents)
                                litcontents = litcontents.replace('"', "'")
                                litcontents = litcontents.replace("\n", " ").replace("\r", " ")
                                detailData['artwork_literature'] = litcontents
                    exhibitionh3tag = nexth3.find_next_sibling("h3")
                    if exhibitionh3tag:
                        exhibitionh3contents = exhibitionh3tag.renderContents().decode('utf-8')
                        xps = re.search(exhibitionPattern, exhibitionh3contents)
                        if xps:
                            exptag = exhibitionh3tag.find_next_sibling("p")
                            if exptag:
                                exhibitioncontents = exptag.renderContents().decode('utf-8')
                                exhibitioncontents = self.__class__.htmltagPattern.sub("", exhibitioncontents)
                                exhibitioncontents = exhibitioncontents.replace('"', "'")
                                exhibitioncontents = exhibitioncontents.replace("\n", " ").replace("\r", " ")
                                detailData['artwork_exhibited'] = exhibitioncontents
                        lith3tag = exhibitionh3tag.find_next_sibling("h3")
                        if lith3tag:
                            lith3contents = lith3tag.renderContents().decode('utf-8')
                            lps = re.search(literaturePattern, lith3contents)
                            if lps:
                                litptag = lith3tag.find_next_sibling("p")
                                if litptag:
                                    litpcontents = litptag.renderContents().decode('utf-8')
                                    litpcontents = self.__class__.htmltagPattern.sub("", litpcontents)
                                    litpcontents = litpcontents.replace('"', "'")
                                    litpcontents = litpcontents.replace("\n", " ").replace("\r", " ")
                                    detailData['artwork_literature'] = litpcontents
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
        detailData['auction_house_name'] = "IM KINKSY"
        imganchortags = soup.find_all("a", {'class' : 'lc_lightbox'})
        if imganchortags.__len__() > 0:
            defaultimgurl = imganchortags[0]['href']
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
        textdivtags = soup.find_all("div", {'class' : 'txt'})
        if textdivtags.__len__() > 0:
            desccontents = textdivtags[0].renderContents().decode('utf-8')
            detailData['artwork_description'] = desccontents
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
        if re.search(partialUrlPattern, imageUrl):
            imageUrl = "https://imkinsky.com" + imageUrl
        imageUrlParts = imageUrl.split("/")
        try:
            imagefilename = imageUrlParts[-2] + "_" + imageUrlParts[-1]
            imagedir = imageUrlParts[-2]
        except:
            imagefilename = "temp.jpg"
            imagedir = imageUrlParts[-1]
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
        baseUrl = "https://imkinsky.com"
        info = []
        endSpacePattern = re.compile("\s+$", re.DOTALL)
        yearPattern = re.compile("(\d{4})")
        endcommaPattern = re.compile(",\s*$")
        beginspacePattern = re.compile("^\s+")
        for htmlli in htmlList:
            data = {}
            data['auction_num'] = self.saleno
            lotno = ""
            detailUrl = ""
            data['artist_name'] = ""
            data['artwork_name'] = ""
            htmlContent = htmlli.renderContents().decode('utf-8')
            s = BeautifulSoup(htmlContent, features="html.parser")
            h2tags = s.find_all("h2")
            if h2tags.__len__() > 0:
                h2anchortags = h2tags[0].find_all("a")
                if h2anchortags.__len__() > 0:
                    detailUrl = baseUrl + h2anchortags[0]['href']
                    data['lot_origin_url'] = detailUrl
                h2content = h2tags[0].renderContents().decode('utf-8')
                h2content = self.__class__.htmltagPattern.sub("", h2content)
                lotno = h2content
                data['lot_num'] = lotno
            else:
                continue
            allparatags = s.find_all("p")
           
            if allparatags.__len__() > 0:# and allparatags[0]['class'] == 'b':
                artistname = allparatags[0].renderContents().decode('utf-8')
                artistname = self.__class__.htmltagPattern.sub("", artistname)
                data['artist_name'] = artistname
                data['artist_name'] = data['artist_name'].replace("*", "")
            if allparatags.__len__() > 1:
                title = allparatags[1].renderContents().decode('utf-8')
                data['artwork_name'] = title
                yps = re.search(yearPattern, title)
                if yps:
                    data['artwork_start_year'] = yps.groups()[0]
                    data['artwork_name'] = yearPattern.sub("", data['artwork_name'])
                    data['artwork_name'] = endcommaPattern.sub("", data['artwork_name'])
                data['artwork_name'] = data['artwork_name'].replace('"', "'")
                data['artwork_name'] = data['artwork_name'].replace('„', "'")
                data['artwork_name'] = data['artwork_name'].replace('“', "'")
                data['artwork_name'] = data['artwork_name'].replace("c.", "")
                data['artwork_name'] = endcommaPattern.sub("", data['artwork_name'])
            if allparatags.__len__() > 2:# and allparatags[2]['class'] == "price":
                pricecontent = allparatags[2].renderContents().decode('utf-8')
                pricecontent = self.__class__.htmltagPattern.sub("", pricecontent)
                pricecontent = pricecontent.replace("&nbsp;", " ").replace("▲", "")
                pricecontent = pricecontent.replace("€", "")
                pricecontent = pricecontent.replace("EUR", "")
                pricecontent = pricecontent + " EUR"
                pricecontent = beginspacePattern.sub("", pricecontent)
                pricecontent = pricecontent.replace(".", "")
                pricecontentparts = pricecontent.split(" - ")
                data['price_estimate_min'] = pricecontentparts[0]
                if pricecontentparts.__len__() > 1:
                    data['price_estimate_max'] = pricecontentparts[1]
            if self.auctionstate == 'auction-results':
                data['lot_origin_url'] = data['lot_origin_url'].replace("online-catalogue", "auction-results")
            print("Getting '%s'..."%data['lot_origin_url'])
            detailUrl = data['lot_origin_url']
            detailsPageContent = self.getDetailsPage(data['lot_origin_url'])
            if not lotno:
                continue
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
            data['auction_location'] = "Vienna"
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
    pageurl = "http://216.137.189.57:8080/scrapers/finish/?scrapername=Imkinsky&auctionnumber=%s&auctionurl=%s&scrapertype=2"%(auctionno, urllib.parse.quote(auctionurl))
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
    auctionnumber = sys.argv[2] # This would be something like 137_711_2
    auctionnumberparts = auctionnumber.split("_")
    mainnumber = auctionnumberparts[0] # This will be something like 137
    subnumber = auctionnumberparts[1] # This will be something like 711
    tailnumber = auctionnumberparts[2] # This would be 2
    auctionstate = "online-catalogue"
    if 'auction-results' in auctionurl:
        auctionstate = "auction-results"
    csvpath = sys.argv[3]
    imagepath = sys.argv[4]
    downloadimages = 0
    convertfractions = 0
    if sys.argv.__len__() > 5:
        downloadimages = sys.argv[5]
    if sys.argv.__len__() > 6:
        convertfractions = sys.argv[6]
    imkinsky = ImkinskyBot(auctionurl, auctionnumber)
    imkinsky.auctionstate = auctionstate
    fp = open(csvpath, "w")
    fieldnames = ['auction_house_name', 'auction_location', 'auction_num', 'auction_start_date', 'auction_end_date', 'auction_name', 'lot_num', 'sublot_num', 'price_kind', 'price_estimate_min', 'price_estimate_max', 'price_sold', 'artist_name', 'artist_birth', 'artist_death', 'artist_nationality', 'artwork_name', 'artwork_year_identifier', 'artwork_start_year', 'artwork_end_year', 'artwork_materials', 'artwork_category', 'artwork_markings', 'artwork_edition', 'artwork_description', 'artwork_measurements_height', 'artwork_measurements_width', 'artwork_measurements_depth', 'artwork_size_notes', 'auction_measureunit', 'artwork_condition_in', 'artwork_provenance', 'artwork_exhibited', 'artwork_literature', 'artwork_images1', 'artwork_images2', 'artwork_images3', 'artwork_images4', 'artwork_images5', 'image1_name', 'image2_name', 'image3_name', 'image4_name', 'image5_name', 'lot_origin_url']
    fieldsstr = ",".join(fieldnames)
    fp.write(fieldsstr + "\n")
    pagectr = 0
    pagehtml = imkinsky.currentPageContent
    pagehtml = pagehtml.replace("\\/", "/")
    viewargsPattern = re.compile("\"view_args\"\:\"(\d+)\/", re.DOTALL)
    vps = re.search(viewargsPattern, pagehtml)
    viewargs = "2490" # Default value
    if vps:
        viewargs = vps.groups()[0]
    while True:
        soup = BeautifulSoup(imkinsky.currentPageContent, features="html.parser")
        lotsdata = imkinsky.getLotsFromPage()
        if lotsdata.__len__() == 0:
            break
        info = imkinsky.getInfoFromLotsData(lotsdata, imagepath, downloadimages)
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
        # Set headers for the next page request
        headers = {}
        headers['accept'] = "application/json, text/javascript, */*; q=0.01"
        headers['accept-encoding'] = "gzip, deflate, br"
        headers['accept-language'] = "en-GB,en-US;q=0.9,en;q=0.8"
        headers['content-type'] = "application/x-www-form-urlencoded; charset=UTF-8"
        headers['cookie'] = "cookie-agreed-version=1.0.0; imkinsky_menu=closed; cookie-agreed=2"
        headers['origin'] = "https://imkinsky.com"
        headers['referer'] = "https://imkinsky.com/en/%s/%s/%s/%s"%(auctionstate, mainnumber, subnumber, tailnumber)
        headers['sec-fetch-dest'] = "empty"
        headers['sec-fetch-mode'] = "cors"
        headers['sec-fetch-site'] = "same-origin"
        headers['user-agent'] = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36"
        headers['x-requested-with'] = "XMLHttpRequest"
        # headers for next page request ends
        inputdict = {'view_name' : 'lot_overview', 'view_display_id' : 'online_catalogue', 'view_args' : '%s/%s/%s'%(viewargs, subnumber, tailnumber), 'view_path' : '/%s/%s/%s/%s'%(auctionstate, str(auctionnumber), str(subnumber), str(tailnumber)), 'view_dom_id' : '93709123125a083030eddf2b945f6b616fba60153d937463514286034f5e099e', 'pager_element' : '0', 'sort_by' : 'KatalogNr', 'page' : str(pagectr), '_drupal_ajax' : '1', 'ajax_page_state[theme]' : 'ikt', 'ajax_page_state[theme_token]' : '', 'ajax_page_state[libraries]' : 'argos/lot_form,classy/base,classy/messages,core/normalize,eu_cookie_compliance/eu_cookie_compliance_bare,ikm/lc_lightbox.dark,ikt/back_to_top,ikt/global-styling,select2/select2.i18n.en,system/base,views/views.module,views_infinite_scroll/views-infinite-scroll'}
        postdata = urlencode(inputdict, quote_via=quote_plus)
        headers['content-length'] = str(postdata.__len__())
        postdatabytes = bytes(postdata, 'utf-8')
        jsurl = "https://imkinsky.com/en/views/ajax?_wrapper_format=drupal_ajax"
        imkinsky.pageRequest = urllib.request.Request(jsurl, postdatabytes, headers=headers)
        try:
            imkinsky.pageResponse = imkinsky.opener.open(imkinsky.pageRequest)
        except:
            print("Couldn't find the page %s"%str(pagectr))
            break
        imkinsky.currentPageContent = imkinsky.__class__._decodeGzippedContent(imkinsky.getPageContent())
        imkinsky.currentPageContent = imkinsky.currentPageContent.replace("\\u003C", "<").replace("\\u003E", ">").replace("\\u0022", "'").replace("\\/", "/").replace("\\u0026", "&").replace("\\u20ac", "EUR") # last replace is replacing Euro sign directly to the string we need.
        #imkinsky.currentPageContent = imkinsky.currentPageContent.encode('utf-8')
        jsondata = json.loads(imkinsky.currentPageContent)
        if jsondata.__len__() > 1:
            jsondict = jsondata[1]
            if 'data' in jsondict.keys():
                imkinsky.currentPageContent = jsondict['data']
            else:
                imkinsky.currentPageContent = ""
        else:
            imkinsky.currentPageContent = ""
        #print(imkinsky.currentPageContent)
    fp.close()
    updatestatus(auctionnumber, auctionurl)

# Example: python imkinsky.py https://imkinsky.com/en/auction-results/128/663/2   128_663_2  /Users/saiswarupsahu/freelanceprojectchetan/imkinsky_128_663_2.csv /Users/saiswarupsahu/freelanceprojectchetan/1-5TNCV9 0 0

# supmit

