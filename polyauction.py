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


class PolyauctionBot(object):
    
    startUrl=r"https://www.polyauction.com.hk/auction-catalog/modern-art_OH64A0G02J?pageNum=1"
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
            beginspacePattern = re.compile("^\s+")
            endspacePattern = re.compile("\s+$")
            title = beginspacePattern.sub("", title)
            title = endspacePattern.sub("", title)
            titleparts = title.split("|")
            if titleparts.__len__() > 0:
                title = titleparts[0]
            else:
                pass
            self.auctiontitle = title
        alldateh3tags = soup.find_all("h3", {'class' : 'main-title'})
        if alldateh3tags.__len__() > 0:
            dateh3content = alldateh3tags[0].renderContents().decode('utf-8')
            datePattern = re.compile("(\d+\s+\w+\s+\d{4})", re.DOTALL)
            dps = re.search(datePattern, dateh3content)
            if dps:
                auctiondate = dps.groups()[0]
                self.auctiondate = auctiondate
        lotblocks = soup.find_all("div", {'class' : 'item entity'})
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
        baseUrl = "https://www.polyauction.com.hk"
        detailData = {}
        soup = BeautifulSoup(detailsPage, features="html.parser")
        mediumPattern = re.compile("(gold)|(silver)|(brass)|(bronze)|(wood)|(porcelain)|(stone)|(marble)|(metal)|(steel)|(iron)|(glass)|(plexiglas)|(chromogenic)|(paper)|(canvas)|(masonite)|(newsprint)|(silkscreen)|(parchment)|(linen)|(inkjet)|(ink\s+jet)|(pigment)|(\stin\s)|(photogravure)|(^oil\s+)|(\s+panel\s+)|(terracotta)|(ivory)|(\s+oak\s+)|(^oak\s+)|(\s+oak$)|(alabaster)", re.DOTALL|re.IGNORECASE)
        nonenglishmediumPattern = re.compile("(crayon)|(encre)|(plume)|(plume\s+et\s+encre)|(papier)|(pastel)|(craie)|(gouachée)|(aquarelle)|(lithographique)|(plomb)|(huile)|(cuivre)|(toile)|(bronze)|(Plâtre)|(en\s+terre\s+de\s+faïence)", re.IGNORECASE|re.DOTALL)
        signedPattern = re.compile("signed", re.IGNORECASE)
        signedPattern2 = re.compile("signature", re.IGNORECASE)
        editionPattern = re.compile("edition", re.IGNORECASE)
        sizePattern = re.compile("([\d,\.]+\s*x\s*[\d,\.]+\s*x\s*[\d,\.]+\s*cm)", re.IGNORECASE|re.DOTALL)
        sizePattern2 = re.compile("([\d,\.]+\s*x\s*[\d,\.]+\s*cm)", re.IGNORECASE|re.DOTALL)
        sizePattern3 = re.compile("([\d,\.]+\s*cm)", re.IGNORECASE|re.DOTALL)
        provenancePattern = re.compile("provenance", re.IGNORECASE|re.DOTALL)
        beginspacePattern = re.compile("^\s+")
        endspacePattern = re.compile("\s+$")
        yearPattern = re.compile("(\d{4})")
        measureunitPattern = re.compile("([a-zA-Z]{2})")
        matcatdict_en = {}
        matcatdict_fr = {}
        #with open("docs/fineart_materials.csv", newline='') as mapfile:
        with open("/root/artwork/deploydirnew/docs/fineart_materials.csv", newline='') as mapfile:
            mapreader = csv.reader(mapfile, delimiter=",", quotechar='"')
            for maprow in mapreader:
                matcatdict_en[maprow[1]] = maprow[3]
                matcatdict_fr[maprow[2]] = maprow[3]
        mapfile.close()
        basiclotdivtags = soup.find_all("div", {'class' : 'lot-basic-information-secondary'})
        if basiclotdivtags.__len__() > 0:
            allcontentdivtags = basiclotdivtags[0].find_all("div", {'class' : 'contents'})
            ctr = 0
            for contentdivtag in allcontentdivtags:
                divcontents = contentdivtag.renderContents().decode('utf-8')
                divcontents = divcontents.replace("\n", " ").replace("\r", "")
                divcontents = beginspacePattern.sub("", divcontents)
                divcontents = endspacePattern.sub("", divcontents)
                divcontents = divcontents.replace('"', "'")
                divcontents = divcontents.replace("×", "x")
                divcontents = divcontents.replace("㎝", "cm")
                if ctr == 0:
                    yps = re.search(yearPattern, divcontents)
                    if yps:
                        detailData['artwork_start_year'] = yps.groups()[0]
                if ctr == 1:
                    detailData['artwork_materials'] = divcontents
                if ctr == 2:
                    zps = re.search(sizePattern, divcontents)
                    if zps and 'artwork_size_notes' not in detailData.keys():
                        size = zps.groups()[0]
                        detailData['artwork_size_notes'] = size
                        mups = re.search(measureunitPattern, size)
                        if mups:
                            detailData['auction_measureunit'] = mups.groups()[0]
                            size = measureunitPattern.sub("", size)
                        sizeparts = size.split("x")
                        detailData['artwork_measurements_height'] = sizeparts[0]
                        if sizeparts.__len__() > 1:
                            detailData['artwork_measurements_width'] = sizeparts[1]
                        if sizeparts.__len__() > 2:
                            detailData['artwork_measurements_depth'] = sizeparts[2]
                    zps2 = re.search(sizePattern2, divcontents)
                    if zps2 and 'artwork_size_notes' not in detailData.keys():
                        size = zps2.groups()[0]
                        detailData['artwork_size_notes'] = size
                        mups = re.search(measureunitPattern, size)
                        if mups:
                            detailData['auction_measureunit'] = mups.groups()[0]
                            size = measureunitPattern.sub("", size)
                        sizeparts = size.split("x")
                        detailData['artwork_measurements_height'] = sizeparts[0]
                        if sizeparts.__len__() > 1:
                            detailData['artwork_measurements_width'] = sizeparts[1]
                        if sizeparts.__len__() > 2:
                            detailData['artwork_measurements_depth'] = sizeparts[2]
                    zps3 = re.search(sizePattern3, divcontents)
                    if zps3 and 'artwork_size_notes' not in detailData.keys():
                        size = zps3.groups()[0]
                        detailData['artwork_size_notes'] = size
                        mups = re.search(measureunitPattern, size)
                        if mups:
                            detailData['auction_measureunit'] = mups.groups()[0]
                            size = measureunitPattern.sub("", size)
                        sizeparts = size.split("x")
                        detailData['artwork_measurements_height'] = sizeparts[0]
                        if sizeparts.__len__() > 1:
                            detailData['artwork_measurements_width'] = sizeparts[1]
                        if sizeparts.__len__() > 2:
                            detailData['artwork_measurements_depth'] = sizeparts[2]
                zps4 = re.search(sizePattern, divcontents)
                if zps4 and 'artwork_size_notes' not in detailData.keys():
                    size = zps4.groups()[0]
                    detailData['artwork_size_notes'] = zps4.groups()[0]
                    mups = re.search(measureunitPattern, size)
                    if mups:
                        detailData['auction_measureunit'] = mups.groups()[0]
                        size = measureunitPattern.sub("", size)
                    sizeparts = size.split("x")
                    detailData['artwork_measurements_height'] = sizeparts[0]
                    if sizeparts.__len__() > 1:
                        detailData['artwork_measurements_width'] = sizeparts[1]
                    if sizeparts.__len__() > 2:
                        detailData['artwork_measurements_depth'] = sizeparts[2]
                zps5 = re.search(sizePattern2, divcontents)
                if zps5 and 'artwork_size_notes' not in detailData.keys():
                    size = zps5.groups()[0]
                    detailData['artwork_size_notes'] = zps5.groups()[0]
                    mups = re.search(measureunitPattern, size)
                    if mups:
                        detailData['auction_measureunit'] = mups.groups()[0]
                        size = measureunitPattern.sub("", size)
                    sizeparts = size.split("x")
                    detailData['artwork_measurements_height'] = sizeparts[0]
                    if sizeparts.__len__() > 1:
                        detailData['artwork_measurements_width'] = sizeparts[1]
                    if sizeparts.__len__() > 2:
                        detailData['artwork_measurements_depth'] = sizeparts[2]
                zps6 = re.search(sizePattern3, divcontents)
                if zps6 and 'artwork_size_notes' not in detailData.keys():
                    detailData['artwork_size_notes'] = zps6.groups()[0]
                    size = zps6.groups()[0]
                    mups = re.search(measureunitPattern, size)
                    if mups:
                        detailData['auction_measureunit'] = mups.groups()[0]
                        size = measureunitPattern.sub("", size)
                    sizeparts = size.split("x")
                    detailData['artwork_measurements_height'] = sizeparts[0]
                    if sizeparts.__len__() > 1:
                        detailData['artwork_measurements_width'] = sizeparts[1]
                    if sizeparts.__len__() > 2:
                        detailData['artwork_measurements_depth'] = sizeparts[2]
                sps = re.search(signedPattern, divcontents)
                if sps:
                    detailData['artwork_markings'] = divcontents
                sps2 = re.search(signedPattern2, divcontents)
                if sps2 and 'artwork_markings' not in detailData.keys():
                    detailData['artwork_markings'] = divcontents
                eps = re.search(editionPattern, divcontents)
                if eps:
                    detailData['artwork_edition'] = divcontents
                ctr += 1
        allsecondaryh2tags = soup.find_all("h2", {'class' : 'secondary'})
        for secondaryh2tag in allsecondaryh2tags:
            secondarycontents = secondaryh2tag.renderContents().decode('utf-8')
            pps = re.search(provenancePattern, secondarycontents)
            if pps:
                divtag = secondaryh2tag.findNext("div", {'class' : 'accordion-content'})
                if divtag:
                    divcontents = divtag.renderContents().decode('utf-8')
                    divcontents = divcontents.replace("\n", " ").replace("\r", "")
                    divcontents = beginspacePattern.sub("", divcontents)
                    divcontents = endspacePattern.sub("", divcontents)
                    detailData['artwork_provenance'] = divcontents
        allimgtags = soup.find_all("img", {'class' : 'swiper-image'})
        if allimgtags.__len__() > 0:
            defaultimgurl = allimgtags[0]['src']
            defaultimgurlparts = defaultimgurl.split("?")
            if defaultimgurlparts.__len__() > 0:
                defaultimgurl = defaultimgurlparts[0]
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
        descdivtags = soup.find_all("div", {'class' : 'lot-basic-information-secondary'})
        if descdivtags.__len__() > 0:
            descdivcontents = descdivtags[0].renderContents().decode('utf-8')
            descdivcontents = descdivcontents.replace("\n", "").replace("\r", "")
            descdivcontents = self.__class__.htmltagPattern.sub("", descdivcontents)
            detailData['artwork_description'] = descdivcontents
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
        return detailData


    def getInfoFromLotsData(self, htmlList, imagepath, downloadimages):
        baseUrl = "https://www.polyauction.com.hk"
        info = []
        endSpacePattern = re.compile("\s+$", re.DOTALL)
        soldpricePattern = re.compile("([\d\s\.,]+)\s+€")
        beginspacePattern = re.compile("^\s+")
        for htmldiv in htmlList:
            data = {}
            data['auction_num'] = self.saleno
            lotno = ""
            htmlContent = htmldiv.renderContents().decode('utf-8')
            s = BeautifulSoup(htmlContent, features="html.parser")
            allanchors = s.find_all("a")
            htmlanchor = allanchors[0]
            detailUrl = htmlanchor['href']
            data['lot_origin_url'] = detailUrl
            lotnoptags = s.find_all("p", {'class' : 'lot-no'})
            lotnoPattern = re.compile("Lot\s*(\d+)", re.IGNORECASE|re.DOTALL)
            artistname, artworkname = "", ""
            if lotnoptags.__len__() > 0:
                lotnopcontents = lotnoptags[0].renderContents().decode('utf-8')
                lnps = re.search(lotnoPattern, lotnopcontents)
                if lnps:
                    lotno = lnps.groups()[0]
                    data['lot_num'] = lotno
            artisth2tags = s.find_all("h2", {'class' : 'lots-artist'})
            if artisth2tags.__len__() > 0:
                artistcontents = artisth2tags[0].renderContents().decode('utf-8')
                data['artist_name'] = artistcontents
                artistname = data['artist_name']
                titleh2tag = artisth2tags[0].findNext("h2")
                if titleh2tag:
                    titlecontents = titleh2tag.renderContents().decode('utf-8')
                    titlecontents = titlecontents.replace('"', "'")
                    titlecontents = self.__class__.htmltagPattern.sub("", titlecontents)
                    data['artwork_name'] = titlecontents
                    artworkname = data['artwork_name']
            pricespantags = s.find_all("span", {'class' : 'estimate-values'})
            if pricespantags.__len__() > 0:
                estimatecontents = pricespantags[0].renderContents().decode('utf-8')
                estimatePattern = re.compile("HKD\s+([\d\.,]+\s*\-\s*[\d\.,]+)", re.DOTALL)
                eps = re.search(estimatePattern, estimatecontents)
                if eps:
                    estimate = eps.groups()[0]
                    estimateparts = estimate.split(" - ")
                    data['price_estimate_min'] = estimateparts[0]
                    if estimateparts.__len__() > 1:
                        data['price_estimate_max'] = estimateparts[1]
            soldspantags = s.find_all("span", {'class' : 'estimate-values'})
            if soldspantags.__len__() > 1:
                soldspancontents = soldspantags[1].renderContents().decode('utf-8')
                soldPattern = re.compile("HKD\s+([\d\.,]+)", re.DOTALL)
                sps = re.search(soldPattern, soldspancontents)
                if sps:
                    soldprice = sps.groups()[0]
                    data['price_sold'] = soldprice
            #print(data['lot_num'] + " ## " + data['artist_name'] + " ## " + data['artist_birth'] + " ## " + data['artist_death'] + " ## " + data['price_estimate_max'])
            print("Getting '%s'..."%data['lot_origin_url'])
            detailsPageContent = self.getDetailsPage(detailUrl)
            if not lotno:
                continue
            detailData = self.parseDetailPage(detailsPageContent, lotno, imagepath, artistname, artworkname, downloadimages)
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
            data['auction_start_date'] = self.__class__.formatDate(self.auctiondate)
            data['auction_start_date'] = data['auction_start_date'].replace("\n", " ").replace("\r\n", " ")
            data['auction_name'] = self.auctiontitle
            data['auction_house_name'] = "POLY AUCTION"
            data['auction_location'] = "Hongkong"
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
    pageurl = "http://216.137.189.57:8080/scrapers/finish/?scrapername=Polyauction&auctionnumber=%s&auctionurl=%s&scrapertype=2"%(auctionno, urllib.parse.quote(auctionurl))
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
    polyauction = PolyauctionBot(auctionurl, auctionnumber)
    fp = open(csvpath, "w")
    fieldnames = ['auction_house_name', 'auction_location', 'auction_num', 'auction_start_date', 'auction_end_date', 'auction_name', 'lot_num', 'sublot_num', 'price_kind', 'price_estimate_min', 'price_estimate_max', 'price_sold', 'artist_name', 'artist_birth', 'artist_death', 'artist_nationality', 'artwork_name', 'artwork_year_identifier', 'artwork_start_year', 'artwork_end_year', 'artwork_materials', 'artwork_category', 'artwork_markings', 'artwork_edition', 'artwork_description', 'artwork_measurements_height', 'artwork_measurements_width', 'artwork_measurements_depth', 'artwork_size_notes', 'auction_measureunit', 'artwork_condition_in', 'artwork_provenance', 'artwork_exhibited', 'artwork_literature', 'artwork_images1', 'artwork_images2', 'artwork_images3', 'artwork_images4', 'artwork_images5', 'image1_name', 'image2_name', 'image3_name', 'image4_name', 'image5_name', 'lot_origin_url']
    fieldsstr = ",".join(fieldnames)
    fp.write(fieldsstr + "\n")
    pagectr = 1
    while True:
        soup = BeautifulSoup(polyauction.currentPageContent, features="html.parser")
        lotsdata = polyauction.getLotsFromPage()
        info = polyauction.getInfoFromLotsData(lotsdata, imagepath, downloadimages)
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
        nextpageanchors = soup.find_all("a", {'class' : 'button pagination-next'})
        if nextpageanchors.__len__() > 0:
            nextpageUrl = nextpageanchors[0]['href']
            polyauction.pageRequest = urllib.request.Request(nextpageUrl, headers=polyauction.httpHeaders)
            try:
                polyauction.pageResponse = polyauction.opener.open(polyauction.pageRequest)
            except:
                print("Couldn't find the page %s"%str(pagectr))
                break
            polyauction.currentPageContent = polyauction.__class__._decodeGzippedContent(polyauction.getPageContent())
        else:
            break
    fp.close()
    updatestatus(auctionnumber, auctionurl)

# Example: python polyauction.py "https://www.polyauction.com.hk/en/buy-and-sell/auctions/lot-listings/314/?keywords=&currencyType=USD&view=default&sort=lot_number&offset=0&limit=20" 314 /home/supmit/work/artwork/polyauction_314.csv /home/supmit/work/artwork/images/polyauction/314 0 0

# supmit

