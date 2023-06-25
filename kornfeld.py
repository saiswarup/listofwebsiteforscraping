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


class KornfeldBot(object):
    
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
        #self.requestUrl = self.__class__.startUrl
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
                    print ("Error 1: %s"%sys.exc_info()[1].__str__())
                    sys.exit()
        except:
            print ("Error 2: %s"%sys.exc_info()[1].__str__())
            sys.exit()
        self.httpHeaders["Referer"] = self.requestUrl
        self.sessionCookies = self.__class__._getCookieFromResponse(self.pageResponse)
        self.httpHeaders["Cookie"] = self.sessionCookies
        # Initialize the account related variables...
        self.currentPageContent = self.__class__._decodeGzippedContent(self.getPageContent())
        self.currentPageNumber = 1 # Page number of the page that is currently being read.
        self.data = {'auction_house_name': '', 'auction_location' : '', 'auction_num' : '', 'auction_start_date' : '', 'auction_end_date' : '', 'auction_name' : '', 'lot_num' : '', 'sublot_num' : '', 'price_kind' : '', 'price_estimate_min' : '', 'price_estimate_max' : '', 'price_sold' : '', 'artist_name' : '', 'artist_birth' : '', 'artist_death' : '', 'artist_nationality' : '', 'artwork_name' : '', 'artwork_year_identifier' : '', 'artwork_start_year' : '', 'artwork_end_year' : '', 'artwork_materials' : '', 'artwork_category' : '', 'artwork_markings' : '', 'artwork_edition' : '', 'artwork_description' : '', 'artwork_measurements_height' : '', 'artwork_measurements_width' : '', 'artwork_measurements_depth' : '', 'artwork_size_notes' : '', 'auction_measureunit' : '', 'artwork_condition_in' : '', 'artwork_provenance' : '', 'artwork_exhibited' : '', 'artwork_literature' : '', 'artwork_images1' : '', 'artwork_images2' : '', 'artwork_images3' : '', 'artwork_images4' : '', 'artwork_images5' : '', 'image1_name' : '', 'image2_name' : '', 'image3_name' : '', 'image4_name' : '', 'image5_name' : '', 'lot_origin_url' : ''}
        self.saleno = auctionnumber
        self.aid = ""
        auctionnumberPattern = re.compile("(\d+)\.html$")
        aps = re.search(auctionnumberPattern, auctionurl)
        if aps:
            self.aid = str(aps.groups()[0])
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
        try:
            decoded_content = decoded_content.decode('utf-8')
        except:
            try:
                decoded_content = decoded_content.decode('latin-1')
            except:
                decoded_content = ""
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
        alldivtags = soup.find_all("div", {'class' : 'headheadlinekatalog'})
        if alldivtags.__len__() > 0:
            title = alldivtags[0].renderContents().decode('utf-8')
            beginspacePattern = re.compile("^\s+")
            endspacePattern = re.compile("\s+$")
            title = self.__class__.htmltagPattern.sub("", title)
            titleparts = title.split("&nbsp;")
            if titleparts.__len__() > 0:
                title = titleparts[0]
            title = beginspacePattern.sub("", title)
            title = endspacePattern.sub("", title)
            self.auctiontitle = title
        idPattern = re.compile("li" + self.aid)
        lotblocks = soup.find_all("li", {'id' : idPattern})
        return lotblocks


    def getDetailsPage(self, detailUrl):
        #detailUrl = u''.join(detailUrl.split()).encode('utf-8')
        #self.requestUrl = detailUrl.decode('utf-8')
        detailUrl = u''.join(detailUrl.split()).encode('ascii', 'ignore').decode('ascii')
        self.requestUrl = detailUrl
        self.pageRequest = urllib.request.Request(self.requestUrl, headers=self.httpHeaders)
        self.pageResponse = None
        self.postData = {}
        try:
            self.pageResponse = self.opener.open(self.pageRequest)
        except:
            print ("Error 3: %s"%sys.exc_info()[1].__str__())
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
        baseUrl = "https://www.kornfeld.ch"
        detailData = {}
        soup = BeautifulSoup(detailsPage, features="html.parser")
        signedPattern = re.compile("Signature", re.IGNORECASE|re.DOTALL)
        editionPattern = re.compile("edition", re.IGNORECASE|re.DOTALL)
        sizePattern1 = re.compile("([\d,\.]+\s*x\s*[\d,\.]+\s*x\s*[\d,\.]+\s*cm)", re.IGNORECASE|re.DOTALL)
        sizePattern2 = re.compile("([\d,]+\s*x\s*[\d,]+\s*cm)", re.IGNORECASE|re.DOTALL)
        sizePattern3 = re.compile("([\d,]+\s*cm)", re.IGNORECASE|re.DOTALL)
        sheetsizePattern = re.compile("([\d,]+\s*x\s*[\d,]+\s*cm),\s+Blattgrösse", re.IGNORECASE|re.DOTALL)
        auctiondatePattern = re.compile("Sale\s+time\s+(\d{1,2}\-\d{1,2}\-\d{4})", re.IGNORECASE|re.DOTALL)
        catraisonnePattern = re.compile("Catalogue\s+Raisonné", re.IGNORECASE|re.DOTALL)
        provenancePattern = re.compile("Provenance", re.IGNORECASE|re.DOTALL)
        literaturePattern = re.compile("Literature", re.IGNORECASE|re.DOTALL)
        exhibitionPattern = re.compile("Exhibition", re.IGNORECASE|re.DOTALL)
        birthdeathPattern = re.compile("(\d{4})\s*\-\s*(\d{4})", re.DOTALL)
        showlargePattern = re.compile("showlarge\('([^']+)'\)", re.IGNORECASE|re.DOTALL)
        beginspacePattern = re.compile("^\s+")
        measureunitPattern = re.compile("([a-zA-Z]{2})")
        adps = re.search(auctiondatePattern, detailsPage)
        if adps:
            adpsg = adps.groups()
            self.auctiondate = adpsg[0]
        alldivtags = soup.find_all("div", {'class' : 'DIV7111details'})
        if alldivtags.__len__() > 0:
            divcontent = alldivtags[0].renderContents().decode('utf-8')
            zps1 = re.search(sizePattern1, divcontent)
            if zps1:
                zpsg1 = zps1.groups()
                detailData['artwork_size_notes'] = zpsg1[0]
            zps2 = re.search(sizePattern2, divcontent)
            if zps2 and 'artwork_size_notes' not in detailData.keys():
                zpsg2 = zps2.groups()
                detailData['artwork_size_notes'] = zpsg2[0]
            zps3 = re.search(sizePattern3, divcontent)
            if zps3 and 'artwork_size_notes' not in detailData.keys():
                zpsg3 = zps3.groups()
                detailData['artwork_size_notes'] = zpsg3[0]
            szps = re.search(sheetsizePattern, divcontent)
            if szps and 'SHEETSIZE' not in detailData.keys():
                szpsg = szps.groups()
                detailData['SHEETSIZE'] = szpsg[0]
        if 'artwork_size_notes' in detailData.keys():
            detailData['artwork_size_notes'] = detailData['artwork_size_notes'].replace(",", ".")
            detailData['artwork_size_notes'] = detailData['artwork_size_notes'].replace("x", " x ")
        if 'SHEETSIZE' in detailData.keys():
            detailData['SHEETSIZE'] = detailData['SHEETSIZE'].replace(",", ".")
            detailData['SHEETSIZE'] = detailData['SHEETSIZE'].replace("x", " x ")
        bdps = re.search(birthdeathPattern, detailsPage)
        if bdps:
            birthdate = bdps.groups()[0]
            deathdate = bdps.groups()[1]
            detailData['artist_birth'] = birthdate
            detailData['artist_death'] = deathdate
        allh5tags = soup.find_all("h5")
        for h5tag in allh5tags:
            h5content = h5tag.renderContents().decode('utf-8')
            sps = re.search(signedPattern, h5content)
            if sps:
                ptag = h5tag.findNext("p")
                detailData['artwork_markings'] = ptag.renderContents().decode('utf-8')
                detailData['artwork_markings'] = detailData['artwork_markings'].replace('"', "'")
                detailData['artwork_markings'] = detailData['artwork_markings'].replace('\n', "").replace("\r", "")
            rps = re.search(catraisonnePattern, h5content)
            if rps:
                ptag = h5tag.findNext("p")
                detailData['CATALOGRAISIONNE'] = ptag.renderContents().decode('utf-8')
                detailData['CATALOGRAISIONNE'] = detailData['CATALOGRAISIONNE'].replace('"', "'")
                detailData['CATALOGRAISIONNE'] = detailData['CATALOGRAISIONNE'].replace('\n', "").replace("\r", "")
            pps = re.search(provenancePattern, h5content)
            if pps:
                ptag = h5tag.findNext("p")
                detailData['artwork_provenance'] = ptag.renderContents().decode('utf-8')
                detailData['artwork_provenance'] = detailData['artwork_provenance'].replace('"', "'")
                detailData['artwork_provenance'] = detailData['artwork_provenance'].replace('\n', "").replace("\r", "")
            lps = re.search(literaturePattern, h5content)
            if lps:
                ptag = h5tag.findNext("p")
                detailData['artwork_literature'] = ptag.renderContents().decode('utf-8')
                detailData['artwork_literature'] = detailData['artwork_literature'].replace('"', "'")
                detailData['artwork_literature'] = detailData['artwork_literature'].replace('\n', "").replace("\r", "")
            eps = re.search(exhibitionPattern, h5content)
            if eps:
                ptag = h5tag.findNext("p")
                detailData['artwork_exhibited'] = ptag.renderContents().decode('utf-8')
                detailData['artwork_exhibited'] = detailData['artwork_exhibited'].replace('"', "'")
                detailData['artwork_exhibited'] = detailData['artwork_exhibited'].replace('\n', "").replace("\r", "")
        auctiondateparts = self.auctiondate.split("-")
        if auctiondateparts.__len__() > 2:
            auctiondate = auctiondateparts[1] + "/" + auctiondateparts[0] + "/" + auctiondateparts[2]
            self.auctiondate = auctiondate
            detailData['auction_start_date'] = self.auctiondate
        detailData['auction_house_name'] = "KORNFELD"
        if 'artwork_size_notes' in detailData.keys():
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
        imgdivtags = soup.find_all("div", {'id' : 'DIVlotimgmob'})
        altimageurls = []
        defaultimgurl = ""
        if imgdivtags.__len__() > 0:
            allimages = imgdivtags[0].find_all("img")
            if allimages.__len__() > 0:
                defaultimg = allimages[0]
                defaultimgurl = defaultimg['src']
                """
                slps = re.search(showlargePattern, defaultshowlarge)
                if slps:
                    defaultimgurl = slps.groups()[0]
                """
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
        newname1 = self.saleno + "__" + processedArtistName + "__" + lotno + "_a"
        #encryptedFilename = self.encryptFilename(newname1)
        encryptedFilename = newname1
        imagepathparts = defaultimgurl.split("/")
        defimageurl = "/".join(imagepathparts[:-2])
        encryptedFilename = str(encryptedFilename).replace("b'", "")
        encryptedFilename = str(encryptedFilename).replace("'", "")
        detailData['image1_name'] = str(encryptedFilename) + ".jpg"
        detailData['artwork_images1'] = defaultimgurl
        allaltimages = soup.find_all("img", {'title' : 'Click to enlarge'})
        if allaltimages.__len__() > 0:
            nextimg = allaltimages[0]
            altimgurl = nextimg['src']
            altimageurls.append(altimgurl)
        if allaltimages.__len__() > 1:
            nextimg = allaltimages[1]
            altimgurl = nextimg['src']
            altimageurls.append(altimgurl)
        imgctr = 2
        if altimageurls.__len__() > 0:
            altimage2 = altimageurls[0]
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
        if altimageurls.__len__() > 1:
            altimage2 = altimageurls[1]
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
        if altimageurls.__len__() > 2:
            altimage2 = altimageurls[2]
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
        if altimageurls.__len__() > 3:
            altimage2 = altimageurls[3]
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
        descdivtags = soup.find_all("div", {'class' : 'DIV7111details'})
        if descdivtags.__len__() > 0:
            desccontents = descdivtags[0].renderContents().decode('utf-8')
            desccontents = desccontents.replace("\n", "").replace("\r", "")
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
        estimatetds = soup.find_all("td", {'class' : 'textalignright'})
        if estimatetds.__len__() > 0:
            prevtd = estimatetds[0].findPrevious("td")
            estimate = estimatetds[0].renderContents().decode('utf-8')
            estimate = estimate.replace("'", "")
            estimateparts = estimate.split("-")
            detailData['price_estimate_min'] = estimateparts[0]
            if estimateparts.__len__() > 1:
                detailData['price_estimate_max'] = estimateparts[1]
        hammerpricedivtags = soup.find_all("div", {'id' : 'DIVspeichern'})
        if hammerpricedivtags.__len__() > 0:
            hammercontent = hammerpricedivtags[0].renderContents().decode('utf-8')
            hammercontent = hammercontent.replace("\n", " ").replace("\r", " ")
            hammercontent = self.__class__.htmltagPattern.sub("", hammercontent)
            hammerPattern = re.compile("Hammer\s+price\s+(\w{3})\s+([\d\.'\,]+)", re.IGNORECASE|re.DOTALL)
            hps = re.search(hammerPattern, hammercontent)
            if hps:
                hpsg = hps.groups()
                currency = hpsg[0]
                soldprice = hpsg[1]
                soldprice = soldprice.replace("'", "")
                detailData['price_sold'] = soldprice
                #print(detailData['price_sold'])
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
        baseUrl = "https://www.kornfeld.ch"
        info = []
        endSpacePattern = re.compile("\s+$", re.DOTALL)
        soldpricePattern = re.compile("([\d\s\.,]+)\s+€")
        beginspacePattern = re.compile("^\s+")
        yeartoyearPattern = re.compile("(\d{4})\s*\-\s*(\d{4})")
        yearPattern = re.compile("(\d{4})")
        mediumPattern = re.compile("(gold)|(silver)|(brass)|(bronze)|(wood)|(porcelain)|(stone)|(marble)|(metal)|(steel)|(iron)|(glass)|(plexiglas)|(chromogenic)|(paper)|(canvas)|(masonite)|(newsprint)|(silkscreen)|(parchment)|(linen)|(inkjet)|(ink\s+jet)|(pigment)|(\stin\s)|(photogravure)|(^oil\s+)|(\s+panel\s+)|(terracotta)|(ivory)|(\s+oak\s+)|(^oak\s+)|(\s+oak$)|(alabaster)|(pencil)", re.DOTALL|re.IGNORECASE)
        nonenglishmediumPattern = re.compile("(crayon)|(encre)|(plume)|(plume\s+et\s+encre)|(papier)|(pastel)|(craie)|(gouachée)|(aquarelle)|(lithographique)|(plomb)|(huile)|(cuivre)|(toile)|(bronze)|(Plâtre)|(en\s+terre\s+de\s+faïence)", re.IGNORECASE|re.DOTALL)
        matcatdict_en = {}
        matcatdict_fr = {}
        #with open("docs/fineart_materials.csv", newline='') as mapfile:
        with open("/root/artwork/deploydirnew/docs/fineart_materials.csv", newline='') as mapfile:
            mapreader = csv.reader(mapfile, delimiter=",", quotechar='"')
            for maprow in mapreader:
                matcatdict_en[maprow[1]] = maprow[3]
                matcatdict_fr[maprow[2]] = maprow[3]
        mapfile.close()
        for htmlli in htmlList:
            data = {}
            data['auction_num'] = self.saleno
            lotno = ""
            htmlContent = htmlli.renderContents().decode('utf-8')
            s = BeautifulSoup(htmlContent, features="html.parser")
            allforms = s.find_all("form")
            detailUrl = ""
            artistname, artworkname = "", ""
            if allforms.__len__() > 0:
                htmlform = allforms[0]
                detailUrl = baseUrl + htmlform['action']
            else:
                continue
            data['lot_origin_url'] = detailUrl
            allparas = s.find_all("p")
            if allparas.__len__() > 0:
                lotnopara = allparas[0]
                lotno = lotnopara.renderContents().decode('utf-8')
                lotno = self.__class__.htmltagPattern.sub("", lotno)
                lotno = lotno.replace(" ", "").replace("\n", "").replace("\r", "")
                lotno = endSpacePattern.sub("", lotno)
            data['lot_num'] = lotno
            lotno = lotno.replace("*", "")
            data['lot_num'] = data['lot_num'].replace("*", "")
            allh3tags = s.find_all("h3")
            allh4tags = s.find_all("h4")
            if allh3tags.__len__() > 0:
                data['artist_name'] = allh3tags[0].renderContents().decode('utf-8')
                data['artist_name'] = data['artist_name'].replace("\n", "").replace("\r", "")
                data['artist_name'] = data['artist_name'].replace('"', "'")
                artistname = data['artist_name']
            if allh4tags.__len__() > 0:
                data['artwork_name'] = allh4tags[0].renderContents().decode('utf-8')
                data['artwork_name'] = data['artwork_name'].replace("\n", "").replace("\r", "")
                data['artwork_name'] = data['artwork_name'].replace('"', "'")
                artworkname = data['artwork_name']
                nextptag = allh4tags[0].findNext("p")
                if nextptag:
                    yearfrom = nextptag.renderContents().decode('utf-8')
                    y2ys = re.search(yeartoyearPattern, yearfrom)
                    if y2ys:
                        data['artwork_start_year'] = y2ys.groups()[0]
                        data['artwork_end_year'] = y2ys.groups()[1]
                    else:
                        yps = re.search(yearPattern, yearfrom)
                        if yps:
                            data['artwork_start_year'] = yps.groups()[0]
                    mediumptag = nextptag.findNext("p")
                    if mediumptag:
                        data['artwork_materials'] = mediumptag.renderContents().decode('utf-8')
                        data['artwork_materials'] = data['artwork_materials'].replace("\n", "").replace("\r", "")
                        data['artwork_materials'] = data['artwork_materials'].replace('"', "'")
                    else: # Perhaps the last p tag was medium information...
                        mps = re.search(mediumPattern, yearfrom)
                        if mps:
                            data['artwork_materials'] = yearfrom
                            data['artwork_materials'] = data['artwork_materials'].replace("\n", "").replace("\r", "")
                            data['artwork_materials'] = data['artwork_materials'].replace('"', "'")
                        else:
                            pass
            """
            try:
                print(data['lot_num'] + " ## " + data['artist_name'] + " ## " + data['artwork_name'] + " ## " + data['artwork_start_year'] + " ## " + data['Martwork_materials'])
            except:
                print(data['lot_num'] + " ================================ ")
            """
            print("Getting '%s'..."%data['lot_origin_url'])
            detailsPageContent = self.getDetailsPage(detailUrl)
            if not lotno:
                continue
            detailData = self.parseDetailPage(detailsPageContent, lotno, imagepath, artistname, artworkname, downloadimages)
            for k in detailData.keys():
                data[k] = detailData[k]
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
            if 'price_sold' not in data.keys() or data['price_sold'] == "":
                data['price_sold'] = ""
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
            data['auction_name'] = self.auctiontitle
            data['auction_name'] = data['auction_name'].replace("\n", "").replace("\r", "")
            data['auction_name'] = data['auction_name'].replace('"', "'")
            data['auction_location'] = "Bern, Switzerland"
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
    pageurl = "http://216.137.189.57:8080/scrapers/finish/?scrapername=Kornfeld&auctionnumber=%s&auctionurl=%s&scrapertype=2"%(auctionno, urllib.parse.quote(auctionurl))
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
    kornfeld = KornfeldBot(auctionurl, auctionnumber)
    fp = open(csvpath, "w")
    fieldnames = ['auction_house_name', 'auction_location', 'auction_num', 'auction_start_date', 'auction_end_date', 'auction_name', 'lot_num', 'sublot_num', 'price_kind', 'price_estimate_min', 'price_estimate_max', 'price_sold', 'artist_name', 'artist_birth', 'artist_death', 'artist_nationality', 'artwork_name', 'artwork_year_identifier', 'artwork_start_year', 'artwork_end_year', 'artwork_materials', 'artwork_category', 'artwork_markings', 'artwork_edition', 'artwork_description', 'artwork_measurements_height', 'artwork_measurements_width', 'artwork_measurements_depth', 'artwork_size_notes', 'auction_measureunit', 'artwork_condition_in', 'artwork_provenance', 'artwork_exhibited', 'artwork_literature', 'artwork_images1', 'artwork_images2', 'artwork_images3', 'artwork_images4', 'artwork_images5', 'image1_name', 'image2_name', 'image3_name', 'image4_name', 'image5_name', 'lot_origin_url']
    fieldsstr = ",".join(fieldnames)
    fp.write(fieldsstr + "\n")
    baseUrl = "https://www.kornfeld.ch"
    pagectr = 1
    while True:
        soup = BeautifulSoup(kornfeld.currentPageContent, features="html.parser")
        lotsdata = kornfeld.getLotsFromPage()
        if lotsdata.__len__() == 0:
            break
        info = kornfeld.getInfoFromLotsData(lotsdata, imagepath, downloadimages)
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
        nextpageUrl = ""
        pageultag = soup.find_all("ul", {'class' : 'ULbutton'})
        if pageultag.__len__() > 0:
            chosenanchortags = pageultag[0].find_all("a", {'class' : 'chosen'})
            if chosenanchortags.__len__() > 0:
                nextanchortag = chosenanchortags[0].findNext("a")
                if nextanchortag:
                    nextpageUrl = baseUrl + nextanchortag['href']
        if not nextpageUrl or nextpageUrl == "#":
            break
        kornfeld.pageRequest = urllib.request.Request(nextpageUrl, headers=kornfeld.httpHeaders)
        try:
            kornfeld.pageResponse = kornfeld.opener.open(kornfeld.pageRequest)
        except:
            print("Couldn't find the page %s"%str(pagectr))
            break
        kornfeld.currentPageContent = kornfeld.__class__._decodeGzippedContent(kornfeld.getPageContent())
    fp.close()
    updatestatus(auctionnumber, auctionurl)

# Example: python kornfeld.py https://www.kornfeld.ch/g365/a4001.html a4001 /home/supmit/work/art2/kornfeld_a4001.csv /home/supmit/work/art2/images/kornfeld/a4001 0 0

# supmit

